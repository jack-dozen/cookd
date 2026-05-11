"""
PriceComparisonService.py - FIXED VERSION
"""

import re
import sys
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

_HERE       = os.path.dirname(os.path.abspath(__file__))
_ROOT       = os.path.dirname(_HERE)
_RAFY_DIR   = os.path.join(_ROOT, "rafy")
_FADHIL_DIR = os.path.join(_ROOT, "fadhil")

for _p in [_ROOT, _RAFY_DIR, _FADHIL_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from zaky.TokopediaScraper import tokpedia_scraper

try:
    from rafy.AlfagiftScraper import scrape_by_keyword as _alfa_scrape
    from rafy.AlfagiftScraper import init_driver as _alfa_init_driver
    _ALFA_AVAILABLE = True
except ImportError:
    _ALFA_AVAILABLE = False

try:
    from fadhil.AEONScraper import scrape_by_keyword as _aeon_scrape
    from fadhil.AEONScraper import init_driver as _aeon_init_driver
    _AEON_AVAILABLE = True
except ImportError:
    _AEON_AVAILABLE = False

from tinydb import TinyDB, Query
_DB_PATH = os.path.join(_ROOT, "data", "base.json")

# ── TinyDB cache (buka sekali, reuse) ─────────────────────────────────────────
_db_cache = None
_db_lock  = threading.Lock()

def _get_db() -> TinyDB:
    global _db_cache
    if _db_cache is None:
        _db_cache = TinyDB(_DB_PATH)
    return _db_cache


# ══════════════════════════════════════════════════════════════════════════════
# UNIT CONVERTER
# ══════════════════════════════════════════════════════════════════════════════

_UNIT_TO_GRAM: dict[str, float] = {
    "g": 1.0, "gr": 1.0, "gram": 1.0, "kg": 1000.0, "ons": 100.0,
    "ml": 1.0, "cc": 1.0, "liter": 1000.0, "l": 1000.0,
    "sdm": 15.0, "sdt": 5.0, "gelas": 240.0, "cup": 240.0,
    "siung": 5.0, "buah": 100.0, "biji": 10.0, "butir": 10.0,
    "batang": 20.0, "lembar": 2.0, "ruas": 15.0, "bonggol": 50.0,
    "ikat": 100.0, "genggam": 30.0, "bungkus": 200.0, "sachet": 7.0,
    "kaleng": 400.0, "bks": 200.0, "bh": 100.0, "pcs": 100.0,
    "pack": 250.0, "papan": 300.0, "lonjor": 100.0, "tangkai": 10.0,
    "porsi": 200.0, "sayap": 60.0, "potong": 80.0, "ekor": 800.0,
}

_UNIT_ALIAS: dict[str, str] = {
    "sendok makan": "sdm", "sendok teh": "sdt", "sendok": "sdm",
    "lbr": "lembar", "btg": "batang", "btr": "butir",
    "bh": "buah", "bg": "bungkus", "suing": "siung",
}


def _normalize_unit(raw: str) -> str:
    u = raw.strip().lower()
    return _UNIT_ALIAS.get(u, u)


def _parse_store_unit_gram(unit_str: str, product_name: str = "") -> float:
    """
    Parse unit dari DB scraper → gram.
    PERBAIKAN: Jika unit kosong, parse dari nama produk.
    Default 500g (bukan 1000g) — lebih realistis untuk produk retail.
    """
    if unit_str:
        s = unit_str.strip().lower()
        extra = {
            "per kg": 1000.0, "per gram": 1.0, "per liter": 1000.0,
            "per pcs": 100.0, "per pack": 250.0, "per buah": 100.0,
        }
        combined = {**_UNIT_TO_GRAM, **extra}
        if s in combined:
            return combined[s]
        m = re.match(r"([\d.,]+)\s*([a-z]+)", s)
        if m:
            try:
                qty  = float(m.group(1).replace(",", "."))
                unit = _normalize_unit(m.group(2))
                result = qty * _UNIT_TO_GRAM.get(unit, 1.0)
                if result > 0:
                    return result
            except ValueError:
                pass

    # Coba parse dari nama produk
    if product_name:
        name_lower = product_name.lower()
        # Pola: angka + satuan berat/volume dalam nama produk
        # Prioritas: kg dulu karena "500gr" bisa match "gr" dari "50gr" juga
        patterns = [
            (r"(\d+(?:[.,]\d+)?)\s*kg\b", 1000.0),
            (r"(\d+(?:[.,]\d+)?)\s*gram\b", 1.0),
            (r"(\d+(?:[.,]\d+)?)\s*gr\b", 1.0),
            (r"(\d+(?:[.,]\d+)?)\s*g\b", 1.0),
            (r"(\d+(?:[.,]\d+)?)\s*ml\b", 1.0),
            (r"(\d+(?:[.,]\d+)?)\s*liter\b", 1000.0),
            (r"(\d+(?:[.,]\d+)?)\s*l\b", 1000.0),
        ]
        for pat, multiplier in patterns:
            m = re.search(pat, name_lower)
            if m:
                try:
                    qty = float(m.group(1).replace(",", "."))
                    result = qty * multiplier
                    if result > 0:
                        return result
                except ValueError:
                    pass

    return 500.0  # default 500g (lebih realistis dari 1kg)


def to_gram(qty: float, unit: str) -> float:
    return qty * _UNIT_TO_GRAM.get(_normalize_unit(unit), 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# PORTIONS PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _parse_portions(portion_str) -> int:
    if not portion_str:
        return 1
    # Handle integer langsung (my_recipes simpan int)
    if isinstance(portion_str, int):
        return max(1, portion_str)
    m = re.search(r"(\d+)", str(portion_str))
    if not m:
        return 1
    angka = int(m.group(1))
    portion_lower = str(portion_str).lower()
    satuan_porsi = ["serving", "porsi", "orang", "pax", "person", "sajian"]
    if not any(s in portion_lower for s in satuan_porsi):
        if angka <= 20:
            return max(1, angka)
        return 1
    return max(1, angka)


# ══════════════════════════════════════════════════════════════════════════════
# INGREDIENT PARSER
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParsedIngredient:
    raw          : str
    keyword      : str
    qty_gram     : float
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

_STRIP_SUFFIX = re.compile(
    r"\s*[\(\[].*?[\)\]]"
    r"|\s*,.*$"
    r"|\s*/.*$"
    r"|\s*\b(untuk|supaya|agar|hingga|sampai)\b.*$",
    re.IGNORECASE,
)


def _is_valid_keyword(keyword: str) -> bool:
    """Validasi keyword — hindari keyword seperti '1', '2-3', '2-3 siung', dll."""
    if not keyword or len(keyword.strip()) < 2:
        return False
    # Hanya angka/simbol
    if re.fullmatch(r"[\d\s\-/.,]+", keyword):
        return False
    # Dimulai dengan pola angka-tanda hubung-angka (misal "2-3 siung")
    if re.match(r"^\d+[\-\s]+\d", keyword):
        return False
    return True


def _clean_keyword(text: str) -> str:
    text  = _STRIP_SUFFIX.sub("", text).strip()
    words = [w for w in text.split()
             if w.lower() not in _STRIP_WORDS
             and w.lower() not in _STRIP_DESCRIPTOR
             and len(w) > 1]
    return " ".join(words[:3]).strip().lower()


def parse_ingredient(raw: str) -> ParsedIngredient:
    raw = raw.strip()
    cleaned = _STRIP_SUFFIX.sub("", raw).strip()

    # Pola 1: pecahan "1/2 kg ayam"
    m = re.match(r"^(\d+)/(\d+)\s*([a-zA-Z]+)\s+(.+)$", cleaned)
    if m:
        qty  = int(m.group(1)) / int(m.group(2))
        unit = _normalize_unit(m.group(3))
        keyword = _clean_keyword(m.group(4))
        if _is_valid_keyword(keyword):
            return ParsedIngredient(raw=raw, keyword=keyword,
                                    qty_gram=to_gram(qty, unit),
                                    qty_original=qty, unit_original=unit)

    # Pola 1b: pecahan tanpa satuan "1/2 bawang bombay"
    m = re.match(r"^(\d+)/(\d+)\s+(.+)$", cleaned)
    if m:
        qty = int(m.group(1)) / int(m.group(2))
        keyword = _clean_keyword(m.group(3))
        if _is_valid_keyword(keyword):
            return ParsedIngredient(raw=raw, keyword=keyword,
                                    qty_gram=to_gram(qty, "buah"),
                                    qty_original=qty, unit_original="buah")

    # Pola 2: desimal "1,5 sdm saus hoisin"
    m = re.match(r"^(\d+[.,]\d+)\s*([a-zA-Z]+)\s+(.+)$", cleaned)
    if m:
        qty  = float(m.group(1).replace(",", "."))
        unit = _normalize_unit(m.group(2))
        keyword = _clean_keyword(m.group(3))
        if _is_valid_keyword(keyword):
            return ParsedIngredient(raw=raw, keyword=keyword,
                                    qty_gram=to_gram(qty, unit),
                                    qty_original=qty, unit_original=unit)

    # Pola 3: bulat + satuan + nama "3 siung bawang putih"
    m = re.match(r"^(\d+)\s*([a-zA-Z]+)\s+(.+)$", cleaned)
    if m:
        qty  = float(m.group(1))
        unit = _normalize_unit(m.group(2))
        if unit in _UNIT_TO_GRAM or unit in _UNIT_ALIAS:
            keyword = _clean_keyword(m.group(3))
            if _is_valid_keyword(keyword):
                return ParsedIngredient(raw=raw, keyword=keyword,
                                        qty_gram=to_gram(qty, unit),
                                        qty_original=qty, unit_original=unit)
        else:
            # Bukan satuan → nama dimulai dari token ke-2
            rest = m.group(2) + " " + m.group(3)
            keyword = _clean_keyword(rest)
            if _is_valid_keyword(keyword):
                return ParsedIngredient(raw=raw, keyword=keyword,
                                        qty_gram=to_gram(qty, "buah"),
                                        qty_original=qty, unit_original="buah")

    # Pola 4: bulat tanpa satuan "12 sayap ayam"
    m = re.match(r"^(\d+)\s+(.+)$", cleaned)
    if m:
        qty     = float(m.group(1))
        rest    = m.group(2)
        first_w = rest.split()[0].lower()
        if first_w in _UNIT_TO_GRAM:
            unit    = _normalize_unit(first_w)
            keyword = _clean_keyword(" ".join(rest.split()[1:]))
        else:
            unit    = "buah"
            keyword = _clean_keyword(rest)
        if _is_valid_keyword(keyword):
            return ParsedIngredient(raw=raw, keyword=keyword,
                                    qty_gram=to_gram(qty, unit),
                                    qty_original=qty, unit_original=unit)

    # Fallback: tanpa angka "secukupnya Minyak"
    keyword = _clean_keyword(cleaned)
    if not _is_valid_keyword(keyword):
        keyword = re.sub(r"^\d+\s*", "", cleaned).strip().lower()
    return ParsedIngredient(raw=raw, keyword=keyword, qty_gram=5.0,
                            qty_original=1.0, unit_original="sdt")


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IngredientStorePrice:
    keyword      : str
    store        : str
    name         : str
    price        : int
    price_recipe : int
    url          : str
    found        : bool = True


@dataclass
class StoreTotal:
    store           : str
    harga_total     : int
    harga_resep     : int
    harga_per_porsi : int
    is_cheapest     : bool = False


@dataclass
class PriceResult:
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


def _calc_price_recipe(price: int, unit_str: str, qty_gram_needed: float,
                        product_name: str = "") -> int:
    """
    Harga proporsional = price × (qty_gram_needed / store_gram).
    PERBAIKAN:
    - Parse unit dari nama produk jika unit_str kosong
    - Sanity check: hasil tidak boleh > 10× harga satuan
    """
    if price <= 0 or qty_gram_needed <= 0:
        return 0
    store_gram = _parse_store_unit_gram(unit_str, product_name)
    if store_gram <= 0:
        store_gram = 500.0

    ratio  = qty_gram_needed / store_gram
    result = price * ratio

    # Sanity check: kalau hasil > 10× harga satuan, ada bug di parsing unit
    if result > price * 10:
        print(f"[WARNING] price_recipe ({result:,.0f}) > 10x price ({price:,}) "
              f"untuk unit='{unit_str}', name='{product_name}', qty={qty_gram_needed}g. "
              f"Gunakan harga satuan sebagai batas atas.")
        return price

    return max(1, int(round(result)))


def _load_recipe(recipe_id: str) -> Optional[dict]:
    try:
        db = _get_db()
        for table_name in ["recipes", "cookpad_recipes", "cookpad_temp", "my_recipes"]:
            try:
                row = db.table(table_name).get(Query().recipe_id == recipe_id)
                if row:
                    return row
            except Exception:
                pass

        import json
        with open(_DB_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        for table_data in raw.values():
            if isinstance(table_data, dict):
                for item in table_data.values():
                    if isinstance(item, dict) and item.get("recipe_id") == recipe_id:
                        return item
    except Exception as e:
        print(f"[DB] Gagal baca resep '{recipe_id}': {e}")
    return None


def _extract_ingredient_strings(recipe: dict) -> list[str]:
    ingredients = recipe.get("ingredients", [])
    if not ingredients:
        return []
    if all(isinstance(item, str) for item in ingredients):
        return ingredients
    normalized: list[str] = []
    for item in ingredients:
        if isinstance(item, dict):
            qty  = str(item.get("qty", "")).strip()
            name = str(item.get("name", "")).strip()
            if qty and name:
                normalized.append(f"{qty} {name}")
            elif name:
                normalized.append(name)
            elif qty:
                normalized.append(qty)
        else:
            normalized.append(str(item).strip())
    return normalized


def _read_tokped(keyword: str, qty_gram: float) -> IngredientStorePrice:
    """Tokopedia tidak simpan 'unit' → parse dari nama produk."""
    if not _is_valid_keyword(keyword):
        return _make_failed(keyword, "tokopedia")
    try:
        with _db_lock:
            row = _get_db().table("tokped_ingredients").get(Query().keyword == keyword)
        if row and row.get("price") and int(row["price"]) > 0:
            p    = int(row["price"])
            name = row.get("name", "")
            unit = row.get("unit", "")   # biasanya kosong
            return IngredientStorePrice(
                keyword=keyword, store="tokopedia",
                name=name, price=p,
                price_recipe=_calc_price_recipe(p, unit, qty_gram, name),
                url=row.get("url", ""),
            )
    except Exception as e:
        print(f"[DB] tokped '{keyword}': {e}")
    return _make_failed(keyword, "tokopedia")


def _read_alfagift(keyword: str, qty_gram: float) -> IngredientStorePrice:
    """Skip jika price = 0 (scraping gagal)."""
    if not _is_valid_keyword(keyword):
        return _make_failed(keyword, "alfagift")
    try:
        with _db_lock:
            row = _get_db().table("alfagift_ingredients").get(Query().keyword == keyword)
        if row and row.get("price") and int(row["price"]) > 0:
            p    = int(row["price"])
            name = row.get("name", "")
            unit = row.get("unit", "")
            return IngredientStorePrice(
                keyword=keyword, store="alfagift",
                name=name, price=p,
                price_recipe=_calc_price_recipe(p, unit, qty_gram, name),
                url=row.get("url", ""),
            )
    except Exception as e:
        print(f"[DB] alfagift '{keyword}': {e}")
    return _make_failed(keyword, "alfagift")


def _read_aeon(keyword: str, qty_gram: float) -> IngredientStorePrice:
    """Skip jika price = 0."""
    if not _is_valid_keyword(keyword):
        return _make_failed(keyword, "aeon")
    try:
        with _db_lock:
            row = _get_db().table("aeon_ingredients").get(Query().keyword == keyword)
        if row and row.get("price") and int(row["price"]) > 0:
            p    = int(row["price"])
            name = row.get("name", "")
            unit = row.get("unit", "")
            return IngredientStorePrice(
                keyword=keyword, store="aeon",
                name=name, price=p,
                price_recipe=_calc_price_recipe(p, unit, qty_gram, name),
                url=row.get("url", ""),
            )
    except Exception as e:
        print(f"[DB] aeon '{keyword}': {e}")
    return _make_failed(keyword, "aeon")


def _save_results(recipe_id: str, result: PriceResult) -> None:
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
    per_store_serial: dict = {}
    for store_name, store_total in result.per_store.items():
        per_store_serial[store_name] = {
            "harga_total"    : store_total.harga_total,
            "harga_resep"    : store_total.harga_resep,
            "harga_per_porsi": store_total.harga_per_porsi,
            "is_cheapest"    : store_total.is_cheapest,
        }
    doc = {
        "recipe_id"     : recipe_id,
        "recipe_name"   : result.recipe_name,
        "portions"      : result.portions,
        "calculated_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "per_ingredient": per_ingredient_serial,
        "per_store"     : per_store_serial,
    }
    try:
        with _db_lock:
            db    = _get_db()
            table = db.table("results")
            q     = Query()
            existing = table.get(q.recipe_id == recipe_id)
            if existing:
                table.update(doc, q.recipe_id == recipe_id)
            else:
                table.insert(doc)
            print(f"[DB] results: saved recipe_id='{recipe_id}'")
    except Exception as e:
        print(f"[DB] Gagal simpan results '{recipe_id}': {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class PriceComparisonService:

    def run(
        self,
        recipe_id   : str,
        progress_cb : Optional[Callable[[str], None]] = None,
    ) -> PriceResult:

        def log(msg: str):
            print(f"[PriceComparisonService] {msg}")
            if progress_cb:
                progress_cb(msg)

        log(f"Membaca resep '{recipe_id}' dari DB...")
        recipe = _load_recipe(recipe_id)
        if not recipe:
            return PriceResult(
                success=False,
                error_message=f"Resep '{recipe_id}' tidak ditemukan di database."
            )

        ingredient_strings = _extract_ingredient_strings(recipe)
        portion_str        = recipe.get("portion", "")
        recipe_name        = recipe.get("name", "")
        portions           = _parse_portions(portion_str)

        if not ingredient_strings:
            return PriceResult(success=False, error_message="Resep tidak punya bahan.")

        log(f"Resep: {recipe_name} | {len(ingredient_strings)} bahan | {portions} porsi")

        # Parse + filter keyword valid
        parsed = [parse_ingredient(ing) for ing in ingredient_strings]
        parsed_valid = [p for p in parsed if _is_valid_keyword(p.keyword)]
        invalid = [p for p in parsed if not _is_valid_keyword(p.keyword)]
        if invalid:
            print(f"[PriceComparisonService] SKIP invalid: {[p.raw for p in invalid]}")

        if not parsed_valid:
            return PriceResult(success=False, error_message="Tidak ada bahan yang bisa diparse.")

        # Deduplicate keywords, preserve order
        seen = set()
        keywords = []
        for p in parsed_valid:
            if p.keyword not in seen:
                seen.add(p.keyword)
                keywords.append(p.keyword)

        log(f"Keywords ({len(keywords)}): {keywords}")

        try:
            self._scrape_parallel(keywords, log)
        except Exception as e:
            return PriceResult(success=False, error_message=f"Scraping gagal: {e}")

        log("Scraping selesai, mulai kalkulasi harga...")

        # qty_map: keyword → qty_gram (ambil yang pertama jika duplikat)
        qty_map = {}
        for p in parsed_valid:
            if p.keyword not in qty_map:
                qty_map[p.keyword] = p.qty_gram

        per_ingredient: dict[str, list[IngredientStorePrice]] = {}
        for keyword, qty_gram in qty_map.items():
            tokped   = _read_tokped(keyword, qty_gram)
            alfagift = _read_alfagift(keyword, qty_gram)
            aeon     = _read_aeon(keyword, qty_gram)

            if not any([tokped.found, alfagift.found, aeon.found]):
                print(f"[PriceComparisonService] '{keyword}' tidak ditemukan di semua toko.")

            per_ingredient[keyword] = [tokped, alfagift, aeon]

        log(f"Selesai kalkulasi {len(per_ingredient)} bahan")

        per_store = self._calc_store_totals(per_ingredient, portions)
        log("Total per toko selesai")

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

        log("Menyimpan hasil ke database...")
        _save_results(recipe_id, result)
        log("Hasil tersimpan ✓")

        return result

    def _scrape_parallel(self, keywords: list[str], log: Callable):
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

    def _calc_store_totals(
        self,
        per_ingredient : dict[str, list[IngredientStorePrice]],
        portions       : int,
    ) -> dict[str, StoreTotal]:
        """
        Hitung StoreTotal per toko.

        Kalau suatu bahan tidak ditemukan di satu toko (found=False),
        dan bahan itu ditemukan di ≥ 1 toko lain, gunakan MEDIAN harga_recipe
        dari toko yang punya data sebagai estimasi — tapi hanya kalau
        bahan yang N/A ≤ 50% dari total bahan (kalau terlalu banyak yang missing,
        estimasi tidak bisa dipercaya → tetap tampilkan N/A / 0).
        """
        stores = ["tokopedia", "alfagift", "aeon"]
        totals: dict[str, StoreTotal] = {}

        for store in stores:
            total_satuan = 0
            total_resep  = 0
            missing_count = 0
            total_count   = 0

            for keyword, rows in per_ingredient.items():
                total_count += 1
                # Cari data bahan ini untuk toko ini
                own = next((r for r in rows if r.store == store), None)

                if own and own.found and own.price > 0:
                    total_satuan += own.price
                    total_resep  += own.price_recipe
                else:
                    missing_count += 1
                    # Coba fallback median dari toko lain yang punya data
                    other_prices = [
                        r.price_recipe for r in rows
                        if r.store != store and r.found and r.price_recipe > 0
                    ]
                    if other_prices:
                        # Median dari toko lain sebagai estimasi
                        other_prices.sort()
                        median_price = other_prices[len(other_prices) // 2]
                        # Gunakan median hanya kalau proporsi missing masih wajar
                        # (keputusan akhir ditentukan setelah hitung semua bahan)
                        total_resep  += median_price
                        # Untuk harga total, estimasi dari median resep × rasio umum
                        # (median_price sudah proporsional, kalikan 3 sebagai kasar)
                        total_satuan += median_price * 3

            # Kalau > 80% bahan missing di toko ini → set ke 0 (data tidak cukup)
            if total_count > 0 and missing_count / total_count > 0.8:
                total_satuan = 0
                total_resep  = 0

            per_porsi = (total_resep // portions) if portions > 0 and total_resep > 0 else 0
            totals[store] = StoreTotal(
                store           = store,
                harga_total     = total_satuan,
                harga_resep     = total_resep,
                harga_per_porsi = per_porsi,
            )
        return totals
