"""
theme.py — CookD
Semua konstanta warna, font, dan konfigurasi tema terpusat di sini.
Import dari modul lain dengan: from theme import *
"""

import flet as ft

# ─────────────────────────────────────────────────────────────────────
# DARK THEME (default)
# ─────────────────────────────────────────────────────────────────────
DARK = {
    "BG":     "#1A1A1A",
    "BG2":    "#242424",
    "BG3":    "#2E2E2E",
    "BG4":    "#363636",
    "TEXT":   "#F0F0EC",
    "TEXT2":  "#B0B0AB",
    "TEXT3":  "#707070",
    "BORDER": "#000000",
}

# ─────────────────────────────────────────────────────────────────────
# LIGHT THEME
# ─────────────────────────────────────────────────────────────────────
LIGHT = {
    "BG":     "#F5F5F0",
    "BG2":    "#EBEBEB",
    "BG3":    "#DCDCDC",
    "BG4":    "#CCCCCC",
    "TEXT":   "#1A1A1A",
    "TEXT2":  "#444444",
    "TEXT3":  "#888888",
    "BORDER": "#CCCCCC",
}

# ─────────────────────────────────────────────────────────────────────
# ACCENT (sama di dark & light)
# ─────────────────────────────────────────────────────────────────────
ORANGE = "#E8440A"
GREEN  = "#2E9E5B"
AMBER  = "#E09020"
BLUE   = "#1A6FBF"
RED    = "#C0392B"

# Store brand colors
TOK_COLOR  = "#00AA5B"   # Tokopedia
ALFA_COLOR = "#E31E24"   # Alfagift
AEON_COLOR = "#6B3FA0"   # AEON

# ─────────────────────────────────────────────────────────────────────
# FONT
# ─────────────────────────────────────────────────────────────────────
FONT_FAMILY = "Font"
FONT_PATH   = "fonts/Poppins-Regular.ttf"

# ─────────────────────────────────────────────────────────────────────
# STATE — tema aktif (mutable, diupdate oleh toggle)
# ─────────────────────────────────────────────────────────────────────
_current = DARK.copy()

def is_dark() -> bool:
    return _current["BG"] == DARK["BG"]

def toggle():
    """Ganti antara dark dan light, return nama tema baru."""
    _current.update(LIGHT if is_dark() else DARK)
    return "light" if not is_dark() else "dark"

def get(key: str) -> str:
    """Ambil warna tema aktif. Contoh: theme.get('BG')"""
    return _current.get(key, "#FF00FF")  # magenta = warna belum terdefinisi

# ─────────────────────────────────────────────────────────────────────
# SHORTCUT — variabel langsung (snapshot saat import)
# Untuk live update, pakai theme.get('KEY')
# ─────────────────────────────────────────────────────────────────────
BG     = _current["BG"]
BG2    = _current["BG2"]
BG3    = _current["BG3"]
BG4    = _current["BG4"]
TEXT   = _current["TEXT"]
TEXT2  = _current["TEXT2"]
TEXT3  = _current["TEXT3"]
BORDER = _current["BORDER"]

# ─────────────────────────────────────────────────────────────────────
# FLET THEME OBJECT
# ─────────────────────────────────────────────────────────────────────
def make_flet_theme() -> ft.Theme:
    return ft.Theme(font_family=FONT_FAMILY)

def apply_to_page(page: ft.Page):
    """Terapkan tema ke ft.Page — panggil saat init dan saat toggle."""
    mode = DARK if is_dark() else LIGHT
    page.bgcolor    = mode["BG"]
    page.theme_mode = ft.ThemeMode.DARK if is_dark() else ft.ThemeMode.LIGHT
    page.fonts      = {FONT_FAMILY: FONT_PATH}
    page.theme      = make_flet_theme()

# ─────────────────────────────────────────────────────────────────────
# MATCH SCORE — warna berdasarkan persentase kecocokan
# ─────────────────────────────────────────────────────────────────────
def match_color(score: float) -> tuple[str, str]:
    """Return (bg_color, text_color) berdasarkan score 0.0–1.0."""
    pct = score * 100
    if pct >= 80:
        return "#1B3D28", GREEN
    elif pct >= 50:
        return "#3D2E0A", AMBER
    else:
        return "#3D1A1A", RED