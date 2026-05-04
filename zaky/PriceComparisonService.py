"""
PriceComparisonService.py 
═══════════════════════════════════════════════════════════════════════════════
Service layer untuk kalkulasi perbandingan harga bahan resep dari 3 toko.

Flow:
    1. Terima recipe_id → baca ingredients + portions dari tabel recipes di DB
    2. Parse setiap string bahan → qty_gram + keyword bersih
    3. Scrape paralel: Tokopedia + Alfagift + AEON
    4. Baca unit satuan produk dari DB → hitung rasio proporsional kebutuhan resep
    5. Simpan hasil ke tabel results di base.json (upsert by recipe_id)
    6. Return PriceResult berisi:
         · per_ingredient → harga per bahan per toko (nama, harga satuan, harga resep, url)
         · per_store      → harga total, harga resep, harga per porsi per toko
         · cheapest_store → toko termurah berdasarkan harga_resep

Cara pakai dari PriceController / Gui Hadi:
    from zaky.PriceComparisonService import PriceComparisonService

    service = PriceComparisonService()
    result  = service.run(
        recipe_id   = "5eef19bfb57b",
        progress_cb = lambda msg: print(msg),   # update label Flet
    )
    result.per_ingredient  # dict[keyword, list[IngredientStorePrice × 3 toko]]
    result.per_store       # dict[store,   StoreTotal]
    result.cheapest_store  # "alfagift"
═══════════════════════════════════════════════════════════════════════════════
"""

import re
import sys
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

# ── Path resolver ──────────────────────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_ROOT       = os.path.dirname(_HERE)
_RAFY_DIR   = os.path.join(_ROOT, "rafy")
_FADHIL_DIR = os.path.join(_ROOT, "fadhil")

for _p in [_ROOT, _RAFY_DIR, _FADHIL_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Import scraper ─────────────────────────────────────────────────────────────
from TokopediaScraper import tokpedia_scraper

try:
    from rafy.AlfagiftScraper import scrape_by_keyword as _alfa_scrape
    from rafy.AlfagiftScraper import init_driver as _alfa_init_driver
    _ALFA_AVAILABLE = True
except ImportError:
    _ALFA_AVAILABLE = False
    print("[PriceComparisonService] WARNING: AlfagiftScraper tidak ditemukan.")

try:
    from fadhil.AEONScraper import scrape_by_keyword as _aeon_scrape
    from fadhil.AEONScraper import init_driver as _aeon_init_driver
    _AEON_AVAILABLE = True
except ImportError:
    _AEON_AVAILABLE = False
    print("[PriceComparisonService] WARNING: AEONScraper tidak ditemukan.")

from tinydb import TinyDB, Query
_DB_PATH = os.path.join(_ROOT, "data", "base.json")


# ══════════════════════════════════════════════════════════════════════════════
# UNIT CONVERTER
# Semua satuan dikonversi ke GRAM sebagai satuan dasar kalkulasi.
# ══════════════════════════════════════════════════════════════════════════════

_UNIT_TO_GRAM: dict[str, float] = {
    # berat langsung
    "g"      : 1.0,
    "gr"     : 1.0,
    "gram"   : 1.0,
    "kg"     : 1000.0,
    "ons"    : 100.0,       # ons Indonesia = 100g

    # volume (asumsi densitas ~1 g/ml)
    "ml"     : 1.0,
    "cc"     : 1.0,
    "liter"  : 1000.0,
    "l"      : 1000.0,
    "sdm"    : 15.0,        # sendok makan ≈ 15ml
    "sdt"    : 5.0,         # sendok teh ≈ 5ml
    "gelas"  : 240.0,
    "cup"    : 240.0,

    # satuan masakan Indonesia
    "siung"  : 5.0,         # 1 siung bawang ≈ 5g
    "buah"   : 100.0,
    "biji"   : 10.0,
    "butir"  : 10.0,
    "batang" : 20.0,        # serai, daun bawang
    "lembar" : 2.0,         # daun salam, daun jeruk
    "ruas"   : 15.0,        # jahe, lengkuas
    "bonggol": 50.0,
    "ikat"   : 100.0,
    "genggam": 30.0,
    "bungkus": 200.0,
    "sachet" : 7.0,
    "kaleng" : 400.0,
    "bks"    : 200.0,
    "bh"     : 100.0,       # alias buah
    "pcs"    : 100.0,
    "pack"   : 250.0,
    "papan"  : 300.0,       # papan tempe ≈ 300g
    "lonjor" : 100.0,
    "tangkai": 10.0,
    "porsi"  : 200.0,
    "sayap"  : 60.0,        # 1 sayap ayam ≈ 60g
    "potong" : 80.0,        # 1 potong ayam ≈ 80g
    "ekor"   : 800.0,       # 1 ekor ayam ≈ 800g
}

_UNIT_ALIAS: dict[str, str] = {
    "sendok makan": "sdm",
    "sendok teh"  : "sdt",
    "sendok"      : "sdm",
    "lbr"         : "lembar",
    "btg"         : "batang",
    "btr"         : "butir",
    "bh"          : "buah",
    "bg"          : "bungkus",
    "suing"       : "siung",  # typo umum
}


def _normalize_unit(raw: str) -> str:
    u = raw.strip().lower()
    return _UNIT_ALIAS.get(u, u)


def _parse_store_unit_gram(unit_str: str) -> float:
    """
    Parse field 'unit' dari DB scraper → gram.
    Contoh: "500g" → 500.0, "1kg" → 1000.0, "per kg" → 1000.0, "" → 1000.0
    """
    if not unit_str:
        return 1000.0  # default asumsi 1kg

    s = unit_str.strip().lower()

    extra = {"per kg": 1000.0, "per gram": 1.0, "per liter": 1000.0,
             "per pcs": 100.0, "per pack": 250.0, "per buah": 100.0}
    combined = {**_UNIT_TO_GRAM, **extra}
    if s in combined:
        return combined[s]

    # parse "500g", "1.5kg", "250gr"
    m = re.match(r"([\d.,]+)\s*([a-z]+)", s)
    if m:
        try:
            qty  = float(m.group(1).replace(",", "."))
            unit = _normalize_unit(m.group(2))
            return qty * _UNIT_TO_GRAM.get(unit, 1.0)
        except ValueError:
            pass

    return 1000.0


def to_gram(qty: float, unit: str) -> float:
    """Konversi qty + unit → gram. Contoh: to_gram(3, 'siung') → 15.0"""
    return qty * _UNIT_TO_GRAM.get(_normalize_unit(unit), 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# PORTIONS PARSER
# Parse string porsi dari DB resep → int
# ══════════════════════════════════════════════════════════════════════════════

def _parse_portions(portion_str: str) -> int:
    """
    Parse field 'portion' dari resep → jumlah porsi (int).

    Contoh:
        "2 servings"  → 2
        "4 servings"  → 4
        "400 grams"   → 1   (bukan porsi orang, fallback ke 1)
        ""            → 1
        "untuk 6 org" → 6
    """
    if not portion_str:
        return 1

    # Cari angka pertama dalam string
    m = re.search(r"(\d+)", portion_str)
    if not m:
        return 1

    angka = int(m.group(1))

    # Kalau satuannya bukan "serving/porsi/orang/pax", kemungkinan berat/gram
    # → tidak relevan sebagai jumlah porsi, fallback ke 1
    portion_lower = portion_str.lower()
    satuan_porsi  = ["serving", "porsi", "orang", "pax", "person", "sajian"]
    if not any(s in portion_lower for s in satuan_porsi):
        return 1

    return max(1, angka)


# ══════════════════════════════════════════════════════════════════════════════
# INGREDIENT PARSER
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParsedIngredient:
    raw          : str
    keyword      : str    # keyword bersih untuk scraping
    qty_gram     : float  # kebutuhan resep dalam gram
    qty_original : float
    unit_original: str


_STRIP_WORDS = {
    "secukupnya", "sedikit", "sesuai", "selera", "atau", "dan",
    "iris", "cincang", "potong", "geprek", "memarkan", "parut",
    "giling", "haluskan", "sangrai", "goreng",
}

_STRIP_DESCRIPTOR = {
    "segar", "halus", "kasar", "mentah", "matang", "kering", "basah",
    "has", "dalam", "luar", "fillet", "filet", "utuh",
    "premium", "pilihan", "asli", "lokal", "impor", "organik",
    "bubuk", "instan", "sachet",
}

# Hapus keterangan dalam kurung, setelah koma, atau kata kunci tertentu
_STRIP_SUFFIX = re.compile(
    r"\s*[\(\[].*?[\)\]]"           # (keterangan dalam kurung)
    r"|\s*,.*$"                     # , apapun setelah koma
    r"|\s*/.*$"                     # / alternatif bahan
    r"|\s*\b(untuk|supaya|agar|hingga|sampai)\b.*$",
    re.IGNORECASE,
)


def parse_ingredient(raw: str) -> ParsedIngredient:
    """
    Parse satu baris bahan resep dari Cookpad.

    Contoh:
        "300 gram ayam filet(bagian paha lebih juice)" → keyword="ayam",        qty_gram=300.0
        "2 siung bawang putih(di haluskan)"            → keyword="bawang putih", qty_gram=10.0
        "1/2 kg ayam paha (aku beli yang paha)"        → keyword="ayam paha",    qty_gram=500.0
        "3 sdm kecap manis"                            → keyword="kecap manis",  qty_gram=45.0
        "1,5 sdm saus hoisin"                          → keyword="saus hoisin",  qty_gram=22.5
        "Sedikit kaldu atau garam"                     → keyword="kaldu",        qty_gram=5.0
        "secukupnya Minyak"                            → keyword="minyak",       qty_gram=15.0
        "12 sayap ayam"                                → keyword="ayam",         qty_gram=720.0
    """
    raw = raw.strip()

    # Bersihkan suffix dulu
    cleaned = _STRIP_SUFFIX.sub("", raw).strip()

    # Pola 1: pecahan biasa "1/2", "3/4"
    m = re.match(r"^(\d+)/(\d+)\s*([a-zA-Z]+)\s+(.+)$", cleaned)
    if m:
        qty  = int(m.group(1)) / int(m.group(2))
        unit = _normalize_unit(m.group(3))
        qty_gram = to_gram(qty, unit)
        keyword  = _clean_keyword(m.group(4))
        return ParsedIngredient(raw=raw, keyword=keyword, qty_gram=qty_gram,
                                qty_original=qty, unit_original=unit)

    # Pola 2: angka dengan koma desimal "1,5 sdm" atau titik "1.5 sdm"
    m = re.match(r"^(\d+[.,]\d+)\s*([a-zA-Z]+)\s+(.+)$", cleaned)
    if m:
        qty  = float(m.group(1).replace(",", "."))
        unit = _normalize_unit(m.group(2))
        qty_gram = to_gram(qty, unit)
        keyword  = _clean_keyword(m.group(3))
        return ParsedIngredient(raw=raw, keyword=keyword, qty_gram=qty_gram,
                                qty_original=qty, unit_original=unit)

    # Pola 3: angka bulat + satuan + nama  "3 siung bawang putih"
    m = re.match(r"^(\d+)\s*([a-zA-Z]+)\s+(.+)$", cleaned)
    if m:
        qty  = float(m.group(1))
        unit = _normalize_unit(m.group(2))
        qty_gram = to_gram(qty, unit)
        keyword  = _clean_keyword(m.group(3))
        return ParsedIngredient(raw=raw, keyword=keyword, qty_gram=qty_gram,
                                qty_original=qty, unit_original=unit)

    # Pola 4: angka + nama tanpa satuan  "12 sayap ayam"
    m = re.match(r"^(\d+)\s+(.+)$", cleaned)
    if m:
        qty     = float(m.group(1))
        rest    = m.group(2)
        keyword = _clean_keyword(rest)
        # Cek apakah kata pertama rest adalah satuan yang dikenal
        first_word = rest.split()[0].lower()
        if first_word in _UNIT_TO_GRAM:
            unit     = _normalize_unit(first_word)
            qty_gram = to_gram(qty, unit)
            keyword  = _clean_keyword(" ".join(rest.split()[1:]))
        else:
            # Tidak ada satuan → qty adalah jumlah buah/unit
            qty_gram = to_gram(qty, "buah")  # default per buah
            unit     = "buah"
        return ParsedIngredient(raw=raw, keyword=keyword, qty_gram=qty_gram,
                                qty_original=qty, unit_original=unit)

    # Fallback: tidak ada angka (contoh: "secukupnya Minyak", "Sedikit kaldu")
    keyword = _clean_keyword(cleaned)
    return ParsedIngredient(raw=raw, keyword=keyword, qty_gram=5.0,
                            qty_original=1.0, unit_original="sdt")


def _clean_keyword(text: str) -> str:
    """Bersihkan teks bahan → keyword scraping yang ringkas."""
    text  = _STRIP_SUFFIX.sub("", text).strip()
    words = [w for w in text.split()
             if w.lower() not in _STRIP_WORDS
             and w.lower() not in _STRIP_DESCRIPTOR]
    # Maks 2 kata — cukup untuk keyword scraping
    return " ".join(words[:2]).strip().lower()


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IngredientStorePrice:
    """
    Harga 1 bahan di 1 toko.
    Ditampilkan di popup saat user klik nama bahan.
    """
    keyword      : str
    store        : str   # "tokopedia" | "alfagift" | "aeon"
    name         : str   # nama produk di toko
    price        : int   # harga satuan penuh (Rupiah)
    price_recipe : int   # harga proporsional sesuai kebutuhan resep
    url          : str   # link → tombol Beli
    found        : bool = True


@dataclass
class StoreTotal:
    """
    Ringkasan 1 toko.
    Ditampilkan di PriceCard dan BarChart.

    4 angka yang dikembalikan:
        harga_total     → jumlah price satuan penuh semua bahan
        harga_resep     → jumlah price_recipe (proporsional) semua bahan
        harga_per_porsi → harga_resep / jumlah_porsi
        is_cheapest     → True jika toko ini paling murah (berdasarkan harga_resep)
    """
    store           : str
    harga_total     : int
    harga_resep     : int
    harga_per_porsi : int
    is_cheapest     : bool = False


@dataclass
class PriceResult:
    """
    Output utama service.run().

    Attributes:
        per_ingredient : dict[keyword, list[IngredientStorePrice × 3 toko]]
                         → popup per bahan: nama produk + harga satuan + harga resep + url
        per_store      : dict[store_name, StoreTotal]
                         → PriceCard & BarChart: 4 angka per toko
        cheapest_store : nama toko termurah
        portions       : jumlah porsi resep (hasil parse dari DB)
        recipe_name    : nama resep (untuk label UI)
        success        : False jika recipe_id tidak ditemukan atau semua scraping gagal
        error_message  : pesan error jika success=False
    """
    per_ingredient : dict = field(default_factory=dict)
    per_store      : dict = field(default_factory=dict)
    cheapest_store : str  = ""
    portions       : int  = 1
    recipe_name    : str  = ""
    success        : bool = False
    error_message  : str  = ""


# ══════════════════════════════════════════════════════════════════════════════
# DB HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _make_failed(keyword: str, store: str) -> IngredientStorePrice:
    return IngredientStorePrice(keyword=keyword, store=store, name="",
                                price=0, price_recipe=0, url="", found=False)


def _calc_price_recipe(price: int, unit_str: str, qty_gram_needed: float) -> int:
    """
    Harga proporsional = price × (qty_gram_needed / store_gram).

    Contoh:
        Toko jual 1kg (1000g), harga Rp 14.000, resep butuh 500g
        → 14.000 × (500/1000) = Rp 7.000
    """
    if price <= 0 or qty_gram_needed <= 0:
        return 0
    store_gram = _parse_store_unit_gram(unit_str) or 1000.0
    return max(1, int(round(price * (qty_gram_needed / store_gram))))


def _load_recipe(recipe_id: str) -> Optional[dict]:
    """Baca satu resep dari tabel recipes di base.json."""
    try:
        db  = TinyDB(_DB_PATH)
        row = db.table("recipes").get(Query().recipe_id == recipe_id)
        return row
    except Exception as e:
        print(f"[DB] Gagal baca resep '{recipe_id}': {e}")
        return None


def _read_tokped(keyword: str, qty_gram: float) -> IngredientStorePrice:
    try:
        row = TinyDB(_DB_PATH).table("tokped_ingredients").get(Query().keyword == keyword)
        if row and row.get("price"):
            p = int(row["price"])
            return IngredientStorePrice(
                keyword=keyword, store="tokopedia",
                name=row.get("name", ""), price=p,
                price_recipe=_calc_price_recipe(p, row.get("unit", ""), qty_gram),
                url=row.get("url", ""),
            )
    except Exception as e:
        print(f"[DB] tokped '{keyword}': {e}")
    return _make_failed(keyword, "tokopedia")


def _read_alfagift(keyword: str, qty_gram: float) -> IngredientStorePrice:
    try:
        row = TinyDB(_DB_PATH).table("alfagift_ingredients").get(Query().keyword == keyword)
        if row and row.get("price"):
            p = int(row["price"])
            return IngredientStorePrice(
                keyword=keyword, store="alfagift",
                name=row.get("name", ""), price=p,
                price_recipe=_calc_price_recipe(p, row.get("unit", ""), qty_gram),
                url=row.get("url", ""),
            )
    except Exception as e:
        print(f"[DB] alfagift '{keyword}': {e}")
    return _make_failed(keyword, "alfagift")


def _read_aeon(keyword: str, qty_gram: float) -> IngredientStorePrice:
    try:
        row = TinyDB(_DB_PATH).table("aeon_ingredients").get(Query().keyword == keyword)
        if row and row.get("price"):
            p = int(row["price"])
            return IngredientStorePrice(
                keyword=keyword, store="aeon",
                name=row.get("name", ""), price=p,
                price_recipe=_calc_price_recipe(p, row.get("unit", ""), qty_gram),
                url=row.get("url", ""),
            )
    except Exception as e:
        print(f"[DB] aeon '{keyword}': {e}")
    return _make_failed(keyword, "aeon")


def _save_results(recipe_id: str, result: PriceResult) -> None:
    """
    Simpan PriceResult ke tabel 'results' di base.json.
    Kalau recipe_id sudah ada → overwrite (upsert).
    Kalau belum ada → insert baru.

    Struktur dokumen yang disimpan:
    {
        "recipe_id"     : "5eef19bfb57b",
        "recipe_name"   : "Ayam teriyaki",
        "portions"      : 2,
        "calculated_at" : "2026-05-04 10:00:00",
        "per_ingredient": {
            "ayam": [
                { "store": "tokopedia", "name": "...", "price": 35000,
                  "price_recipe": 21000, "url": "...", "found": true },
                ...
            ],
            ...
        },
        "per_store": {
            "tokopedia": { "harga_total": 120000, "harga_resep": 85000,
                           "harga_per_porsi": 42500, "is_cheapest": false },
            ...
        }
    }
    """
    # ── Serialisasi per_ingredient ─────────────────────────────────────────────
    # per_ingredient adalah dict[keyword, list[IngredientStorePrice]]
    # TinyDB butuh plain dict, jadi dataclass dikonversi manual.
    per_ingredient_serial: dict = {}
    for keyword, store_prices in result.per_ingredient.items():
        per_ingredient_serial[keyword] = [
            {
                "store"       : isp.store,
                "name"        : isp.name,
                "price"       : isp.price,
                "price_recipe": isp.price_recipe,
                "url"         : isp.url,
                "found"       : isp.found,
            }
            for isp in store_prices
        ]

    # ── Serialisasi per_store ──────────────────────────────────────────────────
    # per_store adalah dict[store_name, StoreTotal]
    per_store_serial: dict = {}
    for store_name, store_total in result.per_store.items():
        per_store_serial[store_name] = {
            "harga_total"    : store_total.harga_total,
            "harga_resep"    : store_total.harga_resep,
            "harga_per_porsi": store_total.harga_per_porsi,
            "is_cheapest"    : store_total.is_cheapest,
        }

    # ── Dokumen final yang disimpan ────────────────────────────────────────────
    doc = {
        "recipe_id"     : recipe_id,
        "recipe_name"   : result.recipe_name,
        "portions"      : result.portions,
        "calculated_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "per_ingredient": per_ingredient_serial,
        "per_store"     : per_store_serial,
    }

    # ── Upsert ke tabel results ────────────────────────────────────────────────
    try:
        db    = TinyDB(_DB_PATH)
        table = db.table("results")
        q     = Query()

        existing = table.get(q.recipe_id == recipe_id)
        if existing:
            # Recipe sudah pernah dikalkulasi → timpa dengan data terbaru
            table.update(doc, q.recipe_id == recipe_id)
            print(f"[DB] results: overwrite recipe_id='{recipe_id}'")
        else:
            # Pertama kali → insert baru
            table.insert(doc)
            print(f"[DB] results: insert recipe_id='{recipe_id}'")
    except Exception as e:
        # Gagal simpan tidak menghentikan program — hasil tetap di-return ke UI
        print(f"[DB] Gagal simpan results '{recipe_id}': {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class PriceComparisonService:
    """
    Service utama. Dipanggil dari PriceController setelah user klik
    tombol 'Kalkulasi Harga'.

    Contoh:
        service = PriceComparisonService()
        result  = service.run(recipe_id="5eef19bfb57b", progress_cb=fn)
    """

    def run(
        self,
        recipe_id   : str,
        progress_cb : Optional[Callable[[str], None]] = None,
    ) -> PriceResult:
        """
        Entry point utama.

        Args:
            recipe_id   : ID resep dari tabel recipes di base.json
            progress_cb : Callback string untuk update label di Flet
                          Contoh pesan: "Tokopedia ✓ · Alfagift ⏳ · AEON ⏳"
        """
        def log(msg: str):
            print(f"[PriceComparisonService] {msg}")
            if progress_cb:
                progress_cb(msg)

        # ── Step 1: Baca resep dari DB ────────────────────────────────────────
        log(f"Membaca resep '{recipe_id}' dari DB...")
        recipe = _load_recipe(recipe_id)
        if not recipe:
            return PriceResult(
                success=False,
                error_message=f"Resep '{recipe_id}' tidak ditemukan di database."
            )

        ingredient_strings = recipe.get("ingredients", [])
        portion_str        = recipe.get("portion", "")
        recipe_name        = recipe.get("name", "")
        portions           = _parse_portions(portion_str)

        if not ingredient_strings:
            return PriceResult(success=False, error_message="Resep tidak punya bahan.")

        log(f"Resep: {recipe_name} | {len(ingredient_strings)} bahan | {portions} porsi")

        # ── Step 2: Parse semua bahan → keyword + qty_gram ────────────────────
        parsed   = [parse_ingredient(ing) for ing in ingredient_strings]
        keywords = [p.keyword for p in parsed]
        log(f"Keywords scraping: {keywords}")

        # ── Step 3: Scrape paralel 3 toko ─────────────────────────────────────
        try:
            self._scrape_parallel(keywords, log)
        except Exception as e:
            return PriceResult(success=False, error_message=f"Scraping gagal: {e}")

        # ── Step 4: Baca DB + hitung price_recipe per bahan ───────────────────
        qty_map = {p.keyword: p.qty_gram for p in parsed}
        per_ingredient: dict[str, list[IngredientStorePrice]] = {
            p.keyword: [
                _read_tokped(p.keyword, qty_map[p.keyword]),
                _read_alfagift(p.keyword, qty_map[p.keyword]),
                _read_aeon(p.keyword, qty_map[p.keyword]),
            ]
            for p in parsed
        }

        # ── Step 5: Hitung 4 angka per toko ───────────────────────────────────
        per_store = self._calc_store_totals(per_ingredient, portions)

        # ── Step 6: Tandai toko termurah ──────────────────────────────────────
        valid    = [s for s in per_store.values() if s.harga_resep > 0]
        cheapest = min(valid, key=lambda s: s.harga_resep) if valid else None
        if cheapest:
            cheapest.is_cheapest = True

        log("Kalkulasi selesai ✓")

        result = PriceResult(
            per_ingredient = per_ingredient,
            per_store      = per_store,
            cheapest_store = cheapest.store if cheapest else "",
            portions       = portions,
            recipe_name    = recipe_name,
            success        = True,
        )

        # ── Step 7: Simpan hasil ke tabel results di DB ───────────────────────
        log("Menyimpan hasil ke database...")
        _save_results(recipe_id, result)
        log("Hasil tersimpan ✓")

        return result

    # ── Scraping paralel ───────────────────────────────────────────────────────

    def _scrape_parallel(self, keywords: list[str], log: Callable):
        """Jalankan 3 scraper paralel, update status via log()."""
        lock   = threading.Lock()
        status = {"tokopedia": "⏳", "alfagift": "⏳", "aeon": "⏳"}

        def _progress():
            log(f"Tokopedia {status['tokopedia']} · "
                f"Alfagift {status['alfagift']} · "
                f"AEON {status['aeon']}")

        def _run_tokopedia():
            try:
                tokpedia_scraper(keywords)
                with lock: status["tokopedia"] = "✓"
            except Exception as e:
                print(f"[Tokopedia] ERROR: {e}")
                with lock: status["tokopedia"] = "✗"
            _progress()

        def _run_alfagift():
            if not _ALFA_AVAILABLE:
                with lock: status["alfagift"] = "N/A"
                _progress(); return
            driver = None
            try:
                driver = _alfa_init_driver()
                for kw in keywords:
                    _alfa_scrape(driver, kw)
                with lock: status["alfagift"] = "✓"
            except Exception as e:
                print(f"[Alfagift] ERROR: {e}")
                with lock: status["alfagift"] = "✗"
            finally:
                if driver:
                    try: driver.quit()
                    except: pass
            _progress()

        def _run_aeon():
            if not _AEON_AVAILABLE:
                with lock: status["aeon"] = "N/A"
                _progress(); return
            driver = None
            try:
                driver = _aeon_init_driver()
                for kw in keywords:
                    _aeon_scrape(driver, kw)
                with lock: status["aeon"] = "✓"
            except Exception as e:
                print(f"[AEON] ERROR: {e}")
                with lock: status["aeon"] = "✗"
            finally:
                if driver:
                    try: driver.quit()
                    except: pass
            _progress()

        _progress()
        threads = [
            threading.Thread(target=_run_tokopedia, daemon=True),
            threading.Thread(target=_run_alfagift,  daemon=True),
            threading.Thread(target=_run_aeon,      daemon=True),
        ]
        for t in threads: t.start()
        for t in threads: t.join()

    # ── Kalkulasi 4 angka per toko ─────────────────────────────────────────────

    def _calc_store_totals(
        self,
        per_ingredient : dict[str, list[IngredientStorePrice]],
        portions       : int,
    ) -> dict[str, StoreTotal]:
        """
        Hitung StoreTotal (4 angka) untuk setiap toko:
            harga_total     = jumlah price satuan penuh semua bahan
            harga_resep     = jumlah price_recipe (proporsional) semua bahan
            harga_per_porsi = harga_resep / portions
        """
        totals: dict[str, StoreTotal] = {}
        for store in ["tokopedia", "alfagift", "aeon"]:
            total_satuan = sum(
                r.price for rows in per_ingredient.values()
                for r in rows if r.store == store and r.found
            )
            total_resep = sum(
                r.price_recipe for rows in per_ingredient.values()
                for r in rows if r.store == store and r.found
            )
            per_porsi = (total_resep // portions) if portions > 0 and total_resep > 0 else 0

            totals[store] = StoreTotal(
                store           = store,
                harga_total     = total_satuan,
                harga_resep     = total_resep,
                harga_per_porsi = per_porsi,
            )
        return totals
