import json
import logging
import hashlib
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
log = logging.getLogger("CookpadScraper")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [COOKPAD] %(message)s"))
log.addHandler(handler)
log.propagate = False

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_URL        = "https://cookpad.com"
SEARCH_URL      = "https://cookpad.com/id/cari/{keyword}"
SEARCH_URL_PAGE = "https://cookpad.com/id/cari/{keyword}?page={page}"
OUTPUT_FILE     = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')
MAX_SEARCH_PAGES = 5    # how many cookpad search pages to collect stubs from
PAGE_SIZE        = 10   # recipes per UI page
MAX_THREADS      = 4
MIN_MATCH_SCORE  = 0.01

# ── Fetcher setup ──────────────────────────────────────────────────────────────
StealthyFetcher.adaptive = False

SKIP_WORDS = {
    "dan", "atau", "secukupnya", "sckpnya", "sdm", "sdt", "gr",
    "kg", "ml", "liter", "buah", "butir", "siung", "lembar",
    "batang", "iris", "potong", "besar", "kecil", "sedang",
}

# ── DB lock for thread-safe writes ────────────────────────────────────────────
_db_lock = threading.Lock()


# ── Helpers ────────────────────────────────────────────────────────────────────
def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def save_single_recipe(db, recipe: dict):
    """Save one recipe to DB immediately, thread-safe."""
    with _db_lock:
        cookpad_table = db.table('cookpad_recipes')
        existing_urls = {r['source_url'] for r in cookpad_table.all()}
        if recipe['source_url'] not in existing_urls:
            cookpad_table.insert(recipe)

def is_paywalled(href: str) -> bool:
    return "/premium" in href or "paywall" in href

def safe_get(scraper, field: str, default=None):
    try:
        return getattr(scraper, field)()
    except Exception:
        return default


# ── Ingredient scoring ─────────────────────────────────────────────────────────
def ingredient_score(recipe_ingredients: list, user_ingredients: list[str]) -> dict:
    if not recipe_ingredients:
        return {"score": 0.0, "have": [], "missing": []}

    user_text = " ".join(user_ingredients).lower()
    have, missing = [], []

    for ingr in recipe_ingredients:
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

def search_recipe_page(keyword: str, page: int = 1) -> list[dict]:
    """Return stubs from one Cookpad search page."""
    if page == 1:
        url = SEARCH_URL.format(keyword=keyword.replace(" ", "%20"))
    else:
        url = SEARCH_URL_PAGE.format(keyword=keyword.replace(" ", "%20"), page=page)

    log.info(f"  → Searching page {page}: '{keyword}'")

    try:
        pg = StealthyFetcher.fetch(url, headless=True, network_idle=True)
    except Exception as e:
        log.error(f"Search failed for '{keyword}' page {page}: {e}")
        return []

    stubs = []
    for link in pg.css("a[href*='/id/resep/']"):
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

    log.info(f"     {len(stubs)} stubs found on page {page}")
    return stubs


def collect_all_stubs(keyword: str, stop_event: threading.Event) -> list[dict]:
    """Collect stubs from all search pages up to MAX_SEARCH_PAGES."""
    all_stubs = []
    seen_urls = set()

    for page in range(1, MAX_SEARCH_PAGES + 1):
        if stop_event.is_set():
            log.info("Stop requested, halting stub collection")
            break
        stubs = search_recipe_page(keyword, page)
        if not stubs:
            break  # no more pages
        for stub in stubs:
            if stub["source_url"] not in seen_urls:
                seen_urls.add(stub["source_url"])
                all_stubs.append(stub)

    log.info(f"Total stubs collected: {len(all_stubs)}")
    return all_stubs


def scrape_video_url(video_page_url: str) -> str:
    try:
        page = StealthyFetcher.fetch(video_page_url, headless=True, network_idle=True)
        video_el = page.css("video source")
        if video_el:
            return video_el[0].attrib.get("src", "")
        video_tag = page.css("video")
        if video_tag:
            return video_tag[0].attrib.get("src", "")
    except Exception as e:
        log.warning(f"Video scrape failed: {e}")
    return ""


def scrape_recipe_detail(stub: dict) -> dict | None:
    url = stub["source_url"]
    log.info(f"Scraping: {stub['name']}")

    try:
        page = StealthyFetcher.fetch(
            url, headless=True, network_idle=True,
            wait_selector="div.ingredient-list",
        )
    except Exception as e:
        log.error(f"Fetch failed ({url}): {e}")
        return None

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

    scraper = None
    try:
        scraper = scrape_html(raw_html, org_url=url, supported_only=False)
    except Exception as e:
        log.warning(f"recipe-scrapers failed: {e}. Using CSS fallback.")

    if scraper:
        title     = safe_get(scraper, "title",     stub["name"])
        author    = safe_get(scraper, "author",     "")
        yields    = safe_get(scraper, "yields",     "")
        cook_time = safe_get(scraper, "total_time", None)
        image_url = safe_get(scraper, "image",      "")
        cook_time = f"{cook_time} menit" if isinstance(cook_time, int) and cook_time else (str(cook_time) if cook_time else "")
    else:
        title = stub["name"]
        author = yields = cook_time = image_url = ""

    ingredients = []
    for li in page.css("div[class*='ingredient-list'] ol li"):
        qty_el  = li.css("bdi")
        name_el = li.css("span")
        bold_el = li.css("b, strong")
        qty  = qty_el[0].text.strip() if qty_el else ""
        if name_el:
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
        p           = li.css("div[dir='auto'] p")
        attachments = li.css(".step-attachments-list a.block")
        step = {}
        if p:
            step["text"] = p[0].get_all_text().strip()
        images, videos = [], []
        for a in attachments:
            href    = a.attrib.get("href", "")
            picture = a.css("picture source")
            src     = picture[0].attrib.get("srcset", "").split(" ")[0] if picture else ""
            if "/videos/production/step_videos/" in href:
                full_href = BASE_URL + href if href.startswith("/") else href
                mp4_url   = scrape_video_url(full_href)
                videos.append({"thumb": src, "href": mp4_url if mp4_url else full_href})
            elif "/step_attachment/images/" in href:
                if src:
                    images.append(src)
        if images:
            step["images"] = images
        if videos:
            step["videos"] = videos
        if step.get("text"):
            steps.append(step)

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
    if not image_url and scraper:
        image_url = safe_get(scraper, "image", "")

    return {
        **stub,
        "name":        title,
        "ingredients": ingredients,
        "steps":       steps,
        "author":      author,
        "portion":     yields    if yields    else "-",
        "cook_time":   cook_time if cook_time else "-",
        "image_url":   image_url,
        "source":      "Cookpad",
        "scraped_at":  now(),
    }


# ── Local search ───────────────────────────────────────────────────────────────

def search_local_by_ingredients(user_ingredients: list[str], db) -> list[dict]:
    results = []
    for recipe in db.table('cookpad_recipes').all():
        score_result = ingredient_score(recipe["ingredients"], user_ingredients)
        if score_result["score"] >= MIN_MATCH_SCORE:
            r = recipe.copy()
            r["match_score"]         = score_result["score"]
            r["have_ingredients"]    = score_result["have"]
            r["missing_ingredients"] = score_result["missing"]
            results.append(r)
    return sorted(results, key=lambda x: x["match_score"], reverse=True)


# ── Main find function ─────────────────────────────────────────────────────────

def find_recipe(
    user_ingredients: list[str],
    on_recipe_found=None,
    on_page_ready=None,       # called when PAGE_SIZE recipes are ready: on_page_ready(page_number)
    mode: str = "scrape",
    stop_event: threading.Event = None,
) -> list[dict]:

    if stop_event is None:
        stop_event = threading.Event()

    db = TinyDB(OUTPUT_FILE)

    # ── Local only ────────────────────────────────────────────────────────────
    if mode == "local":
        results = search_local_by_ingredients(user_ingredients, db)
        db.close()
        for r in results:
            if on_recipe_found:
                on_recipe_found(r)
        return results

    # ── Scrape mode ───────────────────────────────────────────────────────────
    local_map = {r["source_url"]: r for r in db.table('cookpad_recipes').all()}

    # Step 1: collect all stubs (sequential, paginated)
    keyword = " ".join(user_ingredients)
    all_stubs = collect_all_stubs(keyword, stop_event)

    # Deduplicate stubs
    seen_urls = set()
    unique_stubs = []
    for stub in all_stubs:
        if stub["source_url"] not in seen_urls:
            seen_urls.add(stub["source_url"])
            unique_stubs.append(stub)

    results    = []
    results_lock = threading.Lock()
    page_count = {"current": 0, "buffer": 0}

    def process_stub(stub):
        # Check stop before doing any work
        if stop_event.is_set():
            return

        # Local hit
        if stub["source_url"] in local_map:
            log.info(f"Local hit: {stub['name']}")
            recipe = local_map[stub["source_url"]]
        else:
            if stop_event.is_set():
                return
            recipe = scrape_recipe_detail(stub)
            # Check stop immediately after the blocking fetch returns —
            # this is the earliest we can bail out of an in-flight request.
            if stop_event.is_set():
                return
            if not recipe:
                return

        if stop_event.is_set():
            return

        score_result = ingredient_score(recipe["ingredients"], user_ingredients)
        log.info(f"Score: {score_result['score']:.2f} for {recipe['name']}")

        if score_result["score"] < MIN_MATCH_SCORE:
            log.info("Skipped (score too low)")
            return

        recipe = recipe.copy()
        recipe["match_score"]         = score_result["score"]
        recipe["have_ingredients"]    = score_result["have"]
        recipe["missing_ingredients"] = score_result["missing"]

        if stop_event.is_set():
            return

        # Save immediately
        save_single_recipe(db, recipe)

        with results_lock:
            results.append(recipe)
            page_count["buffer"] += 1
            current_buffer = page_count["buffer"]

        if on_recipe_found and not stop_event.is_set():
            on_recipe_found(recipe)

        # Notify when a full UI page is ready
        if current_buffer % PAGE_SIZE == 0 and on_page_ready and not stop_event.is_set():
            page_count["current"] += 1
            on_page_ready(page_count["current"])

    # Step 2: scrape details in parallel with 4 threads.
    # Use cancel_futures=True + wait=False so pending (not-yet-started) futures
    # are dropped immediately when stop is pressed; in-flight fetches still have
    # to complete their HTTP request (StealthyFetcher is not interruptible) but
    # will see stop_event.is_set() and discard their result right after.
    executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
    futures = {executor.submit(process_stub, stub): stub for stub in unique_stubs}
    try:
        for future in as_completed(futures):
            if stop_event.is_set():
                log.info("[CookD] Stop event detected — shutting down executor.")
                # cancel_futures=True drops all pending (queued) futures instantly.
                executor.shutdown(wait=False, cancel_futures=True)
                break
            try:
                future.result()
            except Exception as e:
                log.error(f"Thread error: {e}")
    finally:
        # Always shut down cleanly; if already shut down this is a no-op.
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    db.close()
    return sorted(results, key=lambda x: x["match_score"], reverse=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def main(ingredients, on_recipe_found=None, on_page_ready=None, mode: str = "scrape", stop_event: threading.Event = None):
    print("=" * 50)
    print("  Cookpad Recipe Scraper")
    print("=" * 50)

    if not ingredients:
        print("Tidak ada bahan yang diinput. Keluar.")
        return

    user_ingredients = ingredients if isinstance(ingredients, list) else [i.strip() for i in ingredients.split(",")]
    print(f"Bahan yang dimasukkan: {', '.join(user_ingredients)}")

    detailed = find_recipe(
        user_ingredients,
        on_recipe_found=on_recipe_found,
        on_page_ready=on_page_ready,
        mode=mode,
        stop_event=stop_event,
    )

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
        print(f"\n🔴 REKOMENDASI ({len(recommended)} resep):")
        for r in recommended:
            percent = round(r["match_score"] * 100, 1)
            missing_clean = [
                (i["name"] if isinstance(i, dict) else i).replace("\n", " ").strip()
                for i in r["missing_ingredients"]
            ]
            print(f"   {r['name']} ({percent}% bahan tersedia)")
            print(f"   Kurang: {', '.join(missing_clean)}")

    print(f"\nSelesai! {len(detailed)} resep disimpan ke {OUTPUT_FILE}")
    print("=" * 50)


def get_temp_results(filepath: str) -> list[dict]:
    db = TinyDB(filepath)
    results = db.table('cookpad_temp').all()
    db.close()
    return results


if __name__ == "__main__":
    main(sys.argv[1])