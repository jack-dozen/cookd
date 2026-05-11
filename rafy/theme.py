"""
theme.py — CookD
Semua konstanta warna, font, dan konfigurasi tema terpusat di sini.
"""

import flet as ft

# ─────────────────────────────────────────────────────────────────────
# DARK THEME (default)
# ─────────────────────────────────────────────────────────────────────
DARK: dict[str, str] = {
    "BG":     "#111111",
    "BG2":    "#1a1a1a",
    "BG3":    "#242424",
    "BG4":    "#2e2e2e",
    "TEXT":   "#f0ede8",
    "TEXT2":  "#a0a0a0",
    "TEXT3":  "#606060",
    "BORDER": "#333333",
}

# ─────────────────────────────────────────────────────────────────────
# LIGHT THEME
# ─────────────────────────────────────────────────────────────────────
LIGHT: dict[str, str] = {
    "BG":     "#f5f0eb",
    "BG2":    "#edeae4",
    "BG3":    "#e2ddd7",
    "BG4":    "#d4cec7",
    "TEXT":   "#1a1714",
    "TEXT2":  "#5a5550",
    "TEXT3":  "#9a9590",
    "BORDER": "#ccc8c0",
}

# ─────────────────────────────────────────────────────────────────────
# ACCENT
# ─────────────────────────────────────────────────────────────────────
ORANGE      = "#f04f23"
ORANGE_GLOW = "rgba(240,79,35,0.25)"
ORANGE_GLOW2= "rgba(240,79,35,0.10)"
GREEN       = "#22c55e"
AMBER       = "#f59e0b"
BLUE        = "#1A6FBF"
RED         = "#ef4444"
WHITE       = "#FFFFFF"
BLACK       = "#000000"

TOK_COLOR  = "#00AA5B"
ALFA_COLOR = "#E31E24"
AEON_COLOR = "#6B3FA0"

# ─────────────────────────────────────────────────────────────────────
# FONT
# ─────────────────────────────────────────────────────────────────────
FONT_FAMILY = "Font"
FONT_PATH   = "fonts/Poppins-Regular.ttf"


# ─────────────────────────────────────────────────────────────────────
# THEME MANAGER
# ─────────────────────────────────────────────────────────────────────
class ThemeManager:
    def __init__(self):
        self._current: dict[str, str] = DARK.copy()
        self._listeners: list = []

    def get(self, key: str) -> str:
        return self._current.get(key, "#FF00FF")

    def is_dark(self) -> bool:
        return self._current["BG"] == DARK["BG"]

    def toggle(self, page: ft.Page | None = None):
        self._current.update(LIGHT if self.is_dark() else DARK)
        if page:
            self._apply_to_page(page)
        self._notify()

    def _apply_to_page(self, page: ft.Page):
        page.bgcolor    = self._current["BG"]
        page.theme_mode = ft.ThemeMode.DARK if self.is_dark() else ft.ThemeMode.LIGHT
        page.fonts      = {FONT_FAMILY: FONT_PATH}
        page.theme      = ft.Theme(font_family=FONT_FAMILY)

    def add_listener(self, fn):
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


theme_mgr = ThemeManager()


def T(key: str) -> str:
    return theme_mgr.get(key)


# ─────────────────────────────────────────────────────────────────────
# MATCH SCORE
# ─────────────────────────────────────────────────────────────────────
def match_color(score: float) -> tuple[str, str]:
    pct = score * 100
    if pct >= 80:
        return "#1B3D28", GREEN
    elif pct >= 50:
        return "#3D2E0A", AMBER
    else:
        return "#3D1A1A", RED


# ─────────────────────────────────────────────────────────────────────
# THEME TOGGLE WIDGET
# ─────────────────────────────────────────────────────────────────────
def build_theme_toggle(page: ft.Page, show_label: bool = True) -> ft.Container:
    switch = ft.Switch(
        value=not theme_mgr.is_dark(),
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
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def on_toggle(e):
        theme_mgr.toggle(page)
        is_light = not theme_mgr.is_dark()
        switch.value      = is_light
        label_text.value  = "Light mode" if is_light else "Dark mode"
        label_text.color  = theme_mgr.get("TEXT2")
        icon_ctrl.name    = ft.Icons.LIGHT_MODE_OUTLINED if is_light else ft.Icons.DARK_MODE_OUTLINED
        icon_ctrl.color   = theme_mgr.get("TEXT2")
        container.bgcolor = theme_mgr.get("BG3")
        page.update()

    switch.on_change   = on_toggle
    container.on_click = on_toggle

    return container