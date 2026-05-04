"""
sidebar.py — CookD
Widget tambahan untuk sidebar bagian bawah.
Import dari GUI dengan: from rafy.sidebar import build_sidebar_extras

Cara pakai:
    from rafy.sidebar import build_sidebar_extras

    # di dalam sidebar controls, setelah nav items:
    *build_sidebar_extras(page),
"""

import flet as ft
from rafy.theme import theme_mgr, build_theme_toggle


def build_sidebar_extras(page: ft.Page) -> list:
    """
    Buat list widget untuk bagian bawah sidebar:
    - Spacer
    - Tombol Import / Export
    - Theme toggle (dark/light)
    - Bottom padding

    Params:
        page : ft.Page aktif (dioper ke theme toggle)

    Return:
        list of ft.Control — langsung unpack ke sidebar controls
    """

    import_export_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.UPLOAD_OUTLINED, color=theme_mgr.get("TEXT2"), size=18),
                ft.Text("Import / Export", color=theme_mgr.get("TEXT2"), size=13),
            ],
            spacing=10,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=10,
        bgcolor=ft.Colors.TRANSPARENT,
        on_hover=lambda e: (
            setattr(e.control, "bgcolor", theme_mgr.get("BG3") if e.data else ft.Colors.TRANSPARENT),
            e.control.update(),
        ),
    )

    return [
        ft.Container(expand=True),          # spacer dorong ke bawah
        import_export_btn,
        build_theme_toggle(page, show_label=True),
        ft.Container(height=8),             # bottom padding
    ]