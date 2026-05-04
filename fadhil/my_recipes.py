"""
fadhil/MyRecipes.py — Halaman My Recipes aplikasi Cookd
Tampilan sesuai prototype v3: grid 2 kolom, kartu dengan gambar di atas

Dipanggil dari hadi/Gui.py:
    from fadhil.my_recipes import MyRecipesPage
    pages["my-recipes"] = MyRecipesPage(page, navigate)

Fitur:
    - Grid 2 kolom kartu resep
    - Search/filter resep tersimpan
    - Tambah resep manual (AddRecipeDialog)
    - Edit resep lengkap: nama, bahan, langkah, catatan, porsi & waktu (EditRecipeDialog)
    - Hapus resep (ConfirmDeleteDialog)
    - Export JSON (pakai zaky/export_utils.py)
"""

import os
import json
import hashlib
import sys
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
AMBER  = "#E09020"
RED    = "#C0392B"

# ══════════════════════════════════════════════════════════════════════════════
# SAVED RECIPE MODEL
# ══════════════════════════════════════════════════════════════════════════════

def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _table():
    return TinyDB(DB_PATH).table("my_recipes")

def get_all() -> list[dict]:
    rows = _table().all()
    return sorted(rows, key=lambda x: x.get("saved_at", ""), reverse=True)

def search_recipes(keyword: str) -> list[dict]:
    all_data = get_all()
    if not keyword.strip():
        return all_data
    kw = keyword.lower()
    return [r for r in all_data if kw in r.get("recipe_name", "").lower()]

def save_recipe(recipe_id: str, recipe_name: str, notes: str = "",
                ingredients_have: list = None, ingredients_all: list = None,
                steps: list = None, image_url: str = "",
                cook_time: int = 0, portion: int = 0,
                source: str = "Cookpad") -> dict | None:
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
        "image_url":        image_url,
        "cook_time":        cook_time,   # integer, satuan menit
        "portion":          portion,     # integer, satuan orang
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
        rows = get_all()
        downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        output_path = os.path.join(downloads, 'my_recipes.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        return output_path

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
# SAVED CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

class SavedController:

    @staticmethod
    def validate_name(recipe_name: str) -> str | None:
        if not recipe_name.strip():
            return "Nama resep tidak boleh kosong."
        if len(recipe_name.strip()) < 3:
            return "Nama resep minimal 3 karakter."
        return None

    @staticmethod
    def validate_notes(notes: str) -> str | None:
        if len(notes) > 500:
            return "Catatan maksimal 500 karakter."
        return None

    @staticmethod
    def validate_int(value: str, field_name: str) -> tuple[int, str | None]:
        """Validasi input integer. Return (nilai, error)."""
        if not value.strip():
            return 0, None  # boleh kosong, default 0
        try:
            val = int(value.strip())
            if val < 0:
                return 0, f"{field_name} tidak boleh negatif."
            return val, None
        except ValueError:
            return 0, f"{field_name} harus berupa angka."

    @staticmethod
    def do_save(recipe_name: str, notes: str, ingredients: list,
                steps: list, portion_str: str,
                cook_time_str: str) -> tuple[dict | None, str | None]:

        err = SavedController.validate_name(recipe_name)
        if err:
            return None, err

        err = SavedController.validate_notes(notes)
        if err:
            return None, err

        portion, err = SavedController.validate_int(portion_str, "Porsi")
        if err:
            return None, err

        cook_time, err = SavedController.validate_int(cook_time_str, "Waktu masak")
        if err:
            return None, err

        recipe_id = _make_id(recipe_name + _now())
        row = save_recipe(
            recipe_id       = recipe_id,
            recipe_name     = recipe_name.strip(),
            notes           = notes.strip(),
            ingredients_all = ingredients,
            steps           = steps,
            cook_time       = cook_time,
            portion         = portion,
            source          = "Manual",
        )
        return row, None

    @staticmethod
    def do_edit(saved_id: str, recipe_name: str, notes: str,
                ingredients: list, steps: list,
                portion_str: str, cook_time_str: str) -> tuple[bool, str | None]:

        err = SavedController.validate_name(recipe_name)
        if err:
            return False, err

        err = SavedController.validate_notes(notes)
        if err:
            return False, err

        portion, err = SavedController.validate_int(portion_str, "Porsi")
        if err:
            return False, err

        cook_time, err = SavedController.validate_int(cook_time_str, "Waktu masak")
        if err:
            return False, err

        ok = update_recipe(saved_id, {
            "recipe_name":     recipe_name.strip(),
            "notes":           notes.strip(),
            "ingredients_all": ingredients,
            "steps":           steps,
            "portion":         portion,
            "cook_time":       cook_time,
        })
        return ok, None

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: format tampilan
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_portion(portion) -> str:
    """int 4 → '4 porsi', 0 atau None → ''"""
    try:
        val = int(portion)
        return f"{val} porsi" if val > 0 else ""
    except (TypeError, ValueError):
        return str(portion) if portion else ""

def _fmt_time(cook_time) -> str:
    """int 30 → '30 menit', 0 atau None → ''"""
    try:
        val = int(cook_time)
        return f"{val} menit" if val > 0 else ""
    except (TypeError, ValueError):
        return str(cook_time) if cook_time else ""

def _to_str(val) -> str:
    """int/None → str untuk pre-fill field input."""
    if val is None or val == 0:
        return ""
    return str(val)

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: field styling
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

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Edit Resep Lengkap
# ══════════════════════════════════════════════════════════════════════════════

def EditRecipeDialog(page: ft.Page, saved: dict, on_saved) -> ft.AlertDialog:
    existing_ingredients = "\n".join(saved.get("ingredients_all", []))
    existing_steps       = "\n".join(saved.get("steps", []))

    name_field = _field(
        "Nama Resep *",
        value=saved.get("recipe_name", ""),
    )
    portion_field = _field(
        "Porsi (orang)",
        value=_to_str(saved.get("portion")),
        hint="cth: 4",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    cook_time_field = _field(
        "Waktu Masak (menit)",
        value=_to_str(saved.get("cook_time")),
        hint="cth: 30",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    ingredients_field = _field(
        "Bahan-bahan (satu baris = satu bahan)",
        value=existing_ingredients,
        multiline=True, min_lines=5, max_lines=10,
        hint="cth:\n2 butir telur\n1 sdt garam\n3 sdm kecap manis",
    )
    steps_field = _field(
        "Langkah-langkah (satu baris = satu langkah)",
        value=existing_steps,
        multiline=True, min_lines=5, max_lines=10,
        hint="cth:\nCincang bawang putih\nTumis hingga harum\nSajikan",
    )
    notes_field = _field(
        "Catatan",
        value=saved.get("notes", ""),
        multiline=True, min_lines=2, max_lines=4,
        hint="Catatan pribadi kamu...",
    )
    error_text = ft.Text("", color=RED, size=11)

    def on_save(e):
        ingredients = [
            line.strip()
            for line in (ingredients_field.value or "").splitlines()
            if line.strip()
        ]
        steps = [
            line.strip()
            for line in (steps_field.value or "").splitlines()
            if line.strip()
        ]

        ok, err = SavedController.do_edit(
            saved_id      = saved["saved_id"],
            recipe_name   = name_field.value or "",
            notes         = notes_field.value or "",
            ingredients   = ingredients,
            steps         = steps,
            portion_str   = portion_field.value or "",
            cook_time_str = cook_time_field.value or "",
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

    dialog = ft.AlertDialog(
        modal   = True,
        title   = ft.Row(
            controls=[
                ft.Icon(ft.Icons.EDIT, color=ORANGE, size=20),
                ft.Text(
                    f"Edit — {saved.get('recipe_name', 'Resep')}",
                    color=TEXT, weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=8,
        ),
        bgcolor = BG2,
        content = ft.Container(
            content=ft.Column(
                controls=[
                    name_field,
                    ft.Row(controls=[portion_field, cook_time_field], spacing=10),
                    ft.Divider(color=BG4, height=1),
                    ingredients_field,
                    ft.Divider(color=BG4, height=1),
                    steps_field,
                    ft.Divider(color=BG4, height=1),
                    notes_field,
                    error_text,
                ],
                spacing=10, tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=520, height=520,
        ),
        actions=[
            ft.TextButton(
                "Batal",
                style=ft.ButtonStyle(color=TEXT3),
                on_click=on_cancel,
            ),
            ft.ElevatedButton(
                "Simpan Perubahan",
                bgcolor=ORANGE, color="#FFFFFF",
                on_click=on_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Tambah Resep Manual
# ══════════════════════════════════════════════════════════════════════════════

def AddRecipeDialog(page: ft.Page, on_saved) -> ft.AlertDialog:
    name_field = _field("Nama Resep *")
    portion_field = _field(
        "Porsi (orang)", hint="cth: 4",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    cook_time_field = _field(
        "Waktu Masak (menit)", hint="cth: 30",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    ingredients_field = _field(
        "Bahan-bahan (satu baris = satu bahan)",
        multiline=True, min_lines=4, max_lines=8,
        hint="cth:\n2 butir telur\n1 sdt garam",
    )
    steps_field = _field(
        "Langkah-langkah (satu baris = satu langkah)",
        multiline=True, min_lines=4, max_lines=8,
        hint="cth:\nCincang bawang putih\nTumis hingga harum",
    )
    notes_field  = _field(
        "Catatan (opsional)",
        multiline=True, min_lines=2, max_lines=4,
    )
    error_text = ft.Text("", color=RED, size=11)

    def on_save(e):
        ingredients = [
            line.strip()
            for line in (ingredients_field.value or "").splitlines()
            if line.strip()
        ]
        steps = [
            line.strip()
            for line in (steps_field.value or "").splitlines()
            if line.strip()
        ]
        row, err = SavedController.do_save(
            recipe_name   = name_field.value or "",
            notes         = notes_field.value or "",
            ingredients   = ingredients,
            steps         = steps,
            portion_str   = portion_field.value or "",
            cook_time_str = cook_time_field.value or "",
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
        title   = ft.Text("Tambah Resep", color=TEXT, weight=ft.FontWeight.BOLD),
        bgcolor = BG2,
        content = ft.Container(
            content=ft.Column(
                controls=[
                    name_field,
                    ft.Row(controls=[portion_field, cook_time_field], spacing=10),
                    ingredients_field,
                    steps_field,
                    notes_field,
                    error_text,
                ],
                spacing=10, tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=520, height=500,
        ),
        actions=[
            ft.TextButton("Batal", style=ft.ButtonStyle(color=TEXT3), on_click=on_cancel),
            ft.ElevatedButton("Simpan", bgcolor=ORANGE, color="#FFFFFF", on_click=on_save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Konfirmasi Hapus
# ══════════════════════════════════════════════════════════════════════════════

def ConfirmDeleteDialog(page: ft.Page, recipe_name: str,
                        on_confirmed) -> ft.AlertDialog:
    def on_yes(e):
        on_confirmed()
        dialog.open = False
        page.update()

    def on_no(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal   = True,
        title   = ft.Text("Hapus Resep?", color=RED, weight=ft.FontWeight.BOLD),
        bgcolor = BG2,
        content = ft.Text(
            f"'{recipe_name}' akan dihapus.\nTidak bisa dibatalkan.",
            color=TEXT2, size=13,
        ),
        actions=[
            ft.TextButton("Batal", style=ft.ButtonStyle(color=TEXT3), on_click=on_no),
            ft.ElevatedButton("Hapus", bgcolor=RED, color="#FFFFFF", on_click=on_yes),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# KOMPONEN: kartu resep
# ══════════════════════════════════════════════════════════════════════════════

def _recipe_card(saved: dict, on_view, on_edit, on_delete) -> ft.Container:
    recipe_name = saved.get("recipe_name", "Resep")
    image_url   = saved.get("image_url", "")
    notes       = saved.get("notes", "")
    source      = saved.get("source", "Cookpad")

    # Format porsi & waktu dari integer
    portion_text   = _fmt_portion(saved.get("portion"))
    cook_time_text = _fmt_time(saved.get("cook_time"))

    meta_parts = []
    if portion_text:
        meta_parts.append(f"👥 {portion_text}")
    if cook_time_text:
        meta_parts.append(f"⏱ {cook_time_text}")
    if source:
        meta_parts.append(source)
    meta_text = " · ".join(meta_parts) if meta_parts else "Resep tersimpan"

    return ft.Container(
        content=ft.Column(
            controls=[
                # ── Gambar ────────────────────────────────────────
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            ft.Image(
                                src=image_url,
                                width=float("inf"),
                                height=140,
                                fit="cover",
                                error_content=ft.Container(
                                    bgcolor=BG4, height=140,
                                    content=ft.Icon(
                                        ft.Icons.RESTAURANT,
                                        color=TEXT3, size=36,
                                    ),
                                    alignment=ft.Alignment(0, 0),
                                ),
                            ),
                            ft.Container(
                                height=140,
                                gradient=ft.LinearGradient(
                                    begin=ft.Alignment(0, -1),
                                    end=ft.Alignment(0, 1),
                                    colors=["transparent", "#66000000"],
                                ),
                            ),
                        ],
                        height=140,
                    ),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border_radius=ft.BorderRadius.only(top_left=10, top_right=10),
                ),

                # ── Body ──────────────────────────────────────────
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                recipe_name, color=TEXT, size=14,
                                weight=ft.FontWeight.BOLD,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                meta_text, color=TEXT2, size=12,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"📝 {notes}", color=TEXT3, size=11,
                                italic=True, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                visible=bool(notes),
                            ),
                            # Tombol aksi
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

def MyRecipesPage(page: ft.Page, navigate) -> ft.Container:

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
                ft.Text(
                    "Cari resep di Finder dan klik ♥ untuk menyimpan.",
                    color=TEXT3, size=12,
                ),
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
                        saved     = saved,
                        on_view   = _on_view,
                        on_edit   = _on_edit,
                        on_delete = _on_delete,
                    ),
                    width=320,
                )
            )

        try:
            grid.update()
            empty_state.update()
            count_badge.update()
        except Exception:
            pass  # belum di-mount, skip update

    def _on_view(saved: dict):
        navigate("detail", recipe={
            "recipe_id":   saved.get("recipe_id", ""),
            "name":        saved.get("recipe_name", ""),
            "ingredients": saved.get("ingredients_all", []),
            "steps":       saved.get("steps", []),
            "image_url":   saved.get("image_url", ""),
            "cook_time":   _fmt_time(saved.get("cook_time")),
            "portion":     _fmt_portion(saved.get("portion")),
        })

    def _on_edit(saved: dict):
        def on_saved():
            show_snack(f"✓ '{saved.get('recipe_name', 'Resep')}' berhasil diperbarui!")
            refresh(search_keyword["value"])

        dialog = EditRecipeDialog(page=page, saved=saved, on_saved=on_saved)
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_delete(saved: dict):
        def on_confirmed():
            ok = delete_recipe(saved["saved_id"])
            if ok:
                show_snack(f"'{saved['recipe_name']}' dihapus.", color=RED)
                refresh(search_keyword["value"])

        dialog = ConfirmDeleteDialog(
            page=page,
            recipe_name=saved.get("recipe_name", ""),
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
        hint_text            = "🔍 Cari resep tersimpan...",
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
                # Topbar
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
                                    padding=ft.Padding.symmetric(
                                        horizontal=14, vertical=7),
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
                # Search
                ft.Container(
                    content=search_field,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=12),
                ),
                # Grid
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