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

TOKO_TABLES = {
    "tokped_ingredients": "Tokopedia",
    "alfagift_ingredients": "Alfagift",
    "aeon_ingredients": "AEON",
}


def _load_table(table_name: str, input_path: str) -> tuple[int, int]:
    """Import data dari file JSON ke tabel tertentu. Return (imported, skipped)."""
    with open(input_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    if not isinstance(rows, list):
        raise ValueError("Format file tidak valid. Harus berupa list JSON.")

    db    = TinyDB(DB_PATH)
    table = db.table(table_name)
    R     = Query()

    imported = 0
    skipped  = 0
    for row in rows:
        saved_id = row.get("saved_id", "") or row.get("keyword", "")
        if saved_id and table.search(R.saved_id == saved_id):
            skipped += 1
        else:
            table.insert(row)
            imported += 1

    return imported, skipped

def _open_file_dialog(callback):
    """Buka file explorer untuk pilih file JSON."""
    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title     = "Pilih File Import",
                filetypes = [("JSON file", "*.json"), ("Semua file", "*.*")],
            )
            root.destroy()
            if path:
                callback(path)
        except Exception as ex:
            print(f"[importer] error: {ex}")
            
    threading.Thread(target=run, daemon=True).start()

def show_import_dialog(page: ft.Page, on_done=None):
    """
    Dialog import:
    - My Recipes (utama)
    - Advanced: pilih data toko
    """
    from rafy.theme import theme_mgr

    def BG2():   return theme_mgr.get("BG2") or "#242424"
    def BG3():   return theme_mgr.get("BG3") or "#2E2E2E"
    def BG4():   return theme_mgr.get("BG4") or "#363636"
    def TEXT():  return theme_mgr.get("TEXT") or "#F0F0EC"
    def TEXT2(): return theme_mgr.get("TEXT2") or "#B0B0AB"
    def TEXT3(): return theme_mgr.get("TEXT3") or "#707070"

    ORANGE = "#E8440A"
    GREEN  = "#2E9E5B"

    selected_mode = {"val": "my_recipes"}  # "my_recipes" atau tabel toko

    # Radio pilihan
    mode_group = ft.RadioGroup(
        value="my_recipes",
        content=ft.Column(
            controls=[
                ft.Radio(
                    value="my_recipes",
                    label="My Recipes",
                    fill_color=ORANGE,
                ),
            ],
            spacing=4,
        ),
        on_change=lambda e: selected_mode.update({"val": e.control.value}),
    )

    # Advanced section
    show_advanced = {"val": False}
    toko_radios   = []
    for table_key, label in TOKO_TABLES.items():
        r = ft.Radio(value=table_key, label=label, fill_color=ORANGE)
        toko_radios.append(r)
        mode_group.content.controls.append(r)

    # Sembunyikan toko radio awalnya
    for r in toko_radios:
        r.visible = False

    advanced_btn = ft.TextButton(
        "▶ Import data toko lainnya",
        style=ft.ButtonStyle(color=TEXT3()),
    )

    def toggle_advanced(e):
        show_advanced["val"] = not show_advanced["val"]
        for r in toko_radios:
            r.visible = show_advanced["val"]
            r.update()
        advanced_btn.text = (
            "▼ Import data toko lainnya"
            if show_advanced["val"]
            else "▶ Import data toko lainnya"
        )
        advanced_btn.update()

    advanced_btn.on_click = toggle_advanced

    def do_import(e):
        dialog.open = False
        page.update()

        table_name = selected_mode["val"]
        filename   = f"{table_name}.json"

        def on_path_chosen(path: str):
            try:
                imported, skipped = _load_table(table_name, path)
                msg  = f"✓ {imported} data diimport"
                if skipped > 0:
                    msg += f" ({skipped} dilewati)"
                tipe = "success" if imported > 0 else "warning"
                show_snack(page, msg, tipe)
                if on_done:
                    on_done(imported, skipped)
            except ValueError as ex:
                show_snack(page, f"File tidak valid: {ex}", "error")
            except Exception as ex:
                show_snack(page, f"Import gagal: {ex}", "error")

        _open_file_dialog(on_path_chosen)

    def do_cancel(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal   = True,
        bgcolor = BG2(),
        title   = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.UPLOAD_OUTLINED, color=GREEN, size=22),
                    bgcolor=BG4(),
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.all(6),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Import", color=TEXT(),
                                weight=ft.FontWeight.BOLD, size=16),
                        ft.Text("Muat data dari file JSON",
                                color=TEXT3(), size=11),
                    ],
                    spacing=1,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content = ft.Container(
            width=380,
            content=ft.Column(
                controls=[
                    ft.Text("Pilih data yang mau diimport:",
                            color=TEXT2(), size=13),
                    mode_group,
                    advanced_btn,
                ],
                spacing=8,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Batal", on_click=do_cancel,
                          style=ft.ButtonStyle(color=TEXT3())),
            ft.ElevatedButton(
                "📥 Pilih File",
                bgcolor=GREEN, color="#FFFFFF",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=do_import,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()