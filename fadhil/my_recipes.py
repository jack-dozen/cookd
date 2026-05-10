"""
fadhil/my_recipes.py — Halaman My Recipes aplikasi Cookd
"""

import os
import json
import hashlib
import base64
import sys
import threading
from datetime import datetime

import flet as ft
from tinydb import TinyDB, Query

# ══════════════════════════════════════════════════════════════════════════════
# PATH
# ══════════════════════════════════════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')

# ══════════════════════════════════════════════════════════════════════════════
# WARNA
# ══════════════════════════════════════════════════════════════════════════════

BG     = "#1A1A1A"
BG2    = "#242424"
BG3    = "#2E2E2E"
BG4    = "#363636"
TEXT   = "#F0F0EC"
TEXT2  = "#B0B0AB"
TEXT3  = "#707070"
ORANGE = "#E8440A"
BORDER = "rgba(255,255,255,0.08)"
GREEN  = "#2E9E5B"
RED    = "#C0392B"
# Export untuk kompatibilitas import di Gui.py
on_view_recipe = None

# ══════════════════════════════════════════════════════════════════════════════
# IMAGE HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _path_to_base64(path: str) -> str:
    try:
        ext  = os.path.splitext(path)[1].lower().strip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

def _open_file_dialog(callback):
    """Buka file explorer pakai tkinter di thread terpisah, panggil callback(path)."""
    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title="Pilih Foto Resep",
                filetypes=[("Gambar", "*.jpg *.jpeg *.png *.webp"), ("Semua", "*.*")],
            )
            root.destroy()
            if path:
                callback(path)
        except Exception as ex:
            print(f"[file dialog] error: {ex}")
    threading.Thread(target=run, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _table():
    return TinyDB(DB_PATH).table("my_recipes")

def get_all() -> list[dict]:
    rows = _table().all()
    for r in rows:
        # Kompatibilitas field lama
        if "image_url" in r and "image_data" not in r:
            r["image_data"] = r.get("image_url", "")
    return sorted(rows, key=lambda x: x.get("saved_at", ""), reverse=True)

def search_recipes(keyword: str) -> list[dict]:
    all_data = get_all()
    if not keyword.strip():
        return all_data
    kw = keyword.lower()
    return [r for r in all_data if kw in r.get("recipe_name", "").lower()]

def save_recipe(recipe_id, recipe_name, notes="",
                ingredients_have=None, ingredients_all=None,
                steps=None, image_data="",
                cook_time=0, portion=0,
                source="Cookpad") -> dict | None:
    table = _table()
    R     = Query()
    if table.search(R.recipe_id == recipe_id):
        return None
    row = {
        "saved_id":         _make_id(recipe_id + _now()),
        "recipe_id":        recipe_id,
        "recipe_name":      recipe_name,
        "notes":            notes,
        "ingredients_have": ingredients_have or [],
        "ingredients_all":  ingredients_all or [],
        "steps":            steps or [],
        "image_data":       image_data,
        "cook_time":        cook_time,
        "portion":          portion,
        "source":           source,
        "saved_at":         _now(),
        "last_updated":     _now(),
    }
    table.insert(row)
    return row

def update_recipe(saved_id: str, data: dict) -> bool:
    table = _table()
    R     = Query()
    if not table.search(R.saved_id == saved_id):
        return False
    data["last_updated"] = _now()
    table.update(data, R.saved_id == saved_id)
    return True

def delete_recipe(saved_id: str) -> bool:
    table = _table()
    R     = Query()
    if not table.search(R.saved_id == saved_id):
        return False
    table.remove(R.saved_id == saved_id)
    return True

def is_saved(recipe_id: str) -> bool:
    return bool(_table().search(Query().recipe_id == recipe_id))

def export_json() -> str:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'zaky'))
        from export_utils import export_table
        return export_table("my_recipes")
    except ImportError:
        rows     = get_all()
        out_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'my_recipes.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        return out_path

def import_json(file_path: str) -> int:
    if not os.path.exists(file_path):
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        rows = json.load(f)
    table = _table()
    R     = Query()
    count = 0
    for row in rows:
        if not table.search(R.saved_id == row.get("saved_id", "")):
            table.insert(row)
            count += 1
    return count

# ══════════════════════════════════════════════════════════════════════════════
# CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

class SavedController:

    @staticmethod
    def validate_name(name: str) -> str | None:
        if not name.strip():
            return "Nama resep tidak boleh kosong."
        if len(name.strip()) < 3:
            return "Nama resep minimal 3 karakter."
        return None

    @staticmethod
    def validate_notes(notes: str) -> str | None:
        if len(notes) > 500:
            return "Catatan maksimal 500 karakter."
        return None

    @staticmethod
    def validate_int(value: str, field: str) -> tuple[int, str | None]:
        if not value.strip():
            return 0, None
        try:
            val = int(value.strip())
            if val < 0:
                return 0, f"{field} tidak boleh negatif."
            return val, None
        except ValueError:
            return 0, f"{field} harus berupa angka."

    @staticmethod
    def do_save(recipe_name, notes, ingredients, steps,
                portion_str, cook_time_str,
                image_data="") -> tuple[dict | None, str | None]:
        err = SavedController.validate_name(recipe_name)
        if err: return None, err
        err = SavedController.validate_notes(notes)
        if err: return None, err
        portion,   err = SavedController.validate_int(portion_str,   "Porsi")
        if err: return None, err
        cook_time, err = SavedController.validate_int(cook_time_str, "Waktu masak")
        if err: return None, err

        row = save_recipe(
            recipe_id       = _make_id(recipe_name + _now()),
            recipe_name     = recipe_name.strip(),
            notes           = notes.strip(),
            ingredients_all = ingredients,
            steps           = steps,
            cook_time       = cook_time,
            portion         = portion,
            image_data      = image_data,
            source          = "Manual",
        )
        return row, None

    @staticmethod
    def do_edit(saved_id, recipe_name, notes, ingredients, steps,
                portion_str, cook_time_str,
                image_data=None) -> tuple[bool, str | None]:
        err = SavedController.validate_name(recipe_name)
        if err: return False, err
        err = SavedController.validate_notes(notes)
        if err: return False, err
        portion,   err = SavedController.validate_int(portion_str,   "Porsi")
        if err: return False, err
        cook_time, err = SavedController.validate_int(cook_time_str, "Waktu masak")
        if err: return False, err

        data = {
            "recipe_name":     recipe_name.strip(),
            "notes":           notes.strip(),
            "ingredients_all": ingredients,
            "steps":           steps,
            "portion":         portion,
            "cook_time":       cook_time,
        }
        if image_data is not None:
            data["image_data"] = image_data

        return update_recipe(saved_id, data), None

# ══════════════════════════════════════════════════════════════════════════════
# FORMAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_portion(v) -> str:
    try:
        val = int(v)
        return f"{val} porsi" if val > 0 else ""
    except (TypeError, ValueError):
        return str(v) if v else ""

def _fmt_time(v) -> str:
    try:
        val = int(v)
        return f"{val} menit" if val > 0 else ""
    except (TypeError, ValueError):
        return str(v) if v else ""

def _to_str(v) -> str:
    if v is None or v == 0:
        return ""
    return str(v)

# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _field(label, value="", multiline=False, min_lines=1,
           max_lines=4, hint="", keyboard_type=None) -> ft.TextField:
    return ft.TextField(
        label                = label,
        value                = value,
        hint_text            = hint,
        multiline            = multiline,
        min_lines            = min_lines if multiline else None,
        max_lines            = max_lines if multiline else None,
        keyboard_type        = keyboard_type,
        bgcolor              = BG3,
        color                = TEXT,
        label_style          = ft.TextStyle(color=TEXT2),
        hint_style           = ft.TextStyle(color=TEXT3),
        border_color         = BORDER,
        focused_border_color = ORANGE,
        content_padding      = ft.Padding.all(12),
    )

def _section_label(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    width=3, height=14, bgcolor=ORANGE,
                    border_radius=ft.BorderRadius.all(2),
                ),
                ft.Text(text, color=TEXT2, size=11, weight=ft.FontWeight.W_600),
            ],
            spacing=8,
        ),
        margin=ft.Margin.only(top=4),
    )

def _default_image_box(height=160) -> ft.Container:
    return ft.Container(
        bgcolor=BG4,
        height=height,
        border_radius=ft.BorderRadius.all(10),
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, color=TEXT3, size=40),
                ft.Text("Belum ada foto", color=TEXT3, size=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
        ),
        alignment=ft.Alignment(0, 0),
    )

# ══════════════════════════════════════════════════════════════════════════════
# FOTO PICKER WIDGET
# ══════════════════════════════════════════════════════════════════════════════

def _make_photo_widget(page: ft.Page, initial_data=""):
    """
    Return (widget, get_data_fn).
    get_data_fn() -> str|None
      - None  : tidak berubah
      - ""    : dihapus
      - str   : base64 baru
    """
    state = {"data": initial_data, "changed": False}

    # Preview container — isinya diganti dinamis
    preview_container = ft.Container(
        content=ft.Image(
            src=initial_data,
            width=float("inf"),
            height=160,
            fit="cover",
            border_radius=ft.BorderRadius.all(10),
            error_content=_default_image_box(160),
        ) if initial_data else _default_image_box(160),
        height=160,
        border_radius=ft.BorderRadius.all(10),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    filename_text = ft.Text(
        os.path.basename(initial_data) if initial_data and not initial_data.startswith("data:") else
        ("Foto tersimpan" if initial_data else "Belum ada foto dipilih"),
        color=TEXT3, size=11, italic=True,
        expand=True,
        overflow=ft.TextOverflow.ELLIPSIS,
        max_lines=1,
    )

    remove_btn = ft.TextButton(
        "Hapus",
        style   = ft.ButtonStyle(color=RED),
        visible = bool(initial_data),
    )

    def _set_preview(data: str, label: str):
        if data:
            preview_container.content = ft.Image(
                src=data,
                width=float("inf"),
                height=160,
                fit="cover",
                border_radius=ft.BorderRadius.all(10),
                error_content=_default_image_box(160),
            )
        else:
            preview_container.content = _default_image_box(160)
        filename_text.value  = label
        remove_btn.visible   = bool(data)
        preview_container.update()
        filename_text.update()
        remove_btn.update()

    def on_file_chosen(path: str):
        data = _path_to_base64(path)
        if not data:
            filename_text.value = "Gagal membaca file."
            filename_text.update()
            return
        state["data"]    = data
        state["changed"] = True
        page.run_task(_do_update, data, os.path.basename(path))

    async def _do_update(data, label):
        _set_preview(data, label)

    def pick_photo(e):
        _open_file_dialog(on_file_chosen)

    def on_remove(e):
        state["data"]    = ""
        state["changed"] = True
        _set_preview("", "Belum ada foto dipilih")

    pick_btn = ft.ElevatedButton(
        "📷  Pilih Foto",
        bgcolor  = ORANGE,
        color    = "#FFFFFF",
        style    = ft.ButtonStyle(
            shape   = ft.RoundedRectangleBorder(radius=8),
            padding = ft.Padding.symmetric(horizontal=16, vertical=10),
        ),
        on_click = pick_photo,
    )
    remove_btn.on_click = on_remove

    widget = ft.Column(
        controls=[
            preview_container,
            ft.Row(
                controls=[pick_btn, remove_btn, filename_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
        ],
        spacing=10,
    )

    def get_data():
        return state["data"] if state["changed"] else None

    return widget, get_data

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Tambah Resep
# ══════════════════════════════════════════════════════════════════════════════

def AddRecipeDialog(page: ft.Page, on_saved) -> ft.AlertDialog:

    name_field        = _field("Nama Resep *")
    portion_field     = _field("Porsi", hint="cth: 4",
                                keyboard_type=ft.KeyboardType.NUMBER)
    cook_time_field   = _field("Waktu Masak (menit)", hint="cth: 30",
                                keyboard_type=ft.KeyboardType.NUMBER)
    ingredients_field = _field(
        "Bahan-bahan",
        multiline=True, min_lines=4, max_lines=8,
        hint="Satu baris = satu bahan\ncth:\n2 butir telur\n1 sdt garam",
    )
    steps_field = _field(
        "Langkah-langkah",
        multiline=True, min_lines=4, max_lines=8,
        hint="Satu baris = satu langkah\ncth:\nCincang bawang putih\nTumis hingga harum",
    )
    notes_field = _field(
        "Catatan (opsional)",
        multiline=True, min_lines=2, max_lines=3,
        hint="Catatan pribadi kamu...",
    )
    error_text = ft.Text("", color=RED, size=11)

    photo_widget, get_photo_data = _make_photo_widget(page)

    def on_save(e):
        ingredients = [l.strip() for l in (ingredients_field.value or "").splitlines() if l.strip()]
        steps       = [l.strip() for l in (steps_field.value or "").splitlines() if l.strip()]
        image_data  = get_photo_data() or ""

        row, err = SavedController.do_save(
            recipe_name   = name_field.value or "",
            notes         = notes_field.value or "",
            ingredients   = ingredients,
            steps         = steps,
            portion_str   = portion_field.value or "",
            cook_time_str = cook_time_field.value or "",
            image_data    = image_data,
        )
        if err:
            error_text.value = err
            error_text.update()
            return

        dialog.open = False
        page.update()
        if row:
            on_saved(row)

    def on_cancel(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal   = True,
        bgcolor = BG2,
        title   = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=ORANGE, size=22),
                        bgcolor=BG4,
                        border_radius=ft.BorderRadius.all(8),
                        padding=ft.Padding.all(6),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Tambah Resep", color=TEXT,
                                    weight=ft.FontWeight.BOLD, size=16),
                            ft.Text("Isi detail resep kamu", color=TEXT3, size=11),
                        ],
                        spacing=1,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        content = ft.Container(
            width=540,
            height=600,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=14,
                controls=[
                    _section_label("FOTO RESEP"),
                    photo_widget,
                    _section_label("INFO DASAR"),
                    name_field,
                    ft.Row(controls=[portion_field, cook_time_field], spacing=10),
                    _section_label("BAHAN-BAHAN"),
                    ingredients_field,
                    _section_label("LANGKAH-LANGKAH"),
                    steps_field,
                    _section_label("CATATAN"),
                    notes_field,
                    error_text,
                ],
            ),
        ),
        actions=[
            ft.TextButton(
                "Batal",
                style    = ft.ButtonStyle(color=TEXT3),
                on_click = on_cancel,
            ),
            ft.ElevatedButton(
                "💾  Simpan Resep",
                bgcolor  = ORANGE,
                color    = "#FFFFFF",
                style    = ft.ButtonStyle(
                    shape   = ft.RoundedRectangleBorder(radius=8),
                    padding = ft.Padding.symmetric(horizontal=20, vertical=12),
                ),
                on_click = on_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Edit Resep
# ══════════════════════════════════════════════════════════════════════════════

def EditRecipeDialog(page: ft.Page, saved: dict, on_saved) -> ft.AlertDialog:

    name_field        = _field("Nama Resep *", value=saved.get("recipe_name", ""))
    portion_field     = _field("Porsi", value=_to_str(saved.get("portion")),
                                hint="cth: 4", keyboard_type=ft.KeyboardType.NUMBER)
    cook_time_field   = _field("Waktu Masak (menit)", value=_to_str(saved.get("cook_time")),
                                hint="cth: 30", keyboard_type=ft.KeyboardType.NUMBER)
    ingredients_field = _field(
        "Bahan-bahan",
        value="\n".join(saved.get("ingredients_all", [])),
        multiline=True, min_lines=4, max_lines=8,
        hint="Satu baris = satu bahan",
    )
    steps_field = _field(
        "Langkah-langkah",
        value="\n".join(saved.get("steps", [])),
        multiline=True, min_lines=4, max_lines=8,
        hint="Satu baris = satu langkah",
    )
    notes_field = _field(
        "Catatan",
        value=saved.get("notes", ""),
        multiline=True, min_lines=2, max_lines=3,
        hint="Catatan pribadi kamu...",
    )
    error_text = ft.Text("", color=RED, size=11)

    photo_widget, get_photo_data = _make_photo_widget(
        page, initial_data=saved.get("image_data", ""),
    )

    def on_save(e):
        ingredients = [l.strip() for l in (ingredients_field.value or "").splitlines() if l.strip()]
        steps       = [l.strip() for l in (steps_field.value or "").splitlines() if l.strip()]
        new_img     = get_photo_data()  # None=tidak berubah, ""=hapus, str=baru

        ok, err = SavedController.do_edit(
            saved_id      = saved["saved_id"],
            recipe_name   = name_field.value or "",
            notes         = notes_field.value or "",
            ingredients   = ingredients,
            steps         = steps,
            portion_str   = portion_field.value or "",
            cook_time_str = cook_time_field.value or "",
            image_data    = new_img,
        )
        if err:
            error_text.value = err
            error_text.update()
            return

        dialog.open = False
        page.update()
        if ok:
            on_saved()

    def on_cancel(e):
        dialog.open = False
        page.update()

    title_name = saved.get("recipe_name", "")
    if len(title_name) > 32:
        title_name = title_name[:32] + "…"

    dialog = ft.AlertDialog(
        modal   = True,
        bgcolor = BG2,
        title   = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.EDIT_OUTLINED, color=ORANGE, size=22),
                        bgcolor=BG4,
                        border_radius=ft.BorderRadius.all(8),
                        padding=ft.Padding.all(6),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Edit Resep", color=TEXT,
                                    weight=ft.FontWeight.BOLD, size=16),
                            ft.Text(title_name, color=TEXT3, size=11),
                        ],
                        spacing=1,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        content = ft.Container(
            width=540,
            height=600,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=14,
                controls=[
                    _section_label("FOTO RESEP"),
                    photo_widget,
                    _section_label("INFO DASAR"),
                    name_field,
                    ft.Row(controls=[portion_field, cook_time_field], spacing=10),
                    _section_label("BAHAN-BAHAN"),
                    ingredients_field,
                    _section_label("LANGKAH-LANGKAH"),
                    steps_field,
                    _section_label("CATATAN"),
                    notes_field,
                    error_text,
                ],
            ),
        ),
        actions=[
            ft.TextButton(
                "Batal",
                style    = ft.ButtonStyle(color=TEXT3),
                on_click = on_cancel,
            ),
            ft.ElevatedButton(
                "💾  Simpan Perubahan",
                bgcolor  = ORANGE,
                color    = "#FFFFFF",
                style    = ft.ButtonStyle(
                    shape   = ft.RoundedRectangleBorder(radius=8),
                    padding = ft.Padding.symmetric(horizontal=20, vertical=12),
                ),
                on_click = on_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Konfirmasi Hapus
# ══════════════════════════════════════════════════════════════════════════════

def ConfirmDeleteDialog(page: ft.Page, recipe_name: str, on_confirmed) -> ft.AlertDialog:
    def on_yes(e):
        on_confirmed()
        dialog.open = False
        page.update()

    def on_no(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal   = True,
        bgcolor = BG2,
        title   = ft.Row(
            controls=[
                ft.Icon(ft.Icons.DELETE_OUTLINE, color=RED, size=22),
                ft.Text("Hapus Resep?", color=RED, weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        ),
        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f'"{recipe_name}"', color=TEXT,
                            weight=ft.FontWeight.BOLD, size=14),
                    ft.Text("akan dihapus permanen dan tidak bisa dikembalikan.",
                            color=TEXT2, size=13),
                ],
                spacing=6,
            ),
        ),
        actions=[
            ft.TextButton("Batal", style=ft.ButtonStyle(color=TEXT3), on_click=on_no),
            ft.ElevatedButton(
                "🗑  Hapus",
                bgcolor  = RED,
                color    = "#FFFFFF",
                style    = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click = on_yes,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# KARTU RESEP
# ══════════════════════════════════════════════════════════════════════════════

def _recipe_card(saved: dict, on_view, on_edit, on_delete) -> ft.Container:
    recipe_name  = saved.get("recipe_name", "Resep")
    image_data   = saved.get("image_data", "")
    notes        = saved.get("notes", "")
    source       = saved.get("source", "Cookpad")
    portion_text = _fmt_portion(saved.get("portion"))
    time_text    = _fmt_time(saved.get("cook_time"))

    meta_parts = []
    if portion_text:   meta_parts.append(f"👥 {portion_text}")
    if time_text:      meta_parts.append(f"⏱ {time_text}")
    if source:         meta_parts.append(source)
    meta_text = " · ".join(meta_parts) if meta_parts else "Resep tersimpan"

    if image_data:
        img_widget = ft.Image(
            src=image_data,
            width=float("inf"),
            height=140,
            fit="cover",
            error_content=ft.Container(
                bgcolor=BG4, height=140,
                content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3, size=36),
                alignment=ft.Alignment(0, 0),
            ),
        )
    else:
        img_widget = ft.Container(
            bgcolor=BG4, height=140,
            content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3, size=36),
            alignment=ft.Alignment(0, 0),
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            img_widget,
                            ft.Container(
                                height=140,
                                gradient=ft.LinearGradient(
                                    begin=ft.Alignment(0, -1),
                                    end=ft.Alignment(0, 1),
                                    colors=["transparent", "#88000000"],
                                ),
                            ),
                        ],
                        height=140,
                    ),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border_radius=ft.BorderRadius.only(top_left=10, top_right=10),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(recipe_name, color=TEXT, size=14,
                                    weight=ft.FontWeight.BOLD,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(meta_text, color=TEXT2, size=12,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"📝 {notes}", color=TEXT3, size=11,
                                    italic=True, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    visible=bool(notes)),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton(
                                        "Lihat",
                                        style=ft.ButtonStyle(
                                            color=ORANGE,
                                            bgcolor="transparent",
                                            side=ft.BorderSide(1.5, ORANGE),
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                            padding=ft.Padding.symmetric(
                                                horizontal=10, vertical=5),
                                        ),
                                        on_click=lambda e: on_view(saved),
                                    ),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_color=TEXT2, icon_size=18,
                                        tooltip="Edit Resep",
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                            side=ft.BorderSide(1.5, BG4),
                                        ),
                                        on_click=lambda e: on_edit(saved),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=RED, icon_size=18,
                                        tooltip="Hapus",
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                            side=ft.BorderSide(1.5, BG4),
                                        ),
                                        on_click=lambda e: on_delete(saved),
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=5,
                    ),
                    padding=ft.Padding.all(12),
                ),
            ],
            spacing=0,
        ),
        bgcolor=BG3,
        border=ft.Border.all(1, BG4),
        border_radius=ft.BorderRadius.all(10),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

# ══════════════════════════════════════════════════════════════════════════════
# MY RECIPES PAGE
# ══════════════════════════════════════════════════════════════════════════════

def MyRecipesPage(page: ft.Page, navigate, on_view_recipe=None) -> ft.Container:

    search_keyword = {"value": ""}
    grid = ft.Row(wrap=True, spacing=14, run_spacing=14, controls=[])

    count_badge = ft.Container(
        content=ft.Text("Tersimpan: 0", color=TEXT2, size=12),
        bgcolor=BG3,
        border=ft.Border.all(1, BG4),
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border_radius=ft.BorderRadius.all(20),
    )

    empty_state = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.BOOK_OUTLINED, color=TEXT3, size=48),
                ft.Text("Belum ada resep tersimpan.", color=TEXT2, size=14),
                ft.Text("Cari resep di Finder dan klik ♥ untuk menyimpan.",
                        color=TEXT3, size=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.Alignment(0, 0),
        padding=ft.Padding.all(60),
        visible=False,
    )

    def show_snack(msg: str, color=GREEN):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=color),
            bgcolor=BG2, duration=3000,
        )
        page.snack_bar.open = True
        page.update()

    def refresh(keyword: str = ""):
        search_keyword["value"] = keyword
        saved_list = search_recipes(keyword)
        count_badge.content.value = f"Tersimpan: {len(get_all())}"
        grid.controls.clear()
        empty_state.visible = len(saved_list) == 0
        for saved in saved_list:
            grid.controls.append(
                ft.Container(
                    content=_recipe_card(
                        saved=saved, on_view=_on_view,
                        on_edit=_on_edit, on_delete=_on_delete,
                    ),
                    width=320,
                )
            )
        try:
            grid.update()
            empty_state.update()
            count_badge.update()
        except Exception:
            pass

    def _on_view(saved: dict):
        raw_ingredients = saved.get("ingredients_all", [])
        ingredients = []
        for ing in raw_ingredients:
            if isinstance(ing, dict):
                ingredients.append(ing)  # sudah dict, kirim langsung
            else:
                # konversi string jadi dict dengan format yang Gui.py harapkan
                ingredients.append({"qty": "", "name": str(ing)})

        raw_steps = saved.get("steps", [])
        steps = []
        for step in raw_steps:
            if isinstance(step, dict):
                steps.append(step)
            else:
                steps.append({"text": str(step), "images": []})

        recipe = {
            "recipe_id":   saved.get("recipe_id", ""),
            "name":        saved.get("recipe_name", ""),
            "author":      "",
            "ingredients": ingredients,
            "steps":       steps,
            "image_url":   saved.get("image_data", "") or saved.get("image_url", ""),
            "cook_time":   _fmt_time(saved.get("cook_time")),
            "portion":     _fmt_portion(saved.get("portion")),
            "source_url":  saved.get("source_url", ""),
            "source":      saved.get("source", ""),
        }
        if on_view_recipe:
            on_view_recipe(recipe)
        else:
            navigate("detail")

        recipe = {
            "recipe_id":   saved.get("recipe_id", ""),
            "name":        saved.get("recipe_name", ""),
            "author":      "",
            "ingredients": ingredients,
            "steps":       steps,
            "image_url":   saved.get("image_data", "") or saved.get("image_url", ""),
            "cook_time":   _fmt_time(saved.get("cook_time")),
            "portion":     _fmt_portion(saved.get("portion")),
            "source":      saved.get("source", ""),
        }
        if on_view_recipe:
            on_view_recipe(recipe)
        else:
            navigate("detail")

    def _on_edit(saved: dict):
        def on_saved():
            show_snack(f"✓ '{saved.get('recipe_name')}' diperbarui!")
            refresh(search_keyword["value"])
        dialog = EditRecipeDialog(page=page, saved=saved, on_saved=on_saved)
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_delete(saved: dict):
        def on_confirmed():
            if delete_recipe(saved["saved_id"]):
                show_snack(f"'{saved['recipe_name']}' dihapus.", color=RED)
                refresh(search_keyword["value"])
        dialog = ConfirmDeleteDialog(
            page=page, recipe_name=saved.get("recipe_name", ""),
            on_confirmed=on_confirmed,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_add(e):
        def on_saved(row):
            show_snack(f"✓ '{row['recipe_name']}' ditambahkan!")
            refresh(search_keyword["value"])
        dialog = AddRecipeDialog(page=page, on_saved=on_saved)
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_export(e):
        try:
            export_json()
            show_snack("✓ Diekspor ke Downloads/my_recipes.json")
        except Exception as ex:
            show_snack(f"Export gagal: {ex}", color=RED)

    search_field = ft.TextField(
        hint_text            = "🔍  Cari resep tersimpan...",
        bgcolor              = BG3, color=TEXT,
        hint_style           = ft.TextStyle(color=TEXT3),
        border_color         = BG4,
        focused_border_color = ORANGE,
        border_radius        = ft.BorderRadius.all(24),
        content_padding      = ft.Padding.symmetric(horizontal=16, vertical=10),
        expand               = True,
        on_change            = lambda e: refresh(e.control.value),
    )

    page_content = ft.Container(
        expand=True, bgcolor=BG, visible=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("My Recipes", size=17, color=TEXT,
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text("Resep yang kamu simpan",
                                            size=12, color=TEXT3),
                                ],
                                spacing=2, expand=True,
                            ),
                            count_badge,
                            ft.ElevatedButton(
                                "+ Tambah",
                                bgcolor=ORANGE, color="#FFFFFF",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=20),
                                    padding=ft.Padding.symmetric(horizontal=14, vertical=7),
                                ),
                                on_click=_on_add,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DOWNLOAD_OUTLINED,
                                icon_color=TEXT2,
                                tooltip="Export JSON",
                                on_click=_on_export,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=BG2,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=14),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BG4)),
                ),
                ft.Container(
                    content=search_field,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=12),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[grid, empty_state],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=0),
                ),
            ],
            spacing=0, expand=True,
        ),
    )

    page_content.refresh = refresh
    return page_content