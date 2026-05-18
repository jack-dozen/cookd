"""
snackbar.py
════════════════════════════════════════════════════════════════
Utility snackbar terpusat untuk CookD.

Cara pakai:
    from rafy.snackbar import show_snack

    show_snack(page, "Resep disimpan!", "success")
    show_snack(page, "Gagal memuat data", "error")
    show_snack(page, "Harga diperbarui", "info")
    show_snack(page, "Koneksi lambat", "warning")
════════════════════════════════════════════════════════════════
"""

import flet as ft
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from rafy.theme import theme_mgr, GREEN, ORANGE, AMBER, WHITE

def BG3():   return theme_mgr.get("BG3")
def TEXT():  return theme_mgr.get("TEXT")
def TEXT2(): return theme_mgr.get("TEXT2")

# ── Konfigurasi tiap tipe ──────────────────────────────────────────────────────
_SNACK_CONFIG = {
    "success": {
        "icon"      : ft.Icons.CHECK_CIRCLE_OUTLINE,
        "icon_color": GREEN,
        "bar_color" : GREEN,
    },
    "error": {
        "icon"      : ft.Icons.ERROR_OUTLINE,
        "icon_color": "#E74C3C",
        "bar_color" : "#E74C3C",
    },
    "info": {
        "icon"      : ft.Icons.INFO_OUTLINE,
        "icon_color": "#1A6FBF",
        "bar_color" : "#1A6FBF",
    },
    "warning": {
        "icon"      : ft.Icons.WARNING_AMBER_OUTLINED,
        "icon_color": AMBER,
        "bar_color" : AMBER,
    },
}

_DEFAULT_DURATION = 3000   # ms


def show_snack(
    page    : ft.Page,
    message : str,
    type    : str = "info",
    duration: int = _DEFAULT_DURATION,
) -> None:
    """
    Tampilkan snackbar dengan styling konsisten.

    Args:
        page     : ft.Page aktif
        message  : teks yang ditampilkan
        type     : "success" | "error" | "info" | "warning"
        duration : durasi tampil dalam ms (default 3000)
    """
    cfg = _SNACK_CONFIG.get(type, _SNACK_CONFIG["info"])

    snack = ft.SnackBar(
        content=ft.Row(
            controls=[
                ft.Icon(cfg["icon"], color=cfg["icon_color"], size=18),
                ft.Text(message, color=TEXT(), size=13, expand=True),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG3(),
        duration=duration,
        behavior=ft.SnackBarBehavior.FLOATING,
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        margin=ft.Margin(left=16, right=16, top=0, bottom=16),
        show_close_icon=True,
        close_icon_color=TEXT2(),
    )

    # Garis warna kiri sebagai indikator tipe
    snack.content = ft.Row(
        controls=[
            ft.Container(
                width=4,
                height=36,
                bgcolor=cfg["bar_color"],
                border_radius=ft.BorderRadius.all(4),
            ),
            ft.Icon(cfg["icon"], color=cfg["icon_color"], size=18),
            ft.Text(message, color=TEXT(), size=13, expand=True),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.snack_bar = snack
    page.snack_bar.open = True
    page.update()