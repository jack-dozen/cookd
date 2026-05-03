# AEON Store Scraper v3
# Generated with Claude (Anthropic) - claude.ai
"""
AEON Store Scraper - raisa.aeonstore.id
Scrape berdasarkan keyword nama bahan (misal: "ayam", "bawang putih")
Output sesuai struktur tabel ingredients di proposal Cookd

Install dependencies:
    pip install undetected-chromedriver beautifulsoup4 tinydb
"""

import time
import json
import random
from datetime import datetime
from urllib.parse import urljoin, quote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query

from tinydb.storages import JSONStorage
import json
import os

class PrettyJSONStorage(JSONStorage):
    def write(self, data):
        self._handle.seek(0)
        json.dump(data, self._handle, indent=2, ensure_ascii=False)
        self._handle.flush()
        self._handle.truncate()

# ══════════════════════════════════════════════════════════════════════════════
# KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL       = "https://raisa.aeonstore.id"
SEARCH_URL     = "https://raisa.aeonstore.id/?s={keyword}&post_type=product"
DB_PATH        = os.path.join(os.path.dirname(__file__), "ingredients.json")   # TinyDB file
CHROME_VERSION = 147                  # sesuaikan versi Chrome kamu
MAX_RESULTS    = 2                   # maks produk per keyword
DELAY_MIN      = 0.8
DELAY_MAX      = 1.5

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
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=CHROME_VERSION, headless=True)
    return driver


def wait_cloudflare(driver, timeout=30):
    """Tunggu sampai Cloudflare challenge selesai."""
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
    """
    Cari produk di AEON berdasarkan keyword.
    Return: list of (product_url, product_name, price_text, category)
    """
    encoded = quote(keyword, safe='').replace('%20', '+')
    search_url = SEARCH_URL.format(keyword=encoded)

    soup = fetch_page(driver, search_url, wait_seconds=3)

    results = []

    # Ambil produk dari hasil pencarian
    links = soup.select("a[href*='/shop/']")
    seen = set()

    for link in links:
        href = link.get("href", "")
        full_url = urljoin(BASE_URL, href)

        # Filter hanya URL produk
        if (full_url in seen
                or "/product-category/" in full_url
                or "?add-to-cart" in full_url
                or not full_url.startswith(BASE_URL + "/shop/")):
            continue

        seen.add(full_url)

        # Ambil nama produk dari teks link atau title
        name = link.get_text(strip=True) or link.get("title", "")

        # Coba ambil harga dari elemen terdekat
        parent = link.find_parent("li") or link.find_parent("div")
        price_text = ""
        if parent:
            price_el = parent.select_one(".woocommerce-Price-amount bdi, .price bdi")
            if price_el:
                price_text = price_el.get_text(strip=True)

        results.append({
            "url":        full_url,
            "name":       name,
            "price_text": price_text,
        })

        if len(results) >= MAX_RESULTS:
            break

    print(f"    Ditemukan {len(results)} produk untuk keyword '{keyword}'")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE DETAIL PRODUK
# ══════════════════════════════════════════════════════════════════════════════

def parse_price(price_str):
    """Ubah string harga 'Rp\xa049.900' → int 49900."""
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


def scrape_product_detail(driver, url):
    """Scrape detail produk: nama, harga, kategori, satuan, gambar."""
    soup = fetch_page(driver, url, wait_seconds=3)

    # Nama
    nama_el = (
        soup.select_one(".product_title.entry-title") or
        soup.select_one("h1.product_title") or
        soup.select_one("h1")
    )
    nama = nama_el.get_text(strip=True) if nama_el else ""

    # Validasi error
    if any(k in nama.lower() for k in ["can't be reached", "not found", "checking your browser", "404"]):
        return None

    # Harga
    harga_sale   = soup.select_one(".price ins .woocommerce-Price-amount bdi")
    harga_normal = soup.select_one(".price .woocommerce-Price-amount bdi")
    harga_str = ""
    if harga_sale:
        harga_str = harga_sale.get_text(strip=True)
    elif harga_normal:
        harga_str = harga_normal.get_text(strip=True)
    harga_int = parse_price(harga_str)

    # Kategori dari breadcrumb
    breadcrumbs = soup.select(".woocommerce-breadcrumb a")
    kategori = " > ".join(a.get_text(strip=True) for a in breadcrumbs[1:]) if len(breadcrumbs) > 1 else ""

    # Satuan — coba deteksi dari nama produk (misal: "1kg", "500gr", "per pcs")
    unit = ""
    nama_lower = nama.lower()
    for satuan in ["per kg", "per pcs", "per pack", "per liter", "per buah",
                   "1kg", "500g", "500gr", "250g", "250gr", "100g", "100gr",
                   "liter", "ml", "gr", "kg", "pcs", "pack", "btl", "bks"]:
        if satuan in nama_lower:
            unit = satuan
            break

    # Gambar
    gambar_el = soup.select_one(".woocommerce-product-gallery__image img, .wp-post-image")
    gambar_url = ""
    if gambar_el:
        gambar_url = (
            gambar_el.get("data-large_image") or
            gambar_el.get("data-src") or
            gambar_el.get("src", "")
        )

    return {
        "product_name": nama,
        "price":        harga_int,
        "price_str":    harga_str,
        "unit":         unit,
        "kategori":     kategori,
        "product_url":  url,
        "image_url":    gambar_url,
    }


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA: scrape_by_keyword
# Ini yang dipanggil dari aplikasi Flet saat user klik nama bahan
# ══════════════════════════════════════════════════════════════════════════════

def scrape_by_keyword(driver, keyword, db=None):
    """
    Scrape produk AEON berdasarkan keyword bahan.
    Simpan ke TinyDB dengan struktur tabel ingredients.

    Parameter:
        driver  : Selenium driver (sudah diinit)
        keyword : Nama bahan, contoh: "ayam", "bawang putih"
        db      : TinyDB instance (opsional, jika None akan buat baru)

    Return:
        list of dict sesuai struktur tabel ingredients
    """
    if db is None:
        db = TinyDB(DB_PATH, storage=PrettyJSONStorage)

    table = db.table("ingredients")
    Ingredient = Query()

    print(f"\n{'='*55}")
    print(f"SCRAPE AEON — keyword: '{keyword}'")
    print(f"{'='*55}")

    # Cek cache — jika keyword sudah ada di DB hari ini, skip scraping
    today = datetime.now().strftime("%Y-%m-%d")
    existing = table.search(
        (Ingredient.ingredient_keyword == keyword) &
        (Ingredient.scraped_at.test(lambda x: x.startswith(today)))
    )
    if existing:
        print(f"  Cache hit: {len(existing)} data sudah ada untuk hari ini.")
        return existing

    # Scrape hasil pencarian
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

        # Susun data sesuai struktur tabel ingredients
        row = {
            "ingredient_keyword": keyword,
            "product_name":       detail["product_name"],
            "price":              detail["price"],
            "price_str":          detail["price_str"],
            "unit":               detail["unit"],
            "source":             "AEON Store",
            "shop_name":          "RAISA AEON Indonesia",
            "city":               "Jakarta",          # AEON Indonesia
            "product_url":        detail["product_url"],
            "image_url":          detail["image_url"],
            "kategori":           detail["kategori"],
            "scraped_at":         datetime.now().isoformat(),
        }

        # Simpan ke TinyDB (upsert: update jika URL sudah ada)
        table.upsert(row, Ingredient.product_url == row["product_url"])
        saved.append(row)

        print(f"    ✓ {row['product_name']} — {row['price_str']} ({row['unit']})")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    print(f"\n  Selesai! {len(saved)} produk disimpan untuk keyword '{keyword}'")
    return saved


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPER — untuk dipanggil dari UI Flet
# ══════════════════════════════════════════════════════════════════════════════

def get_by_keyword(keyword, db_path=DB_PATH):
    """Ambil semua data dari DB untuk keyword tertentu."""
    db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
    table = db.table("ingredients")
    return table.search(Query().ingredient_keyword == keyword)


def get_all(db_path=DB_PATH):
    """Ambil semua data ingredients dari DB."""
    db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
    return db.table("ingredients").all()


def delete_by_keyword(keyword, db_path=DB_PATH):
    """Hapus semua data untuk keyword tertentu."""
    db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
    db.table("ingredients").remove(Query().ingredient_keyword == keyword)
    print(f"Data untuk '{keyword}' dihapus.")


# ══════════════════════════════════════════════════════════════════════════════
# CONTOH PENGGUNAAN LANGSUNG
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Contoh: scrape beberapa bahan sekaligus
    keywords = ["indomie"]

    db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
    driver = init_driver()

    try:
        for kw in keywords:
            results = scrape_by_keyword(driver, kw, db)

            print(f"\nRingkasan '{kw}':")
            for r in results:
                print(f"  - {r['product_name']:40} Rp {r['price']:>10,}  {r['unit']}")

    finally:
        driver.quit()

    # Print semua data tersimpan
    print(f"\n{'='*55}")
    print(f"Total data di DB: {len(get_all())} baris")
    print(f"File: {DB_PATH}")
