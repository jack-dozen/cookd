"""
fadhil/eksporter.py — Export my_recipes ke file JSON
Dipanggil dari sidebar saat user klik Import/Export → pilih Export

Cara pakai:
    from fadhil.eksporter import export_my_recipes
    export_my_recipes(page, on_done=lambda path: print(f"Disimpan ke {path}"))
"""

import os
import json
import threading

import flet as ft
from tinydb import TinyDB

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')

# ══════════════════════════════════════════════════════════════════════════════
# WARNA
# ══════════════════════════════════════════════════════════════════════════════

BG2    = "#242424"
BG3    = "#2E2E2E"
BG4    = "#363636"
TEXT   = "#F0F0EC"
TEXT2  = "#B0B0AB"
TEXT3  = "#707070"
ORANGE = "#E8440A"
GREEN  = "#2E9E5B"
RED    = "#C0392B"

# ══════════════════════════════════════════════════════════════════════════════
# CORE: ambil data & simpan ke file
# ══════════════════════════════════════════════════════════════════════════════

def _get_my_recipes() -> list[dict]:
    """Ambil semua data dari tabel my_recipes."""
    db = TinyDB(DB_PATH)
    return db.table("my_recipes").all()


def _save_to_file(output_path: str) -> int:
    """
    Simpan my_recipes ke file JSON.
    Return: jumlah baris yang diekspor.
    """
    rows = _get_my_recipes()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    return len(rows)


def _open_save_dialog(callback):
    """
    Buka file explorer untuk pilih lokasi & nama file simpan.
    Jalankan di thread terpisah, panggil callback(path) setelah selesai.
    """
    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.asksaveasfilename(
                title            = "Simpan Export My Recipes",
                defaultextension = ".json",
                filetypes        = [("JSON file", "*.json"), ("Semua file", "*.*")],
                initialfile      = "my_recipes_export.json",
            )
            root.destroy()
            if path:
                callback(path)
        except Exception as ex:
            print(f"[eksporter] error: {ex}")

    threading.Thread(target=run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA: export_my_recipes
# ══════════════════════════════════════════════════════════════════════════════

def export_my_recipes(page: ft.Page, on_done=None):
    """
    Buka file explorer → pilih lokasi simpan → export my_recipes ke JSON.

    Params:
        page    : ft.Page
        on_done : callback(path: str, count: int) dipanggil setelah berhasil
    """

    def show_snack(msg: str, color=GREEN):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=color),
            bgcolor=BG2,
            duration=3500,
        )
        page.snack_bar.open = True
        page.update()

    def on_path_chosen(path: str):
        try:
            count = _save_to_file(path)
            show_snack(f"✓ {count} resep diekspor ke {os.path.basename(path)}")
            if on_done:
                on_done(path, count)
        except Exception as ex:
            show_snack(f"Export gagal: {ex}", color=RED)

    _open_save_dialog(on_path_chosen)