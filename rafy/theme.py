"""
theme.py — CookD
Semua konstanta warna, font, dan konfigurasi tema terpusat di sini.
Import dari modul lain dengan: from rafy.theme import theme_mgr, T

Cara pakai live update:
    color = theme_mgr.get("BG")
    theme_mgr.add_listener(rebuild_fn)
    theme_mgr.toggle(page)
"""

import flet as ft

# ─────────────────────────────────────────────────────────────────────
# DARK THEME (default)
# ─────────────────────────────────────────────────────────────────────
DARK: dict[str, str] = {
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
LIGHT: dict[str, str] = {
    "BG":     "#F5F5F0",
    "BG2":    "#EBEBEB",
    "BG3":    "#DCDCDC",
    "BG4":    "#CCCCCC",
    "TEXT":   "#1A1A1A",
    "TEXT2":  "#444444",
    "TEXT3":  "#888888",
    "BORDER": "#C8C8C8",
}

# ─────────────────────────────────────────────────────────────────────
# ACCENT (sama di dark & light)
# ─────────────────────────────────────────────────────────────────────
ORANGE = "#E8440A"
GREEN  = "#2E9E5B"
AMBER  = "#E09020"
BLUE   = "#1A6FBF"
RED    = "#C0392B"
WHITE  = "#FFFFFF"
BLACK  = "#000000"

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
# THEME MANAGER — singleton reaktif
# ─────────────────────────────────────────────────────────────────────
class ThemeManager:
    """
    Singleton yang menyimpan state tema aktif dan memberitahu semua
    listener ketika tema berubah.

    Cara pakai:
        from rafy.theme import theme_mgr

        # baca warna
        color = theme_mgr.get("BG")

        # daftar listener rebuild
        theme_mgr.add_listener(my_rebuild_fn)

        # toggle (panggil dari on_change Switch)
        theme_mgr.toggle(page)
    """

    def __init__(self):
        self._current: dict[str, str] = DARK.copy()
        self._listeners: list = []

    # ── Query ─────────────────────────────────────────────────────────
    def get(self, key: str) -> str:
        """Ambil warna tema aktif. Contoh: theme_mgr.get('BG')"""
        return self._current.get(key, "#FF00FF")  # magenta = key belum terdefinisi

    def is_dark(self) -> bool:
        return self._current["BG"] == DARK["BG"]

    # ── Mutation ──────────────────────────────────────────────────────
    def toggle(self, page: ft.Page | None = None):
        """Ganti antara dark dan light, lalu panggil semua listener."""
        self._current.update(LIGHT if self.is_dark() else DARK)
        if page:
            self._apply_to_page(page)
        self._notify()

    def _apply_to_page(self, page: ft.Page):
        """Terapkan tema ke ft.Page — bgcolor + theme_mode."""
        page.bgcolor    = self._current["BG"]
        page.theme_mode = ft.ThemeMode.DARK if self.is_dark() else ft.ThemeMode.LIGHT
        page.fonts      = {FONT_FAMILY: FONT_PATH}
        page.theme      = ft.Theme(font_family=FONT_FAMILY)

    # ── Listener registry ─────────────────────────────────────────────
    def add_listener(self, fn):
        """Daftarkan fungsi callback yang dipanggil saat tema berubah."""
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn):
        self._listeners = [f for f in self._listeners if f != fn]

    def _notify(self):
        for fn in self._listeners:
            try:
                fn()
            except Exception:
                pass


# Global singleton — import dan pakai langsung
theme_mgr = ThemeManager()

# Shortcut helper (snapshot baca langsung dari manager)
def T(key: str) -> str:
    """Shortcut: T('BG') == theme_mgr.get('BG')"""
    return theme_mgr.get(key)


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


# ─────────────────────────────────────────────────────────────────────
# THEME TOGGLE WIDGET — bisa langsung ditambah ke mana saja
# ─────────────────────────────────────────────────────────────────────
def build_theme_toggle(page: ft.Page, show_label: bool = True) -> ft.Container:
    """
    Buat widget toggle dark/light mode.

    Params:
        page        : ft.Page aktif
        show_label  : tampilkan label "Dark mode" / "Light mode" (default True)

    Return:
        ft.Container berisi ikon + label + Switch
    """
    switch = ft.Switch(
        value=not theme_mgr.is_dark(),   # True = Light mode aktif
        active_color=ORANGE,
        inactive_track_color="#555555",
        width=40,
        height=22,
        thumb_color=WHITE,
    )

    label_text = ft.Text(
        value="Light mode" if not theme_mgr.is_dark() else "Dark mode",
        color=theme_mgr.get("TEXT2"),
        size=13,
        expand=True,
    )

    icon_ctrl = ft.Icon(
        ft.Icons.LIGHT_MODE_OUTLINED if not theme_mgr.is_dark() else ft.Icons.DARK_MODE_OUTLINED,
        color=theme_mgr.get("TEXT2"),
        size=18,
    )

    container = ft.Container(
        content=ft.Row(
            controls=[icon_ctrl, label_text, switch] if show_label else [switch],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=theme_mgr.get("BG3"),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def on_toggle(e):
        theme_mgr.toggle(page)
        # Update widget ini sendiri
        is_light = not theme_mgr.is_dark()
        switch.value              = is_light
        label_text.value          = "Light mode" if is_light else "Dark mode"
        label_text.color          = theme_mgr.get("TEXT2")
        icon_ctrl.name  = ft.Icons.LIGHT_MODE_OUTLINED if is_light else ft.Icons.DARK_MODE_OUTLINED
        icon_ctrl.color           = theme_mgr.get("TEXT2")
        container.bgcolor         = theme_mgr.get("BG3")
        page.update()

    switch.on_change = on_toggle
    container.on_click = on_toggle   # klik area juga toggle

    return container