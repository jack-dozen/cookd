import json
import logging
import hashlib
import sys
import os
from datetime import datetime
from scrapling.fetchers import StealthyFetcher
from recipe_scrapers import scrape_html
from recipe_scrapers._exceptions import (
    ElementNotFoundInHtml,
    FieldNotProvidedByWebsiteException,
    WebsiteNotImplementedError,
    NoSchemaFoundInWildMode,
)

# ── Setup logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_URL         = "https://cookpad.com"
SEARCH_URL       = "https://cookpad.com/id/cari/{keyword}"
OUTPUT_FILE      = "../data/recipes.json"
MAX_RECIPES      = 5   # max relevant recipes to keep
MIN_MATCH_SCORE  = 0  # discard recipes where user has <x% of ingredients

# ── Fetcher setup ──────────────────────────────────────────────────────────────
StealthyFetcher.adaptive = False

# Words that are units/conjunctions, not ingredient names
SKIP_WORDS = {
    "dan", "atau", "secukupnya", "sckpnya", "sdm", "sdt", "gr",
    "kg", "ml", "liter", "buah", "butir", "siung", "lembar",
    "batang", "iris", "potong", "besar", "kecil", "sedang",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_existing(filepath: str) -> list:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log.warning("Existing JSON file is corrupted, starting fresh.")
    return []

def save_recipes(recipes: list, filepath: str):
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    os.replace(tmp, filepath)
    log.info(f"Saved {len(recipes)} recipes to {filepath}")

def merge_recipes(existing: list, new_recipes: list) -> list:
    existing_map = {r["recipe_id"]: r for r in existing}
    for recipe in new_recipes:
        existing_map[recipe["recipe_id"]] = recipe
    return list(existing_map.values())

def is_paywalled(href: str) -> bool:
    return "/premium" in href or "paywall" in href

def safe_get(scraper, field: str, default=None):
    try:
        return getattr(scraper, field)()
    except Exception:
        return default


# ── Ingredient scoring (standalone, works on a raw ingredient list) ────────────
def ingredient_score(recipe_ingredients: list[str], user_ingredients: list[str]) -> dict:
    """
    Score how many of the RECIPE'S ingredients the user already has.
    Returns score (0.0–1.0), have list, and missing list.
    """
    if not recipe_ingredients:
        return {"score": 0.0, "have": [], "missing": []}

    user_text = " ".join(user_ingredients).lower()
    have, missing = [], []

    for ingr in recipe_ingredients:
        words = ingr.lower().split()
        meaningful = [w for w in words if len(w) > 1 and w not in SKIP_WORDS]
        if any(w in user_text for w in meaningful):
            have.append(ingr)
        else:
            missing.append(ingr)

    return {
        "score":   len(have) / len(recipe_ingredients),
        "have":    have,
        "missing": missing,
    }


# ── Scraping ───────────────────────────────────────────────────────────────────
def search_recipe(keyword: str) -> list[dict]:
    """Return recipe stubs (id, name, url) from one Cookpad search page."""
    url = SEARCH_URL.format(keyword=keyword.replace(" ", "%20"))
    log.info(f"  → Searching: '{keyword}'")

    try:
        page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
    except Exception as e:
        log.error(f"Search failed for '{keyword}': {e}")
        return []

    stubs = []
    for link in page.css("a[href*='/id/resep/']"):
        try:
            href = link.attrib.get("href", "")
            if not href or is_paywalled(href):
                continue
            name = link.attrib.get("title", "").strip() or link.text.strip()
            if not name:
                continue
            full_url = BASE_URL + href if href.startswith("/") else href
            stubs.append({
                "recipe_id":  make_id(full_url),
                "name":       name,
                "source_url": full_url,
            })
        except Exception as e:
            log.warning(f"Skipping link: {e}")

    log.info(f"     {len(stubs)} stubs found")
    return stubs


def scrape_recipe_detail(stub: dict) -> dict | None:
    """
    Fetch and parse one recipe page.
    Returns the enriched dict, or None if the page could not be scraped.
    """
    url = stub["source_url"]
    log.info(f"Scraping: {stub['name']}")

    try:
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            wait_selector="div.ingredient-list",
        )
    except Exception as e:
        log.error(f"Fetch failed ({url}): {e}")
        return None

    # Get raw HTML for recipe-scrapers
    raw_html = ""
    for attr in ("content", "html"):
        try:
            raw_html = getattr(page, attr)
            break
        except AttributeError:
            pass
    if not raw_html:
        root = page.css("html")
        raw_html = root[0].html_content if root else ""

    # Try recipe-scrapers first
    scraper = None
    try:
        scraper = scrape_html(raw_html, org_url=url, supported_only=False)
    except Exception as e:
        log.warning(f"recipe-scrapers failed: {e}. Using CSS fallback.")

    if scraper:
        title       = safe_get(scraper, "title",             stub["name"])
        ingredients = safe_get(scraper, "ingredients",       [])
        steps       = safe_get(scraper, "instructions_list", [])
        author      = safe_get(scraper, "author",            "")
        yields      = safe_get(scraper, "yields",            "")
        cook_time   = safe_get(scraper, "total_time",        None)
        image_url   = safe_get(scraper, "image",             "")
        cook_time   = f"{cook_time} menit" if isinstance(cook_time, int) and cook_time else (str(cook_time) if cook_time else "")
    else:
        # CSS fallback
        ingredients = [
            " ".join(li.get_all_text().replace("\n", " ").split())
            for li in page.css("div[class*='ingredient-list'] ol li")
            if li.get_all_text().strip()
        ]
        steps = [
            p.get_all_text().strip()
            for p in page.css("#steps ol li div[dir='auto'] p")
            if p.get_all_text().strip()
        ]
        author_el  = page.css("span[dir='ltr'][class*='text-cookpad-12']")
        author     = author_el[0].text.strip() if author_el else ""
        portion_el = page.css("div[id*='serving_recipe'] [class*='text']")
        yields     = portion_el[0].text.strip() if portion_el else ""
        time_el    = page.css("div[id*='cooking_time_recipe'] [class*='text']")
        cook_time  = time_el[0].text.strip() if time_el else ""
        img_list   = page.css(".tofu_image img")
        image_url  = img_list[0].attrib.get("src", "") if img_list else ""
        title      = stub["name"]

    return {
        **stub,
        "name":        title,
        "ingredients": ingredients,
        "steps":       steps,
        "author":      author,
        "portion":     yields,
        "cook_time":   cook_time,
        "image_url":   image_url,
        "source":      "Cookpad",
        "scraped_at":  now(),
    }


def find_recipe(user_ingredients: list[str]) -> list[dict]:
    """
    Walk through search stubs ingredient-by-ingredient, scrape each detail
    page, and immediately score it. Only keep recipes where the user already
    has at least MIN_MATCH_SCORE of the required ingredients.

    This prevents irrelevant recipes (e.g. kakap miso when searching for
    "daging sapi") from ever making it into the final list.
    """
    log.info(f"Collecting relevant recipes for: {user_ingredients}")

    # Build a deduplicated queue of stubs from all per-ingredient searches
    seen_ids: set[str] = set()
    stub_queue: list[dict] = []
    for ingredient in user_ingredients:
        for stub in search_recipe(ingredient):
            if stub["recipe_id"] not in seen_ids:
                seen_ids.add(stub["recipe_id"])
                stub_queue.append(stub)

    log.info(f"Total unique stubs to evaluate: {len(stub_queue)}")

    results: list[dict] = []
    skipped = 0

    for stub in stub_queue:
        if len(results) >= MAX_RECIPES:
            break

        recipe = scrape_recipe_detail(stub)
        if not recipe:
            continue

        score_result = ingredient_score(recipe["ingredients"], user_ingredients)

        if score_result["score"] < MIN_MATCH_SCORE:
            log.info(
                f"  ✗ Skipping '{recipe['name']}' "
                f"(score {score_result['score']:.0%} < {MIN_MATCH_SCORE:.0%})"
            )
            skipped += 1
            continue

        recipe["match_score"]         = score_result["score"]
        recipe["have_ingredients"]    = score_result["have"]
        recipe["missing_ingredients"] = score_result["missing"]
        results.append(recipe)
        log.info(
            f"  ✓ Kept '{recipe['name']}' "
            f"({score_result['score']:.0%} match)"
        )

    log.info(
        f"Done — kept {len(results)} relevant recipes, "
        f"skipped {skipped} irrelevant ones."
    )
    return results


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  Cookpad Recipe Scraper")
    print("=" * 50)

    raw = sys.argv[1]
    if not raw:
        print("Tidak ada bahan yang diinput. Keluar.")
        return

    user_ingredients = [k.strip() for k in raw.split(",") if k.strip()]

    detailed = find_recipe(user_ingredients)
    if not detailed:
        print("\nTidak ada resep yang cocok ditemukan.")
        return

    detailed.sort(key=lambda x: x["match_score"], reverse=True)

    matched     = [r for r in detailed if r["match_score"] == 1.0]
    partial     = [r for r in detailed if 0.5 <= r["match_score"] < 1.0]
    recommended = [r for r in detailed if r["match_score"] < 0.5]

    print("\n" + "=" * 50)

    if matched:
        print(f"\n✅ RESEP YANG BISA DIBUAT ({len(matched)} resep):")
        for r in matched:
            print(f"   {r['name']} — kamu punya semua bahan!")

    if partial:
        print(f"\n🟡 HAMPIR LENGKAP ({len(partial)} resep):")
        for r in partial:
            percent = round(r["match_score"] * 100, 1)
            missing_clean = [i.replace("\n", " ").strip() for i in r["missing_ingredients"]]
            print(f"   {r['name']} ({percent}% bahan tersedia)")
            print(f"   Kurang: {', '.join(missing_clean)}")

    if recommended:
        print(f"\n🔴 REKOMENDASI — bahan kurang banyak ({len(recommended)} resep):")
        for r in recommended:
            percent = round(r["match_score"] * 100, 1)
            missing_clean = [i.replace("\n", " ").strip() for i in r["missing_ingredients"]]
            print(f"   {r['name']} ({percent}% bahan tersedia)")
            print(f"   Kurang: {', '.join(missing_clean)}")

    existing = load_existing(OUTPUT_FILE)
    merged   = merge_recipes(existing, detailed)
    save_recipes(merged, OUTPUT_FILE)

    print(f"\nSelesai! {len(detailed)} resep disimpan ke {OUTPUT_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()