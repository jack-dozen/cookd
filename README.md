
# 🍳 CookD

[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.85.0-02569C?logo=flet)](https://flet.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-no_longer_maintained-orange)]()

[cookd website](https://jack-dozen.github.io/cookd/)

---

## Quick Description

CookD is an all-in-one recipe management application that bridges the gap between discovering recipes and purchasing the ingredients to make them. Users enter the ingredients they already have on hand, and CookD searches [Cookpad](https://cookpad.com) for matching recipes — ranked by an ingredient match score. Once a recipe is selected, CookD's price comparison engine scrapes real-time prices from three Indonesian e-commerce platforms (Tokopedia, Alfagift, and AEON Store) so users can see exactly how much each recipe will cost before they shop.

Built with [Flet](https://flet.dev) for a modern desktop GUI and powered by Python's scraping ecosystem, CookD is designed for home cooks who want to minimize food waste and make informed shopping decisions.

---

## Features

- **Ingredient-based Recipe Search** — Enter ingredients you have (e.g., `tomato, garlic, salt`) and get recipes ranked by match percentage
- **Dual Search Modes** — *Scrape* mode fetches live results from Cookpad; *Local* mode searches your cached database instantly
- **Recipe CRUD** — Save, organize, and manage your favorite recipes in a personal cookbook
- **Cross-store Price Comparison** — Compare ingredient prices across Tokopedia, Alfagift, and AEON Store in a single view
- **Per-portion Cost Calculation** — See the estimated cost per serving for each recipe at each store
- **Time-based Recommendations** — The Home page suggests recipes appropriate for breakfast, lunch, snacks, or dinner
- **Dark / Light Theme** — Toggle between themes with persistent settings
- **Import / Export** — Back up and restore your recipe database
- **Pagination & Live Results** — Search results load incrementally with animated cards and a cooking-themed loader
- **Thread-safe Architecture** — Concurrent scraping with shared locks for database and browser driver access

---

## Table of Contents

- [Quick Description](#quick-description)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Technical Details](#technical-details)
- [Academic Context](#academic-context)
- [Contributors](#contributors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Installation

### Prerequisites

- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **Google Chrome** — Required by the Selenium-based scrapers (Tokopedia, Alfagift, AEON)
- **Git** — For cloning the repository

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/jack-dozen/cookd.git
   cd cookd
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv311
   .venv311\Scripts\activate      # Windows
   # source .venv311/bin/activate  # macOS / Linux
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (required by `scrapling` for Cookpad scraping)

   ```bash
   playwright install chromium
   ```

5. **Verify the installation**

   ```bash
   python -c "import flet; print('Flet OK')"
   ```

> **Note:** The first run will create a `data/base.json` file (TinyDB) to store scraped recipes and price data.

---

## Usage

### Launching the Application

```bash
python main.py
```

The GUI window opens at 1200×720 with a dark theme by default. Navigate using the sidebar or topbar.

### Finding Recipes

1. Open the **Finder** page (via sidebar or the search bar on the Home page).
2. Enter the ingredients you have, separated by commas:

   ```
   bawang putih, tomat, telur, garam
   ```

3. Press **Enter** or click **Cari**.
4. Recipes appear as cards, sorted by match score (green = all ingredients available, yellow = partial, red = low match).
5. Click a card to view the full recipe detail.

### CLI Recipe Scraping

The Cookpad scraper can also be run standalone from the command line:

```bash
python -m src.scrapers.cookpad_scraper "bawang putih, tomat, telur"
```

This scrapes Cookpad for matching recipes and saves them to `data/base.json`.

### Price Comparison

1. Open any recipe in the **Detail** view.
2. Click **"Kalkulasi Harga Bahan"** (Calculate Ingredient Prices).
3. The Price Panel fetches prices from Tokopedia, Alfagift, and AEON Store.
4. Each ingredient shows the cheapest store, and the total per-store cost is displayed with a bar chart.

### Saving Recipes

Click the **♥** button on any recipe card to save it to **My Recipes**. Saved recipes are stored locally and can be searched, viewed, or removed at any time.

### Local vs. Scrape Mode

- **Scrape** (default): Fetches live results from Cookpad. Slower but always current.
- **Local**: Searches only recipes previously saved to `data/base.json`. Instant results.

---

## Project Structure

```
cookd-app/
├── main.py                  # Entry point — launches the Flet GUI
├── db_lock.py               # Shared thread locks (DB_LOCK, DRIVER_INIT_LOCK)
├── requirements.txt         # Python dependencies
├── LICENSE                  # MIT license
├── README.md                # This file
├── recipes.json             # Sample recipe data (seed file)
├── assets/                  # Images, icons, fonts used by the GUI
├── data/
│   └── base.json            # TinyDB database (recipes, prices, results)
└── src/
    ├── core/
    │   ├── __init__.py
    │   ├── db_lock.py       # Re-export of shared locks
    │   └── theme.py         # Theme manager (dark/light), color constants, fonts
    ├── scrapers/
    │   ├── __init__.py
    │   ├── cookpad_scraper.py    # Recipe scraper (Cookpad)
    │   ├── tokopedia_scraper.py  # Price scraper (Tokopedia)
    │   ├── alfagift_scraper.py   # Price scraper (Alfagift)
    │   └── aeon_scraper.py       # Price scraper (AEON Store)
    ├── services/
    │   ├── __init__.py
    │   └── price_comparison.py   # PriceComparisonService — orchestrates scraping + calculation
    └── ui/
        ├── components/
        │   ├── __init__.py
        │   ├── ingredient_price_list.py
        │   ├── save_btn.py
        │   ├── sidebar_extras.py
        │   └── snackbar.py
        ├── dialogs/
        │   ├── __init__.py
        │   ├── exporter.py
        │   └── importer.py
        └── views/
            ├── __init__.py
            ├── main_window.py      # Root layout, navigation, page routing
            ├── home.py             # Home page (hero, stats, recommendations)
            ├── finder.py           # Recipe search & results page
            ├── detail.py           # Recipe detail view
            ├── my_recipes.py       # Saved recipes page
            ├── for_you.py          # Personalized recommendations
            ├── info.py             # About / info page
            ├── sidebar.py          # Navigation sidebar
            ├── topbar.py           # Window title bar with controls
            └── price_panel.py      # Price comparison visualization
```

---

## Technical Details

### Architecture

CookD follows a layered architecture with clear separation between UI, business logic, and data access:

```
┌─────────────────────────────────────────────────────┐
│  UI Layer (Flet) — views/, components/, dialogs/    │
│  ────────────────────────────────────────────────── │
│  Services Layer — services/price_comparison.py      │
│  ────────────────────────────────────────────────── │
│  Scraper Layer — scrapers/*.py                      │
│  ────────────────────────────────────────────────── │
│  Data Layer — TinyDB (data/base.json) + db_lock.py  │
└─────────────────────────────────────────────────────┘
```

### Key Technologies

| Layer       | Technology                          | Purpose                              |
|-------------|-------------------------------------|--------------------------------------|
| GUI         | Flet 0.85.0                         | Desktop UI framework (Python)        |
| Scraping    | Scrapling, Selenium, Undetected Chromedriver | Web fetching & browser automation |
| Parsing     | BeautifulSoup, recipe_scrapers      | HTML parsing & structured extraction |
| Storage     | TinyDB 4.8.2                        | Local JSON-based database            |
| Concurrency | threading, ThreadPoolExecutor       | Parallel scraping with locks         |

### Threading Model

- **`DB_LOCK`** (`threading.RLock`): Reentrant lock protecting all TinyDB read/write operations across threads.
- **`DRIVER_INIT_LOCK`** (`threading.Lock`): Serializes `undetected_chromedriver` initialization to prevent `WinError 183` (file already exists) on Windows.
- The `PriceComparisonService` runs scrapers for Tokopedia, Alfagift, and AEON concurrently in separate threads, with results cached for 7 days.

### Data Sources

| Source       | Type      | Scraped Data                        |
|--------------|-----------|-------------------------------------|
| Cookpad      | Recipes   | Title, ingredients, steps, images   |
| Tokopedia    | Prices    | Product name, price, unit, URL      |
| Alfagift     | Prices    | Product name, price, unit, URL      |
| AEON Store   | Prices    | Product name, price, unit, URL      |

### Price Calculation

The `PriceComparisonService` parses ingredient quantities into grams using a built-in unit converter (supports Indonesian units: `sdm`, `sdt`, `siung`, `biji`, `butir`, etc.). It then calculates the proportional recipe cost per ingredient and aggregates totals per store, including median-based estimates for ingredients missing from a particular store.

---

## Academic Context

**This is a course project for the PPLD (Proyek Pengembangan Perangkat Lunak Desktop / Software Development) program at POLBAN.**

CookD was developed as part of a capstone software engineering course, applying full-stack development, web scraping, concurrent programming, and UI/UX design principles. The project demonstrates:

- Multi-developer collaboration using a shared codebase
- Integration of third-party APIs and web scraping
- Thread-safe data access patterns
- Modern desktop GUI development with Python

While the project is functional, it is released as a learning artifact and may not yet meet all production-readiness criteria.

---

## Contributors

| Name       | Role                          | GitHub / Contact         |
|------------|-------------------------------|--------------------------|
| hadi       | GUI architecture, main window, finder, detail, sidebar, topbar | [@hadi-fachriansyah](https://github.com/hadi-fachriansyah) |
| rafy       | Home page, For You recommendations | [@RafyGantenk123](https://github.com/RafyGantenk123) |
| zaky       | Info page, price panel UI | [@jack-dozen](https://github.com/jack-dozen) |
| fadhil     | My Recipes page, import/export dialogs | [@fadhilarfnn](https://github.com/fadhilarfnn) |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 The Cookd Contributors
```

---

## Acknowledgments

- **[Cookpad](https://cookpad.com)** — Recipe data source and inspiration for the ingredient-matching algorithm
- **[Tokopedia](https://tokopedia.com)**, **[Alfagift](https://alfagift.id)**, **[AEON Store](https://aeonstore.id)** — E-commerce platforms providing price data
- **[Flet](https://flet.dev)** — Desktop GUI framework that made the native-looking interface possible
- **[recipe-scrapers](https://github.com/summarydev/recipe-scrapers)** — Structured recipe data extraction library
- **[Scrapling](https://github.com/typomobile/scrapling)** — Stealth web fetching for the Cookpad scraper
- **[Undetected Chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)** — Browser automation bypass for anti-bot sites
- **Tokopedia-Scraper** by crypter70 — Original Tokopedia scraper used as a base (see `src/scrapers/tokopedia_scraper.py`)
- All recipe authors on Cookpad whose recipes are scraped and showcased in the application
- The PPLD course instructors and peers who provided feedback during development
