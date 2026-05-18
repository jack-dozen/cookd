# Alfagift Scraper v8
# Generated with Claude (Anthropic) - claude.ai
"""
Alfagift Scraper - alfagift.id
Scrape berdasarkan keyword nama bahan (misal: "ayam", "bawang putih")
Output sesuai struktur tabel ingredients di proposal Cookd

Perubahan dari v7:
  - AI relevance picker: dari list produk hasil search, Claude API memilih
    produk yang paling cocok sebagai bahan masakan sebelum detail di-fetch.
    Ini menggantikan _is_relevant() yang berbasis string matching.
  - Hemat request: hanya detail produk yang dipilih AI yang di-fetch,
    bukan semua produk di search result.

Install dependencies:
    pip install undetected-chromedriver beautifulsoup4 tinydb anthropic
"""

import time
import random
import re
import os
import threading
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin, quote

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query


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
FRESHNESS_DAYS = 7
MAX_WORKERS    = 3

_db_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# KEYWORD GUARD
# ══════════════════════════════════════════════════════════════════════════════

_INVALID_PATTERNS = [
    r"^[\d\s\-/.,]+$",                                      # hanya angka / simbol
    r"^\d+[\-\s]+\d",                                       # range angka: "1-2", "500 - 1000"
    r"^\d+\s*(gram|gr|kg|ml|liter|pcs|pack|buah)\s*$",     # satuan saja: "500 gram"
]

def _is_valid_keyword(keyword: str) -> bool:
    kw = keyword.strip()
    if len(kw) < 2:
        return False
    for pat in _INVALID_PATTERNS:
        if re.fullmatch(pat, kw, flags=re.IGNORECASE):
            return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# AI RELEVANCE PICKER — Claude API memilih produk terbaik sebagai bahan masakan
# ══════════════════════════════════════════════════════════════════════════════

_ai_client = anthropic.Anthropic()  # baca ANTHROPIC_API_KEY dari env otomatis

def _ai_pick_best_product(keyword: str, candidates: list[dict]) -> dict | None:
    """
    Minta Claude memilih produk yang paling cocok sebagai bahan masakan
    dari list kandidat hasil search.

    Args:
        keyword    : bahan masakan yang dicari, misal "susu"
        candidates : list dict dengan key 'name', 'url', 'price_text'

    Returns:
        dict kandidat terpilih, atau None jika tidak ada yang cocok
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    numbered = "\n".join(
        f"{i+1}. {c['name']}" + (f" ({c['price_text']})" if c['price_text'] else "")
        for i, c in enumerate(candidates)
    )

    prompt = f"""Kamu adalah asisten yang membantu memilih bahan masakan.

Saya sedang mencari produk untuk bahan masakan: "{keyword}"

Berikut pilihan produk yang tersedia:
{numbered}

Pilih SATU nomor produk yang paling cocok digunakan sebagai bahan masakan "{keyword}".
Prioritaskan produk polos/plain (bukan rasa, bukan campuran, bukan minuman kemasan).
Contoh: untuk "susu", pilih susu UHT/segar/full cream, BUKAN susu coklat / susu rasa stroberi / minuman susu.

Jawab HANYA dengan satu angka saja. Jangan tambahkan penjelasan apapun."""

    try:
        response = _ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        raw    = response.content[0].text.strip()
        picked = int(re.search(r'\d+', raw).group()) - 1  # konversi ke index 0-based

        if 0 <= picked < len(candidates):
            chosen = candidates[picked]
            print(f"    [AI] Memilih: {chosen['name']}")
            return chosen
        else:
            print(f"    [AI] Index di luar range ({picked}), fallback ke kandidat pertama.")
            return candidates[0]

    except Exception as e:
        print(f"    [AI] ERROR: {e} — fallback ke kandidat pertama.")
        return candidates[0]


# ══════════════════════════════════════════════════════════════════════════════
# FRESHNESS CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _is_data_fresh(keyword: str) -> bool | None:
    """
    True  → data ada dan masih fresh (< FRESHNESS_DAYS hari)
    False → data ada tapi sudah kadaluarsa
    None  → data tidak ada
    """
    with _db_lock:
        db     = TinyDB(DB_PATH)
        result = db.table('alfagift_ingredients').get(Query().keyword == keyword)

    if result is None:
        return None

    timestamp    = datetime.strptime(result['timestamp'], '%Y-%m-%d %H:%M:%S')
    selisih_hari = (datetime.now() - timestamp).days
    return selisih_hari <= FRESHNESS_DAYS


def _delete_stale(keyword: str):
    with _db_lock:
        db = TinyDB(DB_PATH)
        db.table('alfagift_ingredients').remove(Query().keyword == keyword)


# ══════════════════════════════════════════════════════════════════════════════
# DRIVER — headless, per-thread
# ══════════════════════════════════════════════════════════════════════════════

def _init_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")                   # ← headless aktif
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=id-ID")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    return uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=CHROME_VERSION,
        headless=True,
    )


def _wait_page_ready(driver, timeout=30) -> bool:
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


def _fetch_page(driver, url, wait_seconds=2) -> BeautifulSoup:
    print(f"    Fetch: {url}")
    driver.get(url)
    time.sleep(0.5)
    _wait_page_ready(driver)
    time.sleep(wait_seconds)
    return BeautifulSoup(driver.page_source, "html.parser")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _parse_price(price_str: str) -> int:
    try:
        return int(re.sub(r'[^\d]', '', price_str))
    except Exception:
        return 0


def _detect_unit(nama: str) -> str:
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


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE HASIL PENCARIAN
# ══════════════════════════════════════════════════════════════════════════════

def _search_products(driver, keyword: str) -> list[dict]:
    encoded    = quote(keyword, safe='')
    search_url = SEARCH_URL.format(keyword=encoded)
    soup       = _fetch_page(driver, search_url, wait_seconds=3)

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

    print(f"    Ditemukan {len(results)} produk untuk keyword '{keyword}'")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPE DETAIL PRODUK
# ══════════════════════════════════════════════════════════════════════════════

def _scrape_product_detail(driver, url: str) -> dict | None:
    soup = _fetch_page(driver, url, wait_seconds=3)

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

    harga_int = _parse_price(harga_str)
    unit      = _detect_unit(nama)

    breadcrumb_items = soup.select("ol.breadcrumb li.breadcrumb-item")
    kategori = " > ".join(li.get_text(strip=True) for li in breadcrumb_items[1:-1])

    gambar_url = ""
    gambar_el  = soup.select_one(".product-detail-carousel img")
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
# CORE — satu keyword, satu driver (dipanggil di thread masing-masing)
# ══════════════════════════════════════════════════════════════════════════════

def _scrape_one(keyword: str) -> dict | None:
    """
    Scrape satu keyword. Buat dan tutup driver sendiri.
    Return dict record yang disimpan, atau None jika gagal.
    """
    print(f"\n{'='*55}")
    print(f"SCRAPE ALFAGIFT - keyword: '{keyword}'")
    print(f"{'='*55}")

    driver = None
    try:
        driver         = _init_driver()
        search_results = _search_products(driver, keyword)

        if not search_results:
            print(f"  Tidak ada produk ditemukan untuk '{keyword}'")
            return None

        # ── AI picker: pilih produk paling relevan dari search result ────
        print(f"\n  [AI] Memilih dari {len(search_results)} kandidat...")
        chosen = _ai_pick_best_product(keyword, search_results)

        if not chosen:
            print(f"  Tidak ada produk dipilih AI untuk '{keyword}'")
            return None

        # ── Fetch detail hanya untuk produk yang dipilih AI ──────────────
        print(f"\n  Fetch detail: {chosen['url']}")
        detail = _scrape_product_detail(driver, chosen["url"])
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        if not detail or not detail["product_name"]:
            print("    x Gagal ambil detail.")
            return None

        best = {
            "keyword"  : keyword,
            "name"     : detail["product_name"],
            "price"    : detail["price"],
            "url"      : detail["product_url"],
            "unit"     : detail["unit"],
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        print(f"    v {best['name']} - Rp {best['price']:,} ({best['unit']})")

        # ── Simpan ke TinyDB ──────────────────────────────────────────────
        with _db_lock:
            db    = TinyDB(DB_PATH)
            table = db.table('alfagift_ingredients')
            table.remove(Query().keyword == keyword)
            table.insert(best)
        print(f"[{keyword}] Tersimpan ke TinyDB ✓")
        return best

    except Exception as e:
        print(f"[{keyword}] ERROR: {e}")
        return None

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def scrape_keywords(keywords: list[str], max_workers: int = MAX_WORKERS) -> list[dict]:
    """
    Scrape beberapa keyword secara paralel.
    Tiap keyword mendapat driver Chrome sendiri.

    Args:
        keywords    : list keyword, contoh ['bawang putih', 'gula pasir']
        max_workers : jumlah Chrome paralel (default 3, sesuaikan RAM)

    Returns:
        list dict hasil (fresh maupun baru di-scrape)
    """
    to_scrape: list[str]  = []
    all_results: list[dict] = []

    for kw in keywords:
        # ── Keyword guard ──
        if not _is_valid_keyword(kw):
            print(f"[{kw}] SKIP — keyword tidak valid.")
            continue

        status = _is_data_fresh(kw)
        if status is True:
            print(f"[{kw}] Data masih fresh, skip scraping.")
            row = get_by_keyword(kw)
            if row:
                all_results.append(row)
        elif status is False:
            print(f"[{kw}] Data sudah > {FRESHNESS_DAYS} hari, scraping ulang...")
            _delete_stale(kw)
            to_scrape.append(kw)
        else:
            # status is None → data tidak ada
            print(f"[{kw}] Data tidak ada, mulai scraping...")
            to_scrape.append(kw)

    if not to_scrape:
        print("Semua keyword fresh, tidak ada yang perlu di-scrape.")
        return all_results

    workers = min(max_workers, len(to_scrape))
    print(f"\n[Alfagift Parallel] Scraping {len(to_scrape)} keyword "
          f"dengan {workers} worker paralel...\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_scrape_one, kw): kw for kw in to_scrape}
        for future in as_completed(futures):
            kw = futures[future]
            try:
                result = future.result()
                if result:
                    all_results.append(result)
                    print(f"[Alfagift Parallel] '{kw}' selesai ✓")
                else:
                    print(f"[Alfagift Parallel] '{kw}' tidak menghasilkan data.")
            except Exception as e:
                print(f"[Alfagift Parallel] Future error '{kw}': {e}")

    print(f"\n[Alfagift Parallel] Selesai. Total: {len(all_results)} hasil.")
    return all_results


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_by_keyword(keyword: str) -> dict | None:
    with _db_lock:
        db = TinyDB(DB_PATH)
        return db.table('alfagift_ingredients').get(Query().keyword == keyword)

def get_all() -> list[dict]:
    with _db_lock:
        db = TinyDB(DB_PATH)
        return db.table('alfagift_ingredients').all()


# ── untuk testing ──
# if __name__ == '__main__':
#     hasil = scrape_keywords(['bawang putih', 'gula pasir', 'tempe', 'garam'])
#     for h in hasil:
#         print(h)