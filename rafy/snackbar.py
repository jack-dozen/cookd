"""
snackbar.py — CookD
Utility untuk menampilkan snackbar notifikasi secara konsisten.
Taruh di folder rafy/, import dari modul lain dengan sys.path.
"""

import flet as ft
import sys
import os

sys.path.append(os.path.dirname(__file__))
from theme import ORANGE, GREEN, RED, AMBER, get

# ─────────────────────────────────────────────────────────────────────
# DURASI DEFAULT
# ─────────────────────────────────────────────────────────────────────
DURATION_SHORT  = 2000   # ms
DURATION_NORMAL = 3000
DURATION_LONG   = 5000


# ─────────────────────────────────────────────────────────────────────
# SHOW HELPERS
# ─────────────────────────────────────────────────────────────────────
def show(page: ft.Page, message: str, color: str = None, duration: int = DURATION_NORMAL):
    """Tampilkan snackbar dengan warna custom."""
    bg    = get("BG3")
    color = color or ft.Colors.WHITE

    page.snack_bar = ft.SnackBar(
        content  = ft.Text(message, color=color),
        bgcolor  = bg,
        duration = duration,
    )
    page.snack_bar.open = True
    page.update()


def show_success(page: ft.Page, message: str, duration: int = DURATION_NORMAL):
    """Snackbar hijau — untuk aksi berhasil."""
    show(page, f"✓  {message}", color=GREEN, duration=duration)


def show_error(page: ft.Page, message: str, duration: int = DURATION_LONG):
    """Snackbar merah — untuk error."""
    show(page, f"✗  {message}", color=RED, duration=duration)


def show_warning(page: ft.Page, message: str, duration: int = DURATION_NORMAL):
    """Snackbar amber — untuk peringatan."""
    show(page, f"⚠  {message}", color=AMBER, duration=duration)


def show_info(page: ft.Page, message: str, duration: int = DURATION_NORMAL):
    """Snackbar oranye — untuk info netral."""
    show(page, f"ℹ  {message}", color=ORANGE, duration=duration)