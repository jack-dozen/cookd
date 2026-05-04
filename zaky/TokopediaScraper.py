# BASE: https://github.com/crypter70/Tokopedia-Scraper/blob/main/scraper.py
# MODIFIED WITH CLAUDE

from selenium.webdriver.common.by import By
from selenium import webdriver as wb
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.keys import Keys
from tinydb import TinyDB, Query
import datetime
import time
import re
import threading
from urllib.parse import urlparse
import os


MAX_ITEMS = 5
_db_lock = threading.Lock()


def _scrolling(driver):
    scheight = .1
    while scheight < 9.9:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/%s);" % scheight)
        scheight += .01


def _extract_name_from_url(url):
    path = urlparse(url).path
    slug = path.split('/')[-1]
    slug = re.sub(r'-\d{15,}-\d{15,}$', '', slug)
    slug = re.sub(r'-\d{15,}$', '', slug)
    return slug.replace('-', ' ').title()


def _get_price_from_detail(driver, url):
    driver.get(url)
    time.sleep(3)
    try:
        price_text = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="lblPDPDetailProductPrice"]'))
        ).text
        return int(re.sub(r'[^\d]', '', price_text))
    except:
        return None


def _is_data_fresh(db_path: str, keyword: str) -> bool | None:
    """
    Cek apakah data keyword sudah ada di TinyDB dan masih fresh (< 7 hari).

    Returns:
        True  -> data ada dan masih fresh, skip scraping
        False -> data ada tapi sudah > 7 hari, perlu scraping ulang
        None  -> data tidak ada, perlu scraping
    """
    with _db_lock:
        db = TinyDB(db_path)
        tokped_ingredients = db.table('tokped_ingredients')
        Item = Query()
        result = tokped_ingredients.get(Item.keyword == keyword)

    if result is None:
        return None

    timestamp = datetime.datetime.strptime(result['timestamp'], '%Y-%m-%d %H:%M:%S')
    selisih_hari = (datetime.datetime.today() - timestamp).days

    return selisih_hari <= 7


def _scrape_keyword(keyword, db_path):
    print(f"[{keyword}] Memulai scraping...")
    driver = wb.Chrome()

    try:
        driver.get('https://www.tokopedia.com/')
        driver.implicitly_wait(5)

        search = driver.find_element(By.XPATH, '//*[@id="header-main-wrapper"]/div[2]/div[2]/div/div/div/div/input')
        search.send_keys(keyword)
        search.send_keys(Keys.ENTER)

        # ── Step 1: Ambil link ──
        driver.implicitly_wait(20)
        driver.refresh()
        _scrolling(driver)

        wait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="divSRPContentProducts"]'))
        )
        time.sleep(3)

        container = driver.find_element(By.XPATH, '//div[@data-testid="divSRPContentProducts"]')
        data_item = container.find_elements(By.XPATH, './div')[:MAX_ITEMS]

        links = []
        for item in data_item:
            try:
                href = item.find_element(By.XPATH, './/a').get_attribute('href')
                if href:
                    links.append(href)
            except:
                continue

        print(f"[{keyword}] Berhasil ambil {len(links)} link")

        # ── Step 2: Ambil harga tiap link ──
        product_data = []
        for i, url in enumerate(links):
            print(f"[{keyword}] Scraping produk {i+1}/{len(links)}...")
            name = _extract_name_from_url(url)
            price = _get_price_from_detail(driver, url)
            product_data.append({'name': name, 'price': price, 'url': url})
            print(f"[{keyword}]   {name} -> Rp {price:,}" if price else f"[{keyword}]   {name} -> harga tidak ditemukan")

        # ── Step 3: Hitung median ──
        prices = sorted([p['price'] for p in product_data if p['price'] is not None])
        if not prices:
            print(f"[{keyword}] Tidak ada harga yang berhasil diambil, skip.")
            return

        median = prices[len(prices) // 2]
        hasil = min(product_data, key=lambda x: abs((x['price'] or 0) - median))

        print(f"[{keyword}] Produk terpilih: {hasil['name']} -> Rp {hasil['price']:,}")

        # ── Step 4: Simpan ke TinyDB ──
        with _db_lock:
            db = TinyDB(db_path)
            tokped_ingredients = db.table('tokped_ingredients')
            Item = Query()
            tokped_ingredients.remove(Item.keyword == keyword)  # hapus data lama jika ada
            tokped_ingredients.insert({
                'keyword': keyword,
                'name': hasil['name'],
                'price': int(hasil['price']),
                'url': hasil['url'],
                'timestamp': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            })
            print(f"[{keyword}] Tersimpan ke TinyDB.")

    except Exception as e:
        print(f"[{keyword}] ERROR: {e}")

    finally:
        driver.quit()


def tokpedia_scraper(keywords: list[str]):
    """
    Entry point utama.

    Args:
        keywords: List keyword yang mau di-scrape, contoh: ['bawang putih', 'gula pasir']
        db_path:  Path ke file TinyDB, contoh: './data/scraping_data.json'
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')
    threads = []
    for keyword in keywords:
        status = _is_data_fresh(db_path, keyword)

        if status is True:
            print(f"[{keyword}] Data masih fresh, skip scraping.")
            continue
        elif status is False:
            print(f"[{keyword}] Data sudah > 7 hari, scraping ulang...")
            with _db_lock:
                db = TinyDB(db_path)
                tokped_ingredients = db.table('tokped_ingredients')
                Item = Query()
                tokped_ingredients.remove(Item.keyword == keyword)
        else:
            print(f"[{keyword}] Data tidak ada, mulai scraping...")

        t = threading.Thread(target=_scrape_keyword, args=(keyword, db_path))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("\nSemua scraping selesai!")


# ── untuk testing ──
#if __name__ == '__main__':
#    tokpedia_scraper(keywords=['bawang putih', 'gula pasir', 'tempe', 'garam'])
