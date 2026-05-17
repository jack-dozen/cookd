import os

import flet as ft
from fadhil.my_recipes import MyRecipesPage
from rafy.theme import theme_mgr, ORANGE, WHITE
from zaky.info import InfoPage
from rafy.for_you_ui  import build_for_you_page
from rafy.snackbar    import show_snack
from rafy.home import build_home_page
import uuid
from tinydb import TinyDB, Query

from hadi.ui.topbar  import build_topbar
from hadi.ui.sidebar import build_sidebar
from hadi.ui.detail  import build_detail_page
from hadi.ui.finder  import build_finder_page


def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")


def main(page: ft.Page):

    # ══════════════════════════════════════════════════════════════════
    #  PAGE
    # ══════════════════════════════════════════════════════════════════
    page.title             = "CookD"
    page.bgcolor           = BG()
    page.padding           = 0
    page.window.width      = 1200
    page.window.height     = 720
    page.window.min_width  = 600
    page.window.min_height = 400
    page.window.resizable  = True
    page.theme_mode        = ft.ThemeMode.DARK
    page.scroll            = None
    page.fonts             = {"Font": "fonts/PlusJakartaSans-VariableFont_wght.ttf"}
    #page.text_scale_factor = 2 
    page.theme             = ft.Theme(font_family="Font")
    page.update()

    # ══════════════════════════════════════════════════════════════════
    #  NAVIGATION
    # ══════════════════════════════════════════════════════════════════
    pages: dict[str, ft.Container] = {}

    def navigate(name: str, recipe: dict = None):
        for key, container in pages.items():
            container.visible = (key == name)
        if name != "detail":
            topbar.set_recipe(None)
            topbar.set_page(name)
            topbar.update()
        if name == "detail" and recipe:
            pages["detail"].show(recipe)
        if name == "home" and "home" in pages:
            if hasattr(pages["home"], "refresh"):
                pages["home"].refresh()
        page.update()
        
    # ══════════════════════════════════════════════════════════════════
    #  FOR YOU - RAFY
    # ══════════════════════════════════════════════════════════════════
    def _on_detail_foryou(recipe):
        navigate("detail", recipe)
        topbar.update()
    def save_to_my_recipes(recipe: dict, saved: bool):
        
        db    = TinyDB("./data/base.json")
        table = db.table("my_recipes")
        q     = Query()
        if saved:
            if not table.get(q.recipe_id == recipe.get("recipe_id", "")):
                table.insert({
                    "saved_id"   : uuid.uuid4().hex[:12],
                    "recipe_id"  : recipe.get("recipe_id", ""),
                    "recipe_name": recipe.get("name", ""),
                    "notes"      : "",
                    "ingredients_all": [
                        i.get("name", "") for i in recipe.get("ingredients", [])
                    ],
                    "steps"      : [s.get("text", "") for s in recipe.get("steps", [])],
                    "source_url" : recipe.get("source_url", ""),
                    "image_url"  : recipe.get("image_url", ""),
                    "cook_time"  : recipe.get("cook_time", 0),
                    "portion"    : recipe.get("portion", 4),
                    "source"     : recipe.get("source", "Cookpad"),
                    "saved_at"   : __import__("datetime").datetime.now()
                                .strftime("%Y-%m-%d %H:%M:%S"),
                })
                show_snack(page, "Resep disimpan! ✓", "success")
            else:
                show_snack(page, "Resep sudah ada di My Recipes", "info")
        else:
            table.remove(q.recipe_id == recipe.get("recipe_id", ""))
            show_snack(page, "Resep dihapus dari My Recipes", "warning")

    # ══════════════════════════════════════════════════════════════════
    #  TOPBAR
    # ══════════════════════════════════════════════════════════════════
    topbar = build_topbar(navigate)

    # ══════════════════════════════════════════════════════════════════
    #  PAGES
    # ══════════════════════════════════════════════════════════════════
    def make_placeholder(label: str) -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor=BG(),
            visible=False,
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "Work In Progress",
                                    color=TEXT2(),
                                    font_family="Font",
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                                    "Cras condimentum, lorem nec porttitor tincidunt.",
                                    color=TEXT2(),
                                    font_family="Font",
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=ft.Padding.all(24),
                    ),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    pages["detail"]     = build_detail_page(page, navigate, topbar)
    pages["finder"]     = build_finder_page(page, show_detail_fn=pages["detail"].show)
    pages["home"] = build_home_page(
                        page=page,
                        navigate_fn=navigate,
                        on_detail=lambda r: navigate("detail", r),
                    )
    pages["my-recipes"] = MyRecipesPage(page, navigate)
    pages["info"]       = InfoPage(page)
    pages["home"].visible = True
    pages["for-you"] = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=build_for_you_page(
                        page=page,
                        on_detail=_on_detail_foryou,
                        on_save=save_to_my_recipes,
                    ),
                    padding=ft.Padding.symmetric(horizontal=24, vertical=20),
                    expand=True,
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )


    # ══════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════════════
    sidebar = build_sidebar(page, navigate, on_import_done=lambda: pages["my-recipes"].refresh())

    # ══════════════════════════════════════════════════════════════════
    #  THEME REBUILD LISTENER
    # ══════════════════════════════════════════════════════════════════
    def rebuild_on_theme_change():
        page.bgcolor = BG()
        # sidebar and topbar have their own theme_mgr listeners
        # that handle gradient + border — do NOT overwrite with bgcolor here
        for p in pages.values():
            if hasattr(p, "bgcolor"):
                p.bgcolor = BG()
        page.update()

    theme_mgr.add_listener(rebuild_on_theme_change)

    # ══════════════════════════════════════════════════════════════════
    #  ROOT
    # ══════════════════════════════════════════════════════════════════
    page.padding = ft.Padding.all(0)
    root = ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            sidebar,
            ft.Column(
                controls=[
                    topbar,
                    ft.Container(
                        expand=True,
                        content=ft.Stack(list(pages.values())),
                    ),
                ],
                spacing=0,
                expand=True,
                alignment=ft.MainAxisAlignment.START,
            ),
        ],
    )

    page.add(root)
    topbar.set_page("home")
    topbar.update()
    pages["my-recipes"].refresh()

    def window_resized(e):
        if e.width and e.width < 800 and sidebar.width == 200:
            sidebar.toggle_sidebar()
            page.update()    
            
    page.window.icon = "assets/Cookd-logo.ico"
    page.on_resize = window_resized
    page.update()


# ft.run(main, assets_dir=".")