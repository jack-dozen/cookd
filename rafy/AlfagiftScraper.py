# Alfagift Scraper v7
# Generated with Claude (Anthropic) - claude.ai
"""
Alfagift Scraper - alfagift.id
Scrape berdasarkan keyword nama bahan (misal: "ayam", "bawang putih")

PERUBAHAN v7:
- Hapus _simplify_search_query (bug: "keju quick melt" → "keju" → hasil tidak relevan)
- Tambah relevance scoring dengan difflib untuk pilih produk paling relevan
- Semua TinyDB pakai encoding='utf-8' agar tidak crash di Windows dengan emoji
- Driver cleanup lebih ketat dengan time.sleep setelah quit

Install dependencies:
    pip install undetected-chromedriver beautifulsoup4 tinydb
"""

import time
import re
import os
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin, quote
from difflib import SequenceMatcher

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
import json


# ══════════════════════════════════════════════════════════════════════════════
# KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL       = "https://www.alfagift.id"
SEARCH_URL     = "https://www.alfagift.id/find/{keyword}"
DB_PATH        = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')
CHROME_VERSION = 147
MAX_RESULTS    = 3
DELAY_MIN      = 1.0
DELAY_MAX      = 2.0

# Skor relevansi minimum — produk di bawah ini diabaikan
RELEVANCE_THRESHOLD = 0.25

# Lock untuk TinyDB dan driver init
_db_lock          = threading.Lock()
_driver_init_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# PRETTY JSON STORAGE (utf-8 agar emoji tidak crash di Windows)
# ══════════════════════════════════════════════════════════════════════════════

class PrettyJSONStorage(JSONStorage):
    def __init__(self, path, **kwargs):
        # Paksa encoding utf-8 — fix untuk WinError charmap di Windows
        kwargs.setdefault('encoding', 'utf-8')
        super().__init__(path, **kwargs)

    def write(self, data):
        self._handle.seek(0)
        json.dump(data, self._handle, indent=2, ensure_ascii=False)
        self._handle.flush()
        self._handle.truncate()


# ══════════════════════════════════════════════════════════════════════════════
# RELEVANCE SCORING
# ══════════════════════════════════════════════════════════════════════════════

def _relevance_score(product_name: str, keyword: str) -> float:
    """
    Hitung skor relevansi produk terhadap keyword (0.0 - 1.0).

    Kombinasi dua metrik:
    - Rasio kesamaan string (SequenceMatcher)
    - Proporsi kata keyword yang ditemukan di nama produk

    Contoh:
        keyword = "keju quick melt"
        "Kraft Quick Melt Cheese 165g" → skor tinggi ✓
        "Alamii Snack Cheese Puffs 15g" → skor rendah ✗
    """
    name_lower    = product_name.lower()
    keyword_lower = keyword.lower()

    # Skor 1: kesamaan string keseluruhan
    ratio = SequenceMatcher(None, keyword_lower, name_lower).ratio()

    # Skor 2: proporsi kata keyword yang ada di nama produk
    keyword_words = [w for w in keyword_lower.split() if len(w) > 2]
    if keyword_words:
        words_found = sum(1 for w in keyword_words if w in name_lower)
        word_ratio  = words_found / len(keyword_words)
    else:
        word_ratio = ratio

    # Bobot: word_ratio lebih penting karena lebih presisi
    return (ratio * 0.35) + (word_ratio * 0.65)


def _pick_best(scraped: list[dict], keyword: str) -> dict | None:
    """
    Dari list produk yang sudah di-scrape, pilih yang paling relevan
    dengan keyword, lalu dari yang relevan pilih yang termurah.
    """
    if not scraped:
        return None

    # Hitung skor tiap produk
    scored = [
        (item, _relevance_score(item.get("name", ""), keyword))
        for item in scraped
        if item.get("price", 0) > 0
    ]

    if not scored:
        return None

    # Filter yang relevan
    relevant = [(item, score) for item, score in scored if score >= RELEVANCE_THRESHOLD]

    # Kalau tidak ada yang cukup relevan, ambil skor tertinggi saja
    if not relevant:
        relevant = [max(scored, key=lambda x: x[1])]

    # Dari yang relevan, pilih termurah
    best_item = min(relevant, key=lambda x: x[0]["price"])[0]
    best_score = max(relevant, key=lambda x: x[1])[1]

    print(f"    [relevance] Terpilih: '{best_item['name']}' "
          f"(skor={best_score:.2f}, harga=Rp {best_item['price']:,})")
    return best_item


# ══════════════════════════════════════════════════════════════════════════════
# DRIVER
# ══════════════════════════════════════════════════════════════════════════════

def init_driver():
    import tempfile
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=id-ID")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=CHROME_VERSION,
        headless=True,
        user_data_dir=tempfile.mkdtemp(),  # folder temp unik per instance
    )
    return driver


def wait_page_ready(driver, timeout=30):
    print("    Menunggu halaman...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        title = driver.title.lower()
        if not any(k in title for k in ["checking", "just a moment", "cloudflare"]):
            print(f" OK ({time.time()-start:.1f}s)")
            time.sleep(1.0)
            return True
        time.sleep(0.4)
        print(".", end="", flush=True)
    print(" TIMEOUT!")
    return False


def fetch_page(driver, url, wait_seconds=2):
    print(f"    Fetch: {url}")
    driver.get(url)
    time.sleep(0.5)
    wait_page_ready(driver)
    time.sleep(wait_seconds)
    return BeautifulSoup(driver.page_source, "html.parser")


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE HASIL PENCARIAN
# ══════════════════════════════════════════════════════════════════════════════

def search_products(driver, keyword):
    """
    Cari produk di Alfagift. Keyword TIDAK disederhanakan —
    langsung pakai keyword asli agar hasil lebih relevan.
    """
    encoded    = quote(keyword, safe='')
    search_url = SEARCH_URL.format(keyword=encoded)
    soup       = fetch_page(driver, search_url, wait_seconds=3)

    results = []
    seen    = set()

    for link in soup.select("a[href^='/p/']"):
        href = link.get("href", "")
        if not href or href == "/p/search" or "search?q" in href:
            continue

        full_url = urljoin(BASE_URL, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        name_el    = link.select_one("p, span, h3, h2")
        name       = name_el.get_text(strip=True) if name_el else link.get_text(strip=True)
        price_el   = link.select_one("[class*='price'], [class*='Price']")
        price_text = price_el.get_text(strip=True) if price_el else ""

        if not name:
            continue

        results.append({"url": full_url, "name": name, "price_text": price_text})
        if len(results) >= MAX_RESULTS:
            break

    print(f"    Ditemukan {len(results)} produk untuk '{keyword}'")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE DETAIL PRODUK
# ══════════════════════════════════════════════════════════════════════════════

def parse_price(price_str):
    try:
        cleaned = re.sub(r'[^\d]', '', price_str)
        return int(cleaned)
    except Exception:
        return 0


def detect_unit(nama):
    nama_lower = nama.lower()
    for satuan in [
        "per kg", "per pcs", "per pack", "per liter", "per buah",
        "1kg", "500g", "500gr", "250g", "250gr", "100g", "100gr",
        "liter", " ml", " gr", " kg", " pcs", "pack", "btl", "bks",
        "pouch", "sachet", "dus",
    ]:
        if satuan in nama_lower:
            return satuan.strip()
    return ""


def scrape_product_detail(driver, url):
    soup = fetch_page(driver, url, wait_seconds=3)

    nama_el = (
        soup.select_one("p.text-xlg.fw7") or
        soup.select_one("p.text-xl.fw5")
    )
    nama = nama_el.get_text(strip=True) if nama_el else ""

    if not nama or any(k in nama.lower() for k in ["not found", "404", "halaman tidak"]):
        return None

    harga_el  = soup.select_one("p.text-xlg.fw7.text-primary")
    harga_str = harga_el.get_text(strip=True) if harga_el else ""

    if not harga_str:
        for el in soup.find_all(["p", "span"]):
            teks = el.get_text(strip=True)
            if teks.startswith("Rp"):
                harga_str = teks
                break

    harga_int = parse_price(harga_str)
    unit      = detect_unit(nama)

    return {
        "product_name": nama,
        "price":        harga_int,
        "price_str":    harga_str,
        "unit":         unit,
        "product_url":  url,
    }


# ══════════════════════════════════════════════════════════════════════════════
# FRESHNESS CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _is_data_fresh(db_path: str, keyword: str):
    """
    True  → data ada dan masih fresh (< 7 hari)
    False → data ada tapi sudah > 7 hari
    None  → data tidak ada
    """
    with _db_lock:
        db     = TinyDB(db_path, storage=PrettyJSONStorage)
        result = db.table('alfagift_ingredients').get(Query().keyword == keyword)

    if result is None:
        return None

    try:
        timestamp    = datetime.strptime(result['timestamp'], '%Y-%m-%d %H:%M:%S')
        selisih_hari = (datetime.now() - timestamp).days
        return selisih_hari <= 7
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA: scrape_by_keyword
# ══════════════════════════════════════════════════════════════════════════════

def scrape_by_keyword(driver, keyword, use_relevance_filter=True):
    db_path = DB_PATH

    print(f"\n{'='*55}")
    print(f"SCRAPE ALFAGIFT - keyword: '{keyword}'")
    print(f"{'='*55}")

    # Cek cache
    status = _is_data_fresh(db_path, keyword)
    if status is True:
        print(f"[{keyword}] Data masih fresh, skip scraping.")
        return get_by_keyword(keyword)
    elif status is False:
        print(f"[{keyword}] Data sudah > 7 hari, scraping ulang...")
        with _db_lock:
            db = TinyDB(db_path, storage=PrettyJSONStorage)
            db.table('alfagift_ingredients').remove(Query().keyword == keyword)

    # Cari produk — keyword langsung tanpa simplifikasi
    search_results = search_products(driver, keyword)
    if not search_results:
        print(f"  Tidak ada produk ditemukan untuk '{keyword}'")
        return []

    # Scrape detail tiap produk
    scraped = []
    for i, result in enumerate(search_results, 1):
        print(f"\n  [{i}/{len(search_results)}] {result['url']}")
        detail = scrape_product_detail(driver, result["url"])

        if not detail or not detail["product_name"]:
            print(f"    x Gagal ambil detail, skip.")
            continue

        row = {
            "keyword"  : keyword,
            "name"     : detail["product_name"],
            "price"    : detail["price"],
            "url"      : detail["product_url"],
            "unit"     : detail["unit"],
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        scraped.append(row)
        print(f"    v {row['name']} - Rp {row['price']:,} ({row['unit']})")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    if not scraped:
        return []

    # Pilih produk terbaik: relevan + termurah
    if use_relevance_filter and len(scraped) > 1:
        best = _pick_best(scraped, keyword)
    else:
        # Fallback: termurah saja
        best = min(
            [r for r in scraped if r["price"] > 0],
            key=lambda x: x["price"],
            default=scraped[0],
        )

    if not best:
        best = scraped[0]

    # Simpan ke TinyDB
    with _db_lock:
        db    = TinyDB(db_path, storage=PrettyJSONStorage)
        table = db.table('alfagift_ingredients')
        table.remove(Query().keyword == keyword)
        table.insert(best)
    print(f"[{keyword}] Tersimpan: {best['name']} - Rp {best['price']:,}")

    return [best]


# ══════════════════════════════════════════════════════════════════════════════
# scrape_keywords_parallel
# ══════════════════════════════════════════════════════════════════════════════

def scrape_keywords_parallel(keywords: list[str], max_workers: int = 3) -> list:
    """
    Scrape beberapa keyword secara paralel.
    Driver diinit sequential (_driver_init_lock + user_data_dir unik)
    untuk menghindari WinError 32 di Windows.
    """
    fresh     = [kw for kw in keywords if _is_data_fresh(DB_PATH, kw) is True]
    to_scrape = [kw for kw in keywords if kw not in fresh]

    if fresh:
        print(f"[Alfagift Parallel] Skip {len(fresh)} keyword fresh: {fresh}")
    if not to_scrape:
        print(f"[Alfagift Parallel] Semua keyword fresh.")
        return [get_by_keyword(kw) for kw in keywords if get_by_keyword(kw)]

    workers = min(max_workers, len(to_scrape))
    print(f"[Alfagift Parallel] {len(to_scrape)} keyword → {workers} worker")

    all_results = []

    def _scrape_one(keyword: str) -> list:
        driver = None
        try:
            with _driver_init_lock:
                driver = init_driver()
                time.sleep(0.5)  # beri jeda setelah init sebelum release lock
            result = scrape_by_keyword(driver, keyword)
            return result if isinstance(result, list) else ([result] if result else [])
        except Exception as e:
            print(f"[Alfagift Parallel] ERROR '{keyword}': {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(1.5)  # beri jeda setelah quit agar file dilepas OS

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_scrape_one, kw): kw for kw in to_scrape}
        for future in as_completed(futures):
            kw = futures[future]
            try:
                result = future.result()
                all_results.extend(result)
                print(f"[Alfagift Parallel] '{kw}' selesai ✓")
            except Exception as e:
                print(f"[Alfagift Parallel] Future error '{kw}': {e}")

    print(f"[Alfagift Parallel] Selesai. Total: {len(all_results)} hasil.")
    return all_results


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_by_keyword(keyword, db_path=DB_PATH):
    with _db_lock:
        db = TinyDB(db_path, storage=PrettyJSONStorage)
        return db.table("alfagift_ingredients").get(Query().keyword == keyword)

def get_all(db_path=DB_PATH):
    with _db_lock:
        db = TinyDB(db_path, storage=PrettyJSONStorage)
        return db.table("alfagift_ingredients").all()