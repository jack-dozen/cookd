import json
import logging
import hashlib
import sys
import os
from tinydb import TinyDB, Query
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
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')
MAX_RECIPES      = 10   # max relevant recipes to keep
MIN_MATCH_SCORE  = 0.01  # discard recipes where user has <x% of ingredients

# ── Fetcher setup ──────────────────────────────────────────────────────────────
StealthyFetcher.adaptive = False

# Words that are units/conjunctions, not ingredient names
SKIP_WORDS = {
    "dan", "atau", "secukupnya", "sckpnya", "sdm", "sdt", "gr",
    "kg", "ml", "liter", "buah", "butir", "siung", "lembar",
    "batang", "iris", "potong", "besar", "kecil", "sedang",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_existing(filepath: str):
    db = TinyDB(filepath)
    return db

def save_recipes(db, new_recipes: list, temp: list):
    cookpad_table = db.table('cookpad_recipes')
    cookpad_temp  = db.table('cookpad_temp')
    
    existing_urls = {r['source_url'] for r in cookpad_table.all()}
    for recipe in new_recipes:
        if recipe['source_url'] not in existing_urls:
            cookpad_table.insert(recipe)
    
    cookpad_temp.truncate()
    for item in temp:
        cookpad_temp.insert({k: v for k, v in item.items() if k != 'doc_id'})

def search_local(user_ingredients: list[str], db) -> list[dict]:
    results = []
    for recipe in db.table('cookpad_recipes').all():
        score_result = ingredient_score(recipe["ingredients"], user_ingredients)
        if score_result["score"] >= MIN_MATCH_SCORE:
            r = recipe.copy()
            r["match_score"]         = score_result["score"]
            r["have_ingredients"]    = score_result["have"]
            r["missing_ingredients"] = score_result["missing"]
            results.append(r)
    return sorted(results, key=lambda x: x["match_score"], reverse=True)[:MAX_RECIPES]

def merge_recipes(base: dict, new_recipes: list) -> dict:
    table = base.get("cookpad_recipes", {})
    existing_urls = {r["source_url"] for r in table.values()}
    next_id = max((int(k) for k in table.keys()), default=0) + 1
    for recipe in new_recipes:
        if recipe["source_url"] not in existing_urls:
            table[str(next_id)] = recipe
            next_id += 1
    base["cookpad_recipes"] = table
    return base

def is_paywalled(href: str) -> bool:
    return "/premium" in href or "paywall" in href

def safe_get(scraper, field: str, default=None):
    try:
        return getattr(scraper, field)()
    except Exception:
        return default


# ── Ingredient scoring (standalone, works on a raw ingredient list) ────────────
def ingredient_score(recipe_ingredients: list, user_ingredients: list[str]) -> dict:
    if not recipe_ingredients:
        return {"score": 0.0, "have": [], "missing": []}

    user_text = " ".join(user_ingredients).lower()
    have, missing = [], []

    for ingr in recipe_ingredients:
        # Handle both dict {"qty": ..., "name": ...} and plain string
        text = ingr["name"].lower() if isinstance(ingr, dict) else ingr.lower()
        words = text.split()
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
        title     = safe_get(scraper, "title",      stub["name"])
        author    = safe_get(scraper, "author",      "")
        yields    = safe_get(scraper, "yields",      "")
        cook_time = safe_get(scraper, "total_time",  None)
        image_url = safe_get(scraper, "image",       "")
        cook_time = f"{cook_time} menit" if isinstance(cook_time, int) and cook_time else (str(cook_time) if cook_time else "")
    else:
        title     = stub["name"]
        author    = ""
        yields    = ""
        cook_time = ""
        image_url = ""

    # Always use CSS for ingredients and steps (structured data)
    ingredients = []
    for li in page.css("div[class*='ingredient-list'] ol li"):
        qty_el  = li.css("bdi")
        name_el = li.css("span")
        bold_el = li.css("b, strong")
        
        qty  = qty_el[0].text.strip() if qty_el else ""
        
        if name_el:
            # Use get_all_text() to capture text inside nested <a> tags too
            name = name_el[0].get_all_text().strip()
        else:
            name = ""
        
        if not name_el and bold_el and not qty:
            ingredients.append({"qty": "", "name": bold_el[0].get_all_text().strip(), "is_header": True})
            continue
        
        if not name:
            name = li.get_all_text().strip()
        
        if name:
            ingredients.append({"qty": qty, "name": name})

    steps = []
    for li in page.css("#steps ol li"):
        p    = li.css("div[dir='auto'] p")
        attachments = li.css(".step-attachments-list a.block")
        step = {}
        if p:
            step["text"] = p[0].get_all_text().strip()
        
        images = []
        videos = []
        for a in attachments:
            href = a.attrib.get("href", "")
            img = a.css("img")
            src = img[0].attrib.get("src", "") if img else ""
            if "/step_attachment/videos/" in href:
                videos.append({"thumb": src, "href": BASE_URL + href if href.startswith("/") else href})
            elif src:
                images.append(src)
        
        if images:
            step["images"] = images
        if videos:
            step["videos"] = videos
        if step.get("text"):
            steps.append(step)

    # Fallback for fields not covered by scraper
    if not author:
        author_el = page.css("span[dir='ltr'][class*='text-cookpad-12']")
        author    = author_el[0].text.strip() if author_el else ""
    if not yields:
        portion_el = page.css("div[id*='serving_recipe'] [class*='text']")
        yields     = portion_el[0].text.strip() if portion_el else ""
    if not cook_time:
        time_el   = page.css("div[id*='cooking_time_recipe'] [class*='text']")
        cook_time = time_el[0].text.strip() if time_el else ""
    if not image_url:
        img_list  = page.css(".tofu_image img")
        image_url = img_list[0].attrib.get("src", "") if img_list else ""
                
        author_el  = page.css("span[dir='ltr'][class*='text-cookpad-12']")
        author     = author_el[0].text.strip() if author_el else ""
        portion_el = page.css("div[id*='serving_recipe'] [class*='text']")
        yields     = portion_el[0].text.strip() if portion_el else ""
        time_el    = page.css("div[id*='cooking_time_recipe'] [class*='text']")
        cook_time  = time_el[0].text.strip() if time_el else ""
        img_list   = page.css(".tofu_image img")
        image_url  = img_list[0].attrib.get("src", "") if img_list else ""
        title      = stub["name"]
    if not image_url and scraper:
        image_url = safe_get(scraper, "image", "")

    return {
        **stub,
        "name":        title,
        "ingredients": ingredients,
        "steps":       steps,
        "author":      author,
        "portion":     yields if yields     else "-",
        "cook_time":   cook_time if cook_time  else "-",
        "image_url":   image_url,
        "source":      "Cookpad",
        "scraped_at":  now(),
    }


def find_recipe(user_ingredients: list[str], on_recipe_found=None) -> list[dict]:
    db = TinyDB(OUTPUT_FILE)
    cookpad_table = db.table('cookpad_recipes')

    # Build a url lookup for local recipes
    local_map = {r["source_url"]: r for r in cookpad_table.all()}

    results = []
    seen_urls = set()

    for ingredient in user_ingredients:
        if len(results) >= MAX_RECIPES:
            break
        for stub in search_recipe(ingredient):
            if len(results) >= MAX_RECIPES:
                break
            if stub["source_url"] in seen_urls:
                continue
            seen_urls.add(stub["source_url"])

            # ── Check local first ──
            if stub["source_url"] in local_map:
                log.info(f"Local hit: {stub['name']}")
                recipe = local_map[stub["source_url"]]
            else:
                # ── Not local → scrape detail ──
                recipe = scrape_recipe_detail(stub)
                if not recipe:
                    continue
            #log.info(f"Ingredients: {recipe['ingredients'][:2]}")            
            score_result = ingredient_score(recipe["ingredients"], user_ingredients)
            log.info(f"Score: {score_result['score']} for {stub['name']}")
            if score_result["score"] < MIN_MATCH_SCORE:
                log.info(f"Skipped (score too low)") 
                continue

            recipe["match_score"]         = score_result["score"]
            recipe["have_ingredients"]    = score_result["have"]
            recipe["missing_ingredients"] = score_result["missing"]
            results.append(recipe)
            if on_recipe_found:  # ← call GUI immediately
                on_recipe_found(recipe)
    # Save new recipes to DB
    
    save_recipes(db, [r for r in results if r["source_url"] not in local_map], results)
    db.close()

    return sorted(results, key=lambda x: x["match_score"], reverse=True)[:MAX_RECIPES]
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
            missing_clean = [
                (i["name"] if isinstance(i, dict) else i).replace("\n", " ").strip()
                for i in r["missing_ingredients"]
            ]
            print(f"   {r['name']} ({percent}% bahan tersedia)")
            print(f"   Kurang: {', '.join(missing_clean)}")

    if recommended:
        print(f"\n🔴 REKOMENDASI — bahan kurang banyak ({len(recommended)} resep):")
        for r in recommended:
            percent = round(r["match_score"] * 100, 1)
            missing_clean = [
                (i["name"] if isinstance(i, dict) else i).replace("\n", " ").strip()
                for i in r["missing_ingredients"]
            ]
            print(f"   {r['name']} ({percent}% bahan tersedia)")
            print(f"   Kurang: {', '.join(missing_clean)}")

    pass

    print(f"\nSelesai! {len(detailed)} resep disimpan ke {OUTPUT_FILE}")
    print("=" * 50)

def get_temp_results(filepath: str) -> list[dict]:
    """Read cookpad_temp from TinyDB for the GUI."""
    db = TinyDB(filepath)
    results = db.table('cookpad_temp').all()
    db.close()
    return results
if __name__ == "__main__":
    main()