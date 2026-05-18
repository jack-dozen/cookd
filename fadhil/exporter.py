"""
fadhil/eksporter.py — Export my_recipes dan data toko ke file JSON
"""

import os
import json
import threading

import flet as ft
from tinydb import TinyDB
from rafy.snackbar import show_snack

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')

BG2    = "#242424"
BG3    = "#2E2E2E"
BG4    = "#363636"
TEXT   = "#F0F0EC"
TEXT2  = "#B0B0AB"
TEXT3  = "#707070"
ORANGE = "#E8440A"
GREEN  = "#2E9E5B"
RED    = "#C0392B"

TOKO_TABLES = {
    "tokped_ingredients": "Tokopedia",
    "alfagift_ingredients": "Alfagift",
    "aeon_ingredients": "AEON",
}


def _save_table(table_name: str, output_path: str) -> int:
    db   = TinyDB(DB_PATH)
    rows = db.table(table_name).all()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    return len(rows)


def _open_save_dialog(filename: str, callback):
    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.asksaveasfilename(
                title            = "Simpan Export",
                defaultextension = ".json",
                filetypes        = [("JSON file", "*.json"), ("Semua file", "*.*")],
                initialfile      = filename,
            )
            root.destroy()
            if path:
                callback(path)
        except Exception as ex:
            print(f"[eksporter] error: {ex}")
    threading.Thread(target=run, daemon=True).start()


def _open_folder_dialog(callback):
    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="Pilih Folder Tujuan Export")
            root.destroy()
            if folder:
                callback(folder)
        except Exception as ex:
            print(f"[eksporter] error: {ex}")
    threading.Thread(target=run, daemon=True).start()


def export_my_recipes(page: ft.Page, on_done=None):
    """Export my_recipes saja — langsung buka save dialog."""
    def on_path_chosen(path: str):
        try:
            count = _save_table("my_recipes", path)
            show_snack(page, f"✓ {count} resep diekspor ke {os.path.basename(path)}", "success")
            if on_done:
                on_done(path, count)
        except Exception as ex:
            show_snack(page, f"Export gagal: {ex}", "error")

    _open_save_dialog("my_recipes.json", on_path_chosen)


def show_export_dialog(page: ft.Page, on_done=None):
    """
    Tampilkan dialog export:
    - My Recipes (utama, selalu diceklis)
    - Advanced: pilih data toko (Tokopedia, Alfagift, AEON)
    """
    from rafy.theme import theme_mgr

    def BG2():    return theme_mgr.get("BG2") or "#242424"
    def BG3():    return theme_mgr.get("BG3") or "#2E2E2E"
    def BG4():    return theme_mgr.get("BG4") or "#363636"
    def TEXT():   return theme_mgr.get("TEXT") or "#F0F0EC"
    def TEXT2():  return theme_mgr.get("TEXT2") or "#B0B0AB"
    def TEXT3():  return theme_mgr.get("TEXT3") or "#707070"

    # State
    show_advanced  = {"val": False}
    toko_checks    = {k: {"val": False} for k in TOKO_TABLES}

    # ── Checkboxes toko ──
    toko_rows = []
    for table_key, label in TOKO_TABLES.items():
        cb = ft.Checkbox(
            label       = label,
            value       = False,
            fill_color  = ORANGE,
            check_color = "#FFFFFF",
            on_change   = lambda e, k=table_key: toko_checks[k].update({"val": e.control.value}),
        )
        toko_rows.append(cb)

    advanced_section = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(height=4),
                ft.Divider(color=BG4(), height=1),
                ft.Container(height=4),
                ft.Text("Pilih data toko yang mau diekspor:",
                        color=TEXT2(), size=12),
                *toko_rows,
            ],
            spacing=6,
            tight=True,
        ),
        visible=False,
        animate_size=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    # ── Toggle advanced ──
    advanced_btn = ft.TextButton(
        "▶ Export data toko lainnya",
        style=ft.ButtonStyle(color=TEXT3()),
    )

    def toggle_advanced(e):
        show_advanced["val"] = not show_advanced["val"]
        advanced_section.visible = show_advanced["val"]
        advanced_btn.text = (
            "▼ Export data toko lainnya"
            if show_advanced["val"]
            else "▶ Export data toko lainnya"
        )
        advanced_section.update()
        advanced_btn.update()

    advanced_btn.on_click = toggle_advanced

    # ── Do export ──
    def do_export(e):
        dialog.open = False
        page.update()

        selected_toko = [k for k, v in toko_checks.items() if v["val"]]

        if not selected_toko:
            # Hanya my_recipes
            export_my_recipes(page, on_done=on_done)
        else:
            # Ada toko yang dipilih → pilih folder, export semua ke sana
            def on_folder_chosen(folder):
                try:
                    # Export my_recipes
                    path = os.path.join(folder, "my_recipes.json")
                    count = _save_table("my_recipes", path)
                    msgs  = [f"my_recipes: {count} resep"]

                    # Export toko yang dipilih
                    for table_key in selected_toko:
                        label    = TOKO_TABLES[table_key]
                        out_path = os.path.join(folder, f"{table_key}.json")
                        n        = _save_table(table_key, out_path)
                        msgs.append(f"{label}: {n} data")

                    show_snack(page, "✓ Export selesai: " + ", ".join(msgs), "success")
                    if on_done:
                        on_done(folder, len(msgs))
                except Exception as ex:
                    show_snack(page, f"Export gagal: {ex}", "error")

            _open_folder_dialog(on_folder_chosen)

    def do_cancel(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal   = True,
        bgcolor = BG2(),
        title   = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.DOWNLOAD_OUTLINED, color=ORANGE, size=22),
                    bgcolor=BG4(),
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.all(6),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Export", color=TEXT(),
                                weight=ft.FontWeight.BOLD, size=16),
                        ft.Text("Simpan data ke file JSON",
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
                    # My Recipes — utama
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ORANGE, size=20),
                                ft.Column(
                                    controls=[
                                        ft.Text("My Recipes", color=TEXT(),
                                                weight=ft.FontWeight.BOLD, size=14),
                                        ft.Text("Resep yang kamu simpan",
                                                color=TEXT2(), size=11),
                                    ],
                                    spacing=2, expand=True,
                                ),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=f"{ORANGE}22",
                        border=ft.Border.all(1, ORANGE),
                        border_radius=ft.BorderRadius.all(10),
                        padding=ft.Padding.all(12),
                    ),
                    advanced_btn,
                    advanced_section,
                ],
                spacing=4,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Batal", on_click=do_cancel,
                          style=ft.ButtonStyle(color=TEXT3())),
            ft.ElevatedButton(
                "📤 Export",
                bgcolor=ORANGE, color="#FFFFFF",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=do_export,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()