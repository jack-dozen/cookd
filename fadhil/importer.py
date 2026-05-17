"""
fadhil/importer.py — Import my_recipes dari file JSON
Dipanggil dari sidebar saat user klik Import/Export → pilih Import

Cara pakai:
    from fadhil.importer import import_my_recipes
    import_my_recipes(page, on_done=lambda count: print(f"{count} resep diimport"))
"""

import os
import json
import threading

import flet as ft
from tinydb import TinyDB, Query
from rafy.snackbar import show_snack

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')

# ══════════════════════════════════════════════════════════════════════════════
# WARNA
# ══════════════════════════════════════════════════════════════════════════════

BG2    = "#242424"
BG3    = "#2E2E2E"
TEXT   = "#F0F0EC"
TEXT2  = "#B0B0AB"
TEXT3  = "#707070"
ORANGE = "#E8440A"
GREEN  = "#2E9E5B"
AMBER  = "#E09020"
RED    = "#C0392B"

# ══════════════════════════════════════════════════════════════════════════════
# CORE: baca file & simpan ke DB
# ══════════════════════════════════════════════════════════════════════════════

def _load_from_file(input_path: str) -> tuple[int, int]:
    """
    Import data dari file JSON ke tabel my_recipes.
    Skip baris yang saved_id-nya sudah ada (tidak overwrite).

    Return: (imported_count, skipped_count)
    """
    with open(input_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    if not isinstance(rows, list):
        raise ValueError("Format file tidak valid. Harus berupa list JSON.")

    db    = TinyDB(DB_PATH)
    table = db.table("my_recipes")
    R     = Query()

    imported = 0
    skipped  = 0

    for row in rows:
        saved_id = row.get("saved_id", "")
        if saved_id and table.search(R.saved_id == saved_id):
            skipped += 1
        else:
            table.insert(row)
            imported += 1

    return imported, skipped


def _open_file_dialog(callback):
    """
    Buka file explorer untuk pilih file JSON yang mau diimport.
    Jalankan di thread terpisah, panggil callback(path) setelah selesai.
    """
    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title     = "Pilih File Import My Recipes",
                filetypes = [("JSON file", "*.json"), ("Semua file", "*.*")],
            )
            root.destroy()
            if path:
                callback(path)
        except Exception as ex:
            print(f"[importer] error: {ex}")

    threading.Thread(target=run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA: import_my_recipes
# ══════════════════════════════════════════════════════════════════════════════

def import_my_recipes(page: ft.Page, on_done=None):
    """
    Buka file explorer → pilih file JSON → import ke my_recipes.

    Params:
        page    : ft.Page
        on_done : callback(imported: int, skipped: int) dipanggil setelah selesai
    """

    def on_path_chosen(path: str):
        try:
            imported, skipped = _load_from_file(path)
            msg = f"✓ {imported} resep diimport"
            if skipped > 0:
                msg += f" ({skipped} dilewati karena sudah ada)"
            tipe = "success" if imported > 0 else "warning"
            show_snack(page, msg, tipe)
            if on_done:
                on_done(imported, skipped)
        except ValueError as ex:
            show_snack(page, f"File tidak valid: {ex}", "error")
        except Exception as ex:
            show_snack(page, f"Import gagal: {ex}", "error")

    _open_file_dialog(on_path_chosen)