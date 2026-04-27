# Alfagift Scraper v6
# Generated with Claude (Anthropic) - claude.ai
"""
Alfagift Scraper - alfagift.id
Scrape berdasarkan keyword nama bahan (misal: "ayam", "bawang putih")
Output sesuai struktur tabel ingredients di proposal Cookd

Install dependencies:
    pip install undetected-chromedriver beautifulsoup4 tinydb
"""

import time
import json
import random
import re
import os
from datetime import datetime
from urllib.parse import urljoin, quote

import undetected_chromedriver as uc  # Chrome driver yang susah dideteksi bot
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup          # Parser HTML
from tinydb import TinyDB, Query       # Database JSON ringan
from tinydb.storages import JSONStorage

# ══════════════════════════════════════════════════════════════════════════════
# PRETTY JSON STORAGE
# ══════════════════════════════════════════════════════════════════════════════

class PrettyJSONStorage(JSONStorage):
    def write(self, data):
        self._handle.seek(0)
        json.dump(data, self._handle, indent=2, ensure_ascii=False)  # Simpan JSON rapi + support karakter Indonesia
        self._handle.flush()
        self._handle.truncate()

# ══════════════════════════════════════════════════════════════════════════════
# KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL       = "https://www.alfagift.id"
SEARCH_URL     = "https://www.alfagift.id/find/{keyword}"  # URL search Alfagift, {keyword} diganti saat runtime
DB_PATH        = os.path.join(os.path.dirname(__file__), "ingredients.json")  # DB di folder yang sama dengan script
CHROME_VERSION = 147               # Harus sesuai versi Chrome yang terinstall
MAX_RESULTS    = 3                 # Jumlah produk yang di-scrape per keyword sebelum difilter
DELAY_MIN      = 1.0
DELAY_MAX      = 2.0               # Jeda acak antar request agar tidak diblokir

# ══════════════════════════════════════════════════════════════════════════════
# DRIVER
# ══════════════════════════════════════════════════════════════════════════════

def init_driver():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=id-ID")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")  # Sembunyikan tanda automation
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"  # Pura-pura browser biasa
    )
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=CHROME_VERSION,
        headless=True,  # Jalankan Chrome tanpa tampilan (background)
    )
    return driver


def wait_page_ready(driver, timeout=30):
    """Tunggu sampai halaman selesai dimuat, bukan Cloudflare challenge."""
    print("    Menunggu halaman...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        title = driver.title.lower()
        if not any(k in title for k in ["checking", "just a moment", "cloudflare"]):  # Kalau bukan halaman challenge, lanjut
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
    time.sleep(wait_seconds)                                 # Tunggu JS selesai render
    return BeautifulSoup(driver.page_source, "html.parser")  # Ambil HTML dan parse


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE HASIL PENCARIAN
# ══════════════════════════════════════════════════════════════════════════════

def search_products(driver, keyword):
    """Buka halaman search Alfagift, kumpulkan URL + nama produk."""
    encoded = quote(keyword, safe='')                      # Encode spasi & karakter khusus untuk URL
    search_url = SEARCH_URL.format(keyword=encoded)

    soup = fetch_page(driver, search_url, wait_seconds=3)

    results = []
    seen = set()  # Hindari URL duplikat

    for link in soup.select("a[href^='/p/']"):             # Cari semua link produk (href diawali /p/)
        href = link.get("href", "")

        if not href or href == "/p/search" or "search?q" in href:  # Skip link bukan produk
            continue

        full_url = urljoin(BASE_URL, href)
        if full_url in seen:                               # Skip kalau URL sudah masuk list
            continue
        seen.add(full_url)

        name_el = link.select_one("p, span, h3, h2")      # Ambil nama dari elemen teks pertama dalam kartu
        name = name_el.get_text(strip=True) if name_el else link.get_text(strip=True)

        price_el = link.select_one("[class*='price'], [class*='Price']")  # Harga di kartu (opsional)
        price_text = price_el.get_text(strip=True) if price_el else ""

        if not name:
            continue

        results.append({"url": full_url, "name": name, "price_text": price_text})

        if len(results) >= MAX_RESULTS:                    # Stop kalau sudah cukup
            break

    print(f"    Ditemukan {len(results)} produk untuk keyword '{keyword}'")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE DETAIL PRODUK
# ══════════════════════════════════════════════════════════════════════════════

def parse_price(price_str):
    """Ubah string harga 'Rp 12.500' -> int 12500."""
    try:
        cleaned = re.sub(r'[^\d]', '', price_str)          # Hapus semua karakter selain angka
        return int(cleaned)
    except Exception:
        return 0


def detect_unit(nama):
    """Deteksi satuan dari nama produk (misal '100g', 'pouch', 'pcs')."""
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
    """
    Buka halaman produk, ambil nama/harga/kategori/gambar.
    Selector berdasarkan HTML asli alfagift.id (Nuxt.js/Vue, 2025).
    """
    soup = fetch_page(driver, url, wait_seconds=3)

    # Nama produk - class berbeda untuk desktop vs mobile, ambil salah satu
    nama_el = (
        soup.select_one("p.text-xlg.fw7") or   # versi desktop
        soup.select_one("p.text-xl.fw5")        # versi mobile
    )
    nama = nama_el.get_text(strip=True) if nama_el else ""

    if not nama or any(k in nama.lower() for k in ["not found", "404", "halaman tidak"]):
        return None  # Halaman error, skip produk ini

    # Harga - pakai class text-primary sebagai pembeda dari teks lain
    harga_el = soup.select_one("p.text-xlg.fw7.text-primary")
    harga_str = harga_el.get_text(strip=True) if harga_el else ""

    if not harga_str:  # Fallback kalau selector utama tidak ketemu
        for el in soup.find_all(["p", "span"]):
            teks = el.get_text(strip=True)
            if teks.startswith("Rp"):
                harga_str = teks
                break

    harga_int = parse_price(harga_str)

    unit = detect_unit(nama)

    # Breadcrumb - skip Home (index 0) dan nama produk sendiri (index -1)
    breadcrumb_items = soup.select("ol.breadcrumb li.breadcrumb-item")
    kategori = " > ".join(li.get_text(strip=True) for li in breadcrumb_items[1:-1])

    # Gambar utama produk
    gambar_url = ""
    gambar_el = soup.select_one(".product-detail-carousel img")
    if gambar_el:
        gambar_url = gambar_el.get("data-src") or gambar_el.get("src", "")

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
# CHEAPEST FILTER
# Dari semua produk yang di-scrape, pilih yang paling murah
# ══════════════════════════════════════════════════════════════════════════════

def pick_cheapest(products):
    valids = [p for p in products if p["price"] > 0]      # Buang produk yang harganya 0 / gagal parse
    return min(valids, key=lambda p: p["price"]) if valids else None  # Ambil harga terkecil


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA: scrape_by_keyword
# ══════════════════════════════════════════════════════════════════════════════

def scrape_by_keyword(driver, keyword, db=None, use_cheapest_filter=True):
    """
    Scrape produk Alfagift berdasarkan keyword, simpan ke TinyDB.
    Jika use_cheapest_filter=True, hanya simpan 1 produk termurah.
    """
    if db is None:
        db = TinyDB(DB_PATH, storage=PrettyJSONStorage)

    table = db.table("ingredients")
    Ingredient = Query()

    print(f"\n{'='*55}")
    print(f"SCRAPE ALFAGIFT - keyword: '{keyword}'")
    print(f"{'='*55}")

    # Cek cache - kalau keyword sudah di-scrape hari ini, skip
    today = datetime.now().strftime("%Y-%m-%d")
    existing = table.search(
        (Ingredient.ingredient_keyword == keyword) &
        (Ingredient.source == "Alfagift") &
        (Ingredient.scraped_at.test(lambda x: x.startswith(today)))  # Bandingkan tanggal saja
    )
    if existing:
        print(f"  Cache hit: {len(existing)} data sudah ada untuk hari ini.")
        return existing

    search_results = search_products(driver, keyword)
    if not search_results:
        print(f"  Tidak ada produk ditemukan untuk '{keyword}'")
        return []

    scraped = []

    for i, result in enumerate(search_results, 1):
        print(f"\n  [{i}/{len(search_results)}] {result['url']}")
        detail = scrape_product_detail(driver, result["url"])

        if not detail or not detail["product_name"]:
            print(f"    x Gagal ambil detail, skip.")
            continue

        row = {
            "ingredient_keyword": keyword,
            "product_name":       detail["product_name"],
            "price":              detail["price"],
            "price_str":          detail["price_str"].replace("\xa0", " ").strip(),  # Bersihkan non-breaking space
            "unit":               detail["unit"],
            "source":             "Alfagift",
            "shop_name":          "Alfamart",
            "city":               "Indonesia",
            "product_url":        detail["product_url"],
            "image_url":          detail["image_url"],
            "kategori":           detail["kategori"],
            "scraped_at":         datetime.now().isoformat(),
        }

        scraped.append(row)
        print(f"    v {row['product_name']} - {row['price_str']} ({row['unit']})")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))   # Jeda acak antar produk

    # Filter ke 1 produk termurah sebelum disimpan
    to_save = scraped
    if use_cheapest_filter and len(scraped) > 1:
        best = pick_cheapest(scraped)
        print(f"\n  [Cheapest filter] Produk terpilih: {best['product_name']} - {best['price_str']}")
        to_save = [best]

    # Simpan ke DB - upsert agar tidak duplikat berdasarkan URL produk
    saved = []
    for row in to_save:
        table.upsert(row, Ingredient.product_url == row["product_url"])
        saved.append(row)

    print(f"\n  Selesai! {len(saved)} produk disimpan untuk keyword '{keyword}'")
    return saved


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_by_keyword(keyword, db_path=DB_PATH):
    """Ambil data dari DB untuk keyword tertentu."""
    db = TinyDB(db_path, storage=PrettyJSONStorage)
    table = db.table("ingredients")
    return table.search(
        (Query().ingredient_keyword == keyword) &
        (Query().source == "Alfagift")
    )


def get_all(db_path=DB_PATH):
    """Ambil semua data ingredients dari DB."""
    db = TinyDB(db_path, storage=PrettyJSONStorage)
    return db.table("ingredients").all()


def delete_by_keyword(keyword, db_path=DB_PATH):
    """Hapus semua data Alfagift untuk keyword tertentu."""
    db = TinyDB(db_path, storage=PrettyJSONStorage)
    db.table("ingredients").remove(
        (Query().ingredient_keyword == keyword) &
        (Query().source == "Alfagift")
    )
    print(f"Data Alfagift untuk '{keyword}' dihapus.")


# ══════════════════════════════════════════════════════════════════════════════
# CONTOH PENGGUNAAN LANGSUNG
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    keywords = ["wortel", "tepung tapioka"]

    db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
    driver = init_driver()

    try:
        for kw in keywords:
            results = scrape_by_keyword(driver, kw, db)

            print(f"\nRingkasan '{kw}':")
            for r in results:
                print(f"  - {r['product_name']:40} Rp {r['price']:>10,}  {r['unit']}")

    finally:
        try:
            driver.quit()       # Tutup Chrome
        except Exception:
            pass
        driver = None           # Cegah double-quit saat garbage collection

    print(f"\n{'='*55}")
    print(f"Total data di DB: {len(get_all())} baris")
    print(f"File: {DB_PATH}")