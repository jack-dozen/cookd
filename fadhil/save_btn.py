"""
fadhil/save_btn.py — Tombol simpan resep ke My Recipes
Dipanggil dari finder.py atau for_you_ui.py

Cara pakai:
    from fadhil.save_btn import build_save_btn

    btn = build_save_btn(page, recipe)
    # taruh btn di dalam kartu
"""

import flet as ft
from fadhil.my_recipes import save_recipe, is_saved
from rafy.snackbar import show_snack

ORANGE = "#E8440A"
BG3    = "#2E2E2E"
BG4    = "#363636"
TEXT2  = "#B0B0AB"


def build_save_btn(page: ft.Page, recipe: dict, on_saved=None) -> ft.Container:
    already_saved = is_saved(recipe.get("recipe_id", ""))
    state = {"saved": already_saved}

    icon = ft.Icon(
        ft.Icons.FAVORITE if already_saved else ft.Icons.FAVORITE_BORDER,
        color="#E74C3C" if already_saved else TEXT2,
        size=12,
    )

    btn = ft.Container(
        content=icon,
        width=36,
        height=34,
        border=ft.Border.all(1.5, "#E74C3C" if already_saved else TEXT2),
        border_radius=ft.BorderRadius.all(8),
        alignment=ft.Alignment(0, 0),
        ink=True,
    )
    def on_click(e):
        if state["saved"]:
            # Unlike
            from tinydb import TinyDB, Query
            import os
            DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')
            db = TinyDB(DB_PATH)
            R  = Query()
            recipe_id = recipe.get("recipe_id", "")
            db.table("my_recipes").remove(R.recipe_id == recipe_id)
            state["saved"] = False
            icon.name      = ft.Icons.FAVORITE_BORDER
            icon.color     = TEXT2
            btn.border     = ft.Border.all(1.5, TEXT2)
        else:
            # Save
            row = save_recipe(
                recipe_id       = recipe.get("recipe_id", ""),
                recipe_name     = recipe.get("name", ""),
                ingredients_all = recipe.get("ingredients", []),
                steps           = recipe.get("steps", []),
                image_data      = recipe.get("image_url", ""),
                cook_time       = recipe.get("cook_time", 0),
                portion         = recipe.get("portion", 0),
                source          = recipe.get("source", "Cookpad"),
            )
            if row:
                state["saved"] = True
                icon.name      = ft.Icons.FAVORITE
                icon.color     = "#E74C3C"
                btn.border     = ft.Border.all(1.5, "#E74C3C")

        icon.update()
        btn.update()
        page.update()
        if on_saved:
            on_saved(recipe)
            
    btn.on_click = on_click
    return btn