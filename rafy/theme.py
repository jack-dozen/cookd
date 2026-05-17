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
    """
    Singleton yang menyimpan state tema aktif dan memberitahu semua
    listener ketika tema berubah.

    Cara pakai:
        from rafy.theme import theme_mgr

        # baca warna
        color = theme_mgr.get("BG")

        # daftar listener rebuild
        theme_mgr.add_listener(my_rebuild_fn)s

        # toggle (panggil dari on_change Switch)
        theme_mgr.toggle(page)
    """
    def __init__(self):
        self._current: dict[str, str] = DARK.copy()
        self._listeners: list = []

    # ── Query ─────────────────────────────────────────────────────────
    def get(self, key: str) -> str:
        return self._current.get(key, "#FF00FF")

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
# MATCH SCORE
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
# THEME TOGGLE WIDGET
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
        value=not theme_mgr.is_dark(),
        active_color=ORANGE,
        inactive_track_color="#555555",
        width=40,
        height=22,
        thumb_color=WHITE,
    )

    # label_text pakai opacity untuk animasi halus (tidak ada layout jump)
    # expand=True dipindah ke spacer terpisah supaya icon tidak mengembang saat label transparan
    label_text = ft.Text(
        value="Light mode" if not theme_mgr.is_dark() else "Dark mode",
        color=theme_mgr.get("TEXT2"),
        size=13,
        opacity=1.0 if show_label else 0.0,
        animate_opacity=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
    )
    # Spacer selalu expand, terpisah dari label_text
    spacer = ft.Container(expand=True)

    # icon_ctrl dibungkus Container agar bisa di-replace isinya
    # (Flet 0.85 tidak support update ft.Icon.name secara langsung)
    def _make_icon():
        return ft.Icon(
            ft.Icons.LIGHT_MODE_OUTLINED if not theme_mgr.is_dark() else ft.Icons.DARK_MODE_OUTLINED,
            color=theme_mgr.get("TEXT2"),
            size=18,
        )

    icon_wrapper = ft.Container(content=_make_icon())

    row = ft.Row(
        controls=[icon_wrapper, label_text, spacer, switch],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    container = ft.Container(
        content=row,
        bgcolor=theme_mgr.get("BG3"),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def on_toggle(e):
        theme_mgr.toggle(page)
        is_light = not theme_mgr.is_dark()
        # Update switch
        switch.value = is_light
        # Update label
        label_text.value = "Light mode" if is_light else "Dark mode"
        label_text.color = theme_mgr.get("TEXT2")
        # Ganti icon dengan object baru (workaround Flet 0.85)
        icon_wrapper.content = ft.Icon(
            ft.Icons.LIGHT_MODE_OUTLINED if is_light else ft.Icons.DARK_MODE_OUTLINED,
            color=theme_mgr.get("TEXT2"),
            size=18,
        )
        container.bgcolor = theme_mgr.get("BG3")
        icon_wrapper.update()
        label_text.update()
        container.update()
        page.update()

    switch.on_change   = on_toggle
    container.on_click = on_toggle

    # Expose refs agar caller bisa kontrol visibility saat sidebar collapse
    # label pakai opacity (bukan visible) supaya tidak ada layout jump
    container._label_text = label_text
    container._switch     = switch

    return container
