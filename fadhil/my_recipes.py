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
    - Edit catatan (EditNotesDialog)
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
# WARNA — sesuai prototype v3
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
# SAVED RECIPE MODEL — baca/tulis tabel my_recipes di base.json
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
    """Filter resep berdasarkan keyword nama."""
    all_data = get_all()
    if not keyword.strip():
        return all_data
    kw = keyword.lower()
    return [r for r in all_data if kw in r.get("recipe_name", "").lower()]

def save_recipe(recipe_id: str, recipe_name: str, notes: str = "",
                ingredients_have: list = None, ingredients_all: list = None,
                source_url: str = "", image_url: str = "",
                cook_time: str = "", portion: str = "",
                source: str = "Cookpad") -> dict | None:
    """Simpan resep. Return None kalau sudah ada."""
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
        "source_url":       source_url,
        "image_url":        image_url,
        "cook_time":        cook_time,
        "portion":          portion,
        "source":           source,
        "saved_at":         _now(),
        "last_updated":     _now(),
    }
    table.insert(row)
    return row

def update_notes(saved_id: str, notes: str) -> bool:
    table = _table()
    R     = Query()
    if not table.search(R.saved_id == saved_id):
        return False
    table.update({"notes": notes, "last_updated": _now()}, R.saved_id == saved_id)
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
    """
    Export my_recipes ke Downloads folder.
    Pakai utility dari zaky kalau tersedia, fallback ke manual.
    """
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'zaky'))
        from export_utils import export_table
        return export_table("my_recipes")
    except ImportError:
        # Fallback manual
        rows = get_all()
        downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        output_path = os.path.join(downloads, 'my_recipes.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        return output_path

def import_json(file_path: str) -> int:
    """Import dari file JSON, skip duplikat."""
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
# SAVED CONTROLLER — validasi form
# ══════════════════════════════════════════════════════════════════════════════

class SavedController:

    @staticmethod
    def validate_add(recipe_name: str) -> str | None:
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
    def do_save(recipe_name: str, notes: str, source_url: str
                ) -> tuple[dict | None, str | None]:
        err = SavedController.validate_add(recipe_name)
        if err:
            return None, err
        err = SavedController.validate_notes(notes)
        if err:
            return None, err
        recipe_id = _make_id(recipe_name + _now())
        row = save_recipe(
            recipe_id   = recipe_id,
            recipe_name = recipe_name.strip(),
            notes       = notes.strip(),
            source_url  = source_url.strip(),
            source      = "Manual",
        )
        return row, None

    @staticmethod
    def do_update_notes(saved_id: str, notes: str) -> tuple[bool, str | None]:
        err = SavedController.validate_notes(notes)
        if err:
            return False, err
        return update_notes(saved_id, notes), None

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Tambah Resep Manual
# ══════════════════════════════════════════════════════════════════════════════

def AddRecipeDialog(page: ft.Page, on_saved) -> ft.AlertDialog:
    name_field = ft.TextField(
        label="Nama Resep *", bgcolor=BG3, color=TEXT,
        label_style=ft.TextStyle(color=TEXT2),
        border_color=BORDER, focused_border_color=ORANGE,
        content_padding=ft.Padding.all(12),
    )
    notes_field = ft.TextField(
        label="Catatan (opsional)", multiline=True,
        min_lines=2, max_lines=4,
        bgcolor=BG3, color=TEXT,
        label_style=ft.TextStyle(color=TEXT2),
        border_color=BORDER, focused_border_color=ORANGE,
        content_padding=ft.Padding.all(12),
    )
    url_field = ft.TextField(
        label="URL Sumber (opsional)", bgcolor=BG3, color=TEXT,
        label_style=ft.TextStyle(color=TEXT2),
        border_color=BORDER, focused_border_color=ORANGE,
        content_padding=ft.Padding.all(12),
    )
    error_text = ft.Text("", color=RED, size=11)

    def on_save(e):
        row, err = SavedController.do_save(
            name_field.value or "", notes_field.value or "", url_field.value or ""
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
        modal=True,
        title=ft.Text("Tambah Resep", color=TEXT, weight=ft.FontWeight.BOLD),
        bgcolor=BG2,
        content=ft.Container(
            content=ft.Column(
                controls=[name_field, notes_field, url_field, error_text],
                spacing=10, tight=True,
            ),
            width=400,
        ),
        actions=[
            ft.TextButton("Batal", style=ft.ButtonStyle(color=TEXT3), on_click=on_cancel),
            ft.ElevatedButton("Simpan", bgcolor=ORANGE, color="#FFFFFF", on_click=on_save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog

# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: Edit Catatan
# ══════════════════════════════════════════════════════════════════════════════

def EditNotesDialog(page: ft.Page, saved_id: str,
                    current_notes: str, on_saved) -> ft.AlertDialog:
    notes_field = ft.TextField(
        value=current_notes,
        hint_text="Tulis catatan pribadi kamu...",
        multiline=True, min_lines=3, max_lines=6,
        bgcolor=BG3, color=TEXT,
        hint_style=ft.TextStyle(color=TEXT3),
        border_color=BORDER, focused_border_color=ORANGE,
        content_padding=ft.Padding.all(12),
    )
    error_text = ft.Text("", color=RED, size=11)

    def on_save(e):
        ok, err = SavedController.do_update_notes(saved_id, notes_field.value or "")
        if err:
            error_text.value = err
            error_text.update()
            return
        dialog.open = False
        page.update()
        if ok:
            on_saved(notes_field.value.strip())

    def on_cancel(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Catatan", color=TEXT, weight=ft.FontWeight.BOLD),
        bgcolor=BG2,
        content=ft.Container(
            content=ft.Column(
                controls=[notes_field, error_text], spacing=8, tight=True,
            ),
            width=400,
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
        modal=True,
        title=ft.Text("Hapus Resep?", color=RED, weight=ft.FontWeight.BOLD),
        bgcolor=BG2,
        content=ft.Text(
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
# KOMPONEN: kartu resep (grid 2 kolom, sesuai prototype)
# ══════════════════════════════════════════════════════════════════════════════

def _recipe_card(saved: dict, on_view, on_edit, on_delete) -> ft.Container:
    """
    Kartu resep sesuai prototype:
    - Gambar di atas (140px)
    - Nama + meta di bawah
    - 3 tombol: Lihat | ✏️ | 🗑
    """
    recipe_name = saved.get("recipe_name", "Resep")
    portion     = saved.get("portion", "")
    cook_time   = saved.get("cook_time", "")
    source      = saved.get("source", "Cookpad")
    image_url   = saved.get("image_url", "")

    # Meta text: porsi + waktu + sumber
    meta_parts = []
    if portion:
        meta_parts.append(f"👥 {portion}")
    if cook_time:
        meta_parts.append(f"⏱ {cook_time}")
    if source:
        meta_parts.append(source)
    meta_text = " · ".join(meta_parts) if meta_parts else "Resep tersimpan"

    return ft.Container(
        content=ft.Column(
            controls=[
                # ── Gambar ─────────────────────────────────────────
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            ft.Image(
                                src=image_url,
                                width=float("inf"),
                                height=140,
                                fit="cover",
                                error_content=ft.Container(
                                    bgcolor=BG4,
                                    height=140,
                                    content=ft.Icon(
                                        ft.Icons.RESTAURANT,
                                        color=TEXT3, size=36,
                                    ),
                                    alignment=ft.Alignment(0, 0),
                                ),
                            ),
                            # Overlay gelap di bawah gambar
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
                    border_radius=ft.BorderRadius.only(
                        top_left=10, top_right=10,
                    ),
                ),

                # ── Body ───────────────────────────────────────────
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                recipe_name,
                                color=TEXT,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                meta_text,
                                color=TEXT2,
                                size=12,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            # ── Footer: tombol aksi ────────────────
                            ft.Row(
                                controls=[
                                    # Tombol Lihat
                                    ft.ElevatedButton(
                                        "Lihat",
                                        style=ft.ButtonStyle(
                                            color=ORANGE,
                                            bgcolor="transparent",
                                            side=ft.BorderSide(1.5, ORANGE),
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                            padding=ft.Padding.symmetric(
                                                horizontal=10, vertical=5
                                            ),
                                        ),
                                        on_click=lambda e: on_view(saved),
                                    ),
                                    ft.Container(expand=True),
                                    # Tombol Edit
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_color=TEXT2,
                                        icon_size=18,
                                        tooltip="Edit Catatan",
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                            side=ft.BorderSide(1.5, BG4),
                                        ),
                                        on_click=lambda e: on_edit(saved),
                                    ),
                                    # Tombol Hapus
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=RED,
                                        icon_size=18,
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
                        spacing=6,
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
    """
    Halaman My Recipes sesuai prototype v3.
    Grid 2 kolom, search bar, tombol + Tambah.
    """

    # ── State ─────────────────────────────────────────────────────────
    search_keyword = {"value": ""}

    # ── UI Refs ───────────────────────────────────────────────────────
    grid = ft.Row(
        wrap=True,
        spacing=14,
        run_spacing=14,
        controls=[],
    )

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
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.all(60),
        visible=False,
    )

    # ── Snackbar ──────────────────────────────────────────────────────
    def show_snack(msg: str, color=GREEN):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=color),
            bgcolor=BG2, duration=3000,
        )
        page.snack_bar.open = True
        page.update()

    # ── Render grid ───────────────────────────────────────────────────
    def refresh(keyword: str = ""):
        search_keyword["value"] = keyword
        saved_list = search_recipes(keyword)

        # Update badge count
        all_count = len(get_all())
        count_badge.content.value = f"Tersimpan: {all_count}"

        grid.controls.clear()
        empty_state.visible = len(saved_list) == 0

        for saved in saved_list:
            card = _recipe_card(
                saved     = saved,
                on_view   = _on_view,
                on_edit   = _on_edit,
                on_delete = _on_delete,
            )
            # Setiap kartu lebar ~50% minus spacing
            grid.controls.append(
                ft.Container(
                    content=card,
                    width=320,
                )
            )

        grid.update()
        empty_state.update()
        count_badge.update()

    # ── Handler: lihat detail ─────────────────────────────────────────
    def _on_view(saved: dict):
        navigate("detail", recipe={
            "recipe_id":   saved.get("recipe_id", ""),
            "name":        saved.get("recipe_name", ""),
            "ingredients": saved.get("ingredients_all", []),
            "steps":       [],
            "image_url":   saved.get("image_url", ""),
            "cook_time":   saved.get("cook_time", ""),
            "portion":     saved.get("portion", ""),
            "source_url":  saved.get("source_url", ""),
        })

    # ── Handler: edit catatan ─────────────────────────────────────────
    def _on_edit(saved: dict):
        def on_saved(new_notes):
            show_snack("✓ Catatan diperbarui!")
            refresh(search_keyword["value"])

        dialog = EditNotesDialog(
            page=page, saved_id=saved["saved_id"],
            current_notes=saved.get("notes", ""), on_saved=on_saved,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ── Handler: hapus ────────────────────────────────────────────────
    def _on_delete(saved: dict):
        def on_confirmed():
            ok = delete_recipe(saved["saved_id"])
            if ok:
                show_snack(f"'{saved['recipe_name']}' dihapus.", color=RED)
                refresh(search_keyword["value"])

        dialog = ConfirmDeleteDialog(
            page=page, recipe_name=saved.get("recipe_name", ""),
            on_confirmed=on_confirmed,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ── Handler: tambah manual ────────────────────────────────────────
    def _on_add(e):
        def on_saved(row):
            show_snack(f"✓ '{row['recipe_name']}' ditambahkan!")
            refresh(search_keyword["value"])

        dialog = AddRecipeDialog(page=page, on_saved=on_saved)
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ── Handler: export ───────────────────────────────────────────────
    def _on_export(e):
        try:
            path = export_json()
            show_snack(f"✓ Diekspor ke Downloads/my_recipes.json")
        except Exception as ex:
            show_snack(f"Export gagal: {ex}", color=RED)

    # ── Search field ──────────────────────────────────────────────────
    search_field = ft.TextField(
        hint_text            = "🔍 Cari resep tersimpan...",
        bgcolor              = BG3,
        color                = TEXT,
        hint_style           = ft.TextStyle(color=TEXT3),
        border_color         = BG4,
        focused_border_color = ORANGE,
        border_radius        = ft.BorderRadius.all(24),
        content_padding      = ft.Padding.symmetric(horizontal=16, vertical=10),
        expand               = True,
        on_change            = lambda e: refresh(e.control.value),
    )

    # ── Layout ────────────────────────────────────────────────────────
    page_content = ft.Container(
        expand=True, bgcolor=BG, visible=False,
        content=ft.Column(
            controls=[
                # ── Topbar ────────────────────────────────────────
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

                # ── Search bar ────────────────────────────────────
                ft.Container(
                    content=search_field,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=12),
                ),

                # ── Grid resep ────────────────────────────────────
                ft.Container(
                    content=ft.Column(
                        controls=[
                            grid,
                            empty_state,
                        ],
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

    # Expose refresh
    page_content.refresh = refresh

    return page_content