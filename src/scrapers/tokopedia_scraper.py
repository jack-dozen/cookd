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
import os
from urllib.parse import urlparse

# ── Shared lock ───────────────────────────────────────────────────────────────
try:
    from src.core.db_lock import DB_LOCK as _db_lock
except ImportError:
    _db_lock = threading.RLock()

# ── Semaphore: batasi jumlah browser Tokopedia yang buka bersamaan ────────────
MAX_BROWSER = 5
_browser_sem = threading.Semaphore(MAX_BROWSER)

MAX_ITEMS = 5
_FRESH_DAYS = 7
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _scrolling(driver):
    scheight = .1
    while scheight < 9.9:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight/%s);" % scheight
        )
        scheight += .01


def _extract_name_from_url(url: str) -> str:
    path = urlparse(url).path
    slug = path.split('/')[-1]
    slug = re.sub(r'-\d{15,}-\d{15,}$', '', slug)
    slug = re.sub(r'-\d{15,}$', '', slug)
    return slug.replace('-', ' ').title()


def _get_price_from_detail(driver, url: str):
    driver.get(url)
    time.sleep(3)
    try:
        price_text = wait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@data-testid="lblPDPDetailProductPrice"]')
            )
        ).text
        return int(re.sub(r'[^\d]', '', price_text))
    except Exception:
        return None


def _detect_unit(product_name: str) -> str:
    name_lower = product_name.lower()
    for pat, label in [
        (r'(\d+(?:[.,]\d+)?)\s*kg\b',    lambda m: f"{m.group(1)}kg"),
        (r'(\d+(?:[.,]\d+)?)\s*gram\b',  lambda m: f"{m.group(1)}gram"),
        (r'(\d+(?:[.,]\d+)?)\s*gr\b',    lambda m: f"{m.group(1)}gr"),
        (r'(\d+(?:[.,]\d+)?)\s*g\b',     lambda m: f"{m.group(1)}g"),
        (r'(\d+(?:[.,]\d+)?)\s*ml\b',    lambda m: f"{m.group(1)}ml"),
        (r'(\d+(?:[.,]\d+)?)\s*liter\b', lambda m: f"{m.group(1)}liter"),
    ]:
        m = re.search(pat, name_lower)
        if m:
            return label(m)
    return ''


def _is_valid_keyword(keyword: str) -> bool:
    if not keyword or len(keyword.strip()) < 2:
        return False
    if re.fullmatch(r"[\d\s\-/.,]+", keyword):
        return False
    if re.match(r"^\d+[\-\s]+\d", keyword):
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# FRESHNESS CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _is_data_fresh(db_path: str, keyword: str) -> bool | None:
    try:
        with _db_lock:
            db = TinyDB(db_path, encoding="utf-8")
            result = db.table('tokped_ingredients').get(Query().keyword == keyword)
            db.close()
    except Exception:
        return None

    if result is None:
        return None

    ts = result.get('timestamp')
    if not ts:
        return None

    timestamp = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
    age_days = (datetime.datetime.today() - timestamp).days
    return age_days <= _FRESH_DAYS


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE SATU KEYWORD
# ══════════════════════════════════════════════════════════════════════════════

def _scrape_keyword(keyword: str, db_path: str) -> None:
    if not _is_valid_keyword(keyword):
        print(f"[{keyword}] SKIP — keyword tidak valid.")
        return

    print(f"[{keyword}] Menunggu slot browser ({MAX_BROWSER} maks)...")
    _browser_sem.acquire()
    print(f"[{keyword}] Slot dapat, memulai scraping...")

    options = wb.ChromeOptions()
    options.add_argument("--window-position=1000,0")
    options.add_argument("--window-size=800,600")
    driver = None

    try:
        driver = wb.Chrome(options=options)
        driver.set_window_position(1000, 0)
        driver.set_window_size(800, 600)

        driver.get('https://www.tokopedia.com/')
        driver.implicitly_wait(5)

        search = driver.find_element(
            By.XPATH,
            '//*[@id="header-main-wrapper"]/div[2]/div[2]/div/div/div/div/input'
        )
        search.send_keys(keyword)
        search.send_keys(Keys.ENTER)

        driver.implicitly_wait(20)
        driver.refresh()
        _scrolling(driver)

        wait(driver, 30).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@data-testid="divSRPContentProducts"]')
            )
        )
        time.sleep(3)

        container = driver.find_element(
            By.XPATH, '//div[@data-testid="divSRPContentProducts"]'
        )
        data_item = container.find_elements(By.XPATH, './div')[:MAX_ITEMS]

        links = []
        for item in data_item:
            try:
                href = item.find_element(By.XPATH, './/a').get_attribute('href')
                if href:
                    links.append(href)
            except Exception:
                continue

        print(f"[{keyword}] Berhasil ambil {len(links)} link")

        product_data = []
        for i, url in enumerate(links):
            print(f"[{keyword}] Scraping produk {i+1}/{len(links)}...")
            name = _extract_name_from_url(url)
            price = _get_price_from_detail(driver, url)
            product_data.append({'name': name, 'price': price, 'url': url})
            if price:
                print(f"[{keyword}]   {name} -> Rp {price:,}")
            else:
                print(f"[{keyword}]   {name} -> harga tidak ditemukan")

        prices = sorted([p['price'] for p in product_data if p['price'] is not None])
        if not prices:
            print(f"[{keyword}] Tidak ada harga yang berhasil diambil, skip.")
            return

        median = prices[len(prices) // 2]
        hasil = min(product_data, key=lambda x: abs((x['price'] or 0) - median))
        print(f"[{keyword}] Produk terpilih: {hasil['name']} -> Rp {hasil['price']:,}")

        with _db_lock:
            db = TinyDB(db_path, encoding="utf-8")
            table = db.table('tokped_ingredients')
            table.remove(Query().keyword == keyword)
            table.insert({
                'keyword'  : keyword,
                'name'     : hasil['name'],
                'price'    : int(hasil['price']),
                'unit'     : _detect_unit(hasil['name']),
                'url'      : hasil['url'],
                'timestamp': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            })
            db.close()
            print(f"[{keyword}] Tersimpan ke TinyDB.")

    except Exception as e:
        print(f"[{keyword}] ERROR: {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        _browser_sem.release()
        print(f"[{keyword}] Slot browser dilepas.")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def tokpedia_scraper(keywords: list[str]) -> None:
    db_path = os.path.join(_ROOT, "data", "base.json")

    to_scrape = []
    for keyword in keywords:
        status = _is_data_fresh(db_path, keyword)
        if status is True:
            print(f"[{keyword}] Data masih fresh, skip.")
            continue
        if status is False:
            print(f"[{keyword}] Data stale, hapus dan scraping ulang...")
            with _db_lock:
                db = TinyDB(db_path, encoding="utf-8")
                db.table('tokped_ingredients').remove(Query().keyword == keyword)
                db.close()
        else:
            print(f"[{keyword}] Data tidak ada, scraping...")
        to_scrape.append(keyword)

    if not to_scrape:
        print("Semua data Tokopedia masih fresh, tidak ada yang perlu discrape.")
        return

    threads = [
        threading.Thread(target=_scrape_keyword, args=(kw, db_path), daemon=True)
        for kw in to_scrape
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("\n[Tokopedia] Semua scraping selesai!")
