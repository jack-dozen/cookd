# AEON Store Scraper v4
"""
AEON Store Scraper - raisa.aeonstore.id
Scrape berdasarkan keyword nama bahan (misal: "ayam", "bawang putih")
"""

import time
import json
import re
import os
import sys
import threading
import random
from datetime import datetime
from urllib.parse import urljoin, quote

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage

# ── Shared lock ───────────────────────────────────────────────────────────────
try:
    from src.core.db_lock import DB_LOCK as _db_lock
except ImportError:
    _db_lock = threading.RLock()  # fallback saat test standalone


# ══════════════════════════════════════════════════════════════════════════════
# KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL       = "https://raisa.aeonstore.id"
SEARCH_URL     = "https://raisa.aeonstore.id/?s={keyword}&post_type=product"
_ROOT          = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH        = os.path.join(_ROOT, "data", "base.json")
CHROME_VERSION = 147
MAX_RESULTS    = 2
DELAY_MIN      = 0.8
DELAY_MAX      = 1.5
_FRESH_DAYS    = 7


# ══════════════════════════════════════════════════════════════════════════════
# PRETTY JSON STORAGE
# ══════════════════════════════════════════════════════════════════════════════

class PrettyJSONStorage(JSONStorage):
    def __init__(self, path, **kwargs):
        kwargs.setdefault('encoding', 'utf-8')
        super().__init__(path, **kwargs)

    def write(self, data):
        self._handle.seek(0)
        json.dump(data, self._handle, indent=2, ensure_ascii=False)
        self._handle.flush()
        self._handle.truncate()


# ══════════════════════════════════════════════════════════════════════════════
# DRIVER
# ══════════════════════════════════════════════════════════════════════════════

def init_driver():
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
    )
    return driver


def wait_cloudflare(driver, timeout=30):
    print("    Menunggu Cloudflare...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        title = driver.title.lower()
        if not any(k in title for k in ["checking", "just a moment", "cloudflare"]):
            print(f" OK ({time.time()-start:.1f}s)")
            time.sleep(1.5)
            return True
        time.sleep(0.4)
        print(".", end="", flush=True)
    print(" TIMEOUT!")
    return False


def fetch_page(driver, url, wait_seconds=1):
    print(f"    Fetch: {url}")
    driver.get(url)
    time.sleep(0.5)
    wait_cloudflare(driver)
    time.sleep(wait_seconds)
    return BeautifulSoup(driver.page_source, "html.parser")


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE HASIL PENCARIAN
# ══════════════════════════════════════════════════════════════════════════════

def search_products(driver, keyword):
    encoded    = quote(keyword, safe='').replace('%20', '+')
    search_url = SEARCH_URL.format(keyword=encoded)
    soup       = fetch_page(driver, search_url, wait_seconds=3)

    results = []
    seen    = set()

    for link in soup.select("a[href*='/shop/']"):
        href     = link.get("href", "")
        full_url = urljoin(BASE_URL, href)

        if (full_url in seen
                or "/product-category/" in full_url
                or "?add-to-cart" in full_url
                or not full_url.startswith(BASE_URL + "/shop/")):
            continue

        seen.add(full_url)
        name = link.get_text(strip=True) or link.get("title", "")

        parent     = link.find_parent("li") or link.find_parent("div")
        price_text = ""
        if parent:
            price_el = parent.select_one(".woocommerce-Price-amount bdi, .price bdi")
            if price_el:
                price_text = price_el.get_text(strip=True)

        results.append({"url": full_url, "name": name, "price_text": price_text})
        if len(results) >= MAX_RESULTS:
            break

    print(f"    Ditemukan {len(results)} produk untuk keyword '{keyword}'")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE DETAIL PRODUK
# ══════════════════════════════════════════════════════════════════════════════

def parse_price(price_str):
    try:
        cleaned = (price_str
                   .replace("Rp", "")
                   .replace("\xa0", "")
                   .replace(".", "")
                   .replace(",", ".")
                   .strip())
        return int(float(cleaned))
    except Exception:
        return 0


def _detect_unit(nama):
    nama_lower = nama.lower()
    for satuan in [
        "per kg", "per pcs", "per pack", "per liter", "per buah",
        "1kg", "500g", "500gr", "250g", "250gr", "100g", "100gr",
        "liter", "ml", "gr", "kg", "pcs", "pack", "btl", "bks",
    ]:
        if satuan in nama_lower:
            return satuan
    return ""


def scrape_product_detail(driver, url):
    soup = fetch_page(driver, url, wait_seconds=3)

    nama_el = (
        soup.select_one(".product_title.entry-title") or
        soup.select_one("h1.product_title") or
        soup.select_one("h1")
    )
    nama = nama_el.get_text(strip=True) if nama_el else ""

    if any(k in nama.lower() for k in ["can't be reached", "not found", "checking your browser", "404"]):
        return None

    harga_sale   = soup.select_one(".price ins .woocommerce-Price-amount bdi")
    harga_normal = soup.select_one(".price .woocommerce-Price-amount bdi")
    harga_str    = ""
    if harga_sale:
        harga_str = harga_sale.get_text(strip=True)
    elif harga_normal:
        harga_str = harga_normal.get_text(strip=True)

    breadcrumbs = soup.select(".woocommerce-breadcrumb a")
    kategori    = " > ".join(a.get_text(strip=True) for a in breadcrumbs[1:]) if len(breadcrumbs) > 1 else ""

    gambar_el  = soup.select_one(".woocommerce-product-gallery__image img, .wp-post-image")
    gambar_url = ""
    if gambar_el:
        gambar_url = (
            gambar_el.get("data-large_image") or
            gambar_el.get("data-src") or
            gambar_el.get("src", "")
        )

    return {
        "product_name": nama,
        "price":        parse_price(harga_str),
        "price_str":    harga_str,
        "unit":         _detect_unit(nama),
        "kategori":     kategori,
        "product_url":  url,
        "image_url":    gambar_url,
    }


# ══════════════════════════════════════════════════════════════════════════════
# FRESHNESS CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _is_data_fresh(db_path: str, keyword: str):
    try:
        with _db_lock:
            db     = TinyDB(db_path, storage=PrettyJSONStorage)
            result = db.table('aeon_ingredients').get(Query().keyword == keyword)
            db.close()
    except Exception:
        return None

    if result is None:
        return None

    try:
        ts = datetime.strptime(result["timestamp"], "%Y-%m-%d %H:%M:%S")
        return (datetime.today() - ts).days <= _FRESH_DAYS
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA: scrape_by_keyword
# ══════════════════════════════════════════════════════════════════════════════

def scrape_by_keyword(driver, keyword):
    print(f"\n{'='*55}")
    print(f"SCRAPE AEON — keyword: '{keyword}'")
    print(f"{'='*55}")

    status = _is_data_fresh(DB_PATH, keyword)
    if status is True:
        print(f"  Cache hit untuk '{keyword}'")
        return get_by_keyword(keyword)
    elif status is False:
        print(f"  Data stale, hapus dan scraping ulang...")
        with _db_lock:
            db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
            db.table('aeon_ingredients').remove(Query().keyword == keyword)
            db.close()

    search_results = search_products(driver, keyword)
    if not search_results:
        print(f"  Tidak ada produk ditemukan untuk '{keyword}'")
        return []

    saved = []
    for i, result in enumerate(search_results, 1):
        print(f"\n  [{i}/{len(search_results)}] {result['url']}")
        detail = scrape_product_detail(driver, result["url"])

        if not detail or not detail["product_name"]:
            print(f"    ✗ Gagal ambil detail, skip.")
            continue

        row = {
            "keyword"  : keyword,
            "name"     : detail["product_name"],
            "price"    : detail["price"],
            "url"      : detail["product_url"],
            "unit"     : detail["unit"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        with _db_lock:
            db    = TinyDB(DB_PATH, storage=PrettyJSONStorage)
            table = db.table("aeon_ingredients")
            table.upsert(row, Query().keyword == keyword)
            db.close()

        saved.append(row)
        print(f"    ✓ {row['name']} — Rp {row['price']:,} ({row['unit']})")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    print(f"\n  Selesai! {len(saved)} produk disimpan untuk keyword '{keyword}'")
    return saved


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_by_keyword(keyword, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    with _db_lock:
        db     = TinyDB(db_path, storage=PrettyJSONStorage)
        result = db.table("aeon_ingredients").get(Query().keyword == keyword)
        db.close()
    return result

def get_all(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    with _db_lock:
        db     = TinyDB(db_path, storage=PrettyJSONStorage)
        result = db.table("aeon_ingredients").all()
        db.close()
    return result

def delete_by_keyword(keyword, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    with _db_lock:
        db = TinyDB(db_path, storage=PrettyJSONStorage)
        db.table("aeon_ingredients").remove(Query().keyword == keyword)
        db.close()


if __name__ == "__main__":
    keywords = ["indomie"]
    driver   = init_driver()
    try:
        for kw in keywords:
            results = scrape_by_keyword(driver, kw)
            print(f"\nRingkasan '{kw}':")
            for r in results:
                print(f"  - {r['name']:40} Rp {r['price']:>10,}  {r['unit']}")
    finally:
        driver.quit()

    print(f"\n{'='*55}")
    print(f"Total data di DB: {len(get_all())} baris")
    print(f"File: {DB_PATH}")
