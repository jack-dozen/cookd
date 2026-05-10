import flet as ft
from fadhil.my_recipes import MyRecipesPage
from rafy.theme import theme_mgr, ORANGE, GREEN, WHITE
from zaky.info import InfoPage

from hadi.ui.topbar  import build_topbar
from hadi.ui.sidebar import build_sidebar
from hadi.ui.detail  import build_detail_page
from hadi.ui.finder  import build_finder_page


# ─────────────────────────────────────────────────────────────────────
# COLORS (thin wrappers so every module stays in sync with the theme)
# ─────────────────────────────────────────────────────────────────────
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
    page.window.min_width  = 400
    page.window.min_height = 300
    page.window.resizable  = True
    page.theme_mode        = ft.ThemeMode.DARK
    page.scroll            = None
    page.fonts             = {"Font": "fonts/Poppins-Regular.ttf"}
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
            topbar.update()
        if name == "detail" and recipe:
            pages["detail"].show(recipe)
        page.update()

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
                                ft.Text("Work In Progress", color=TEXT2(),
                                        font_family="Font", weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                                    "Cras condimentum, lorem nec porttitor tincidunt.",
                                    color=TEXT2(), font_family="Font",
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
    # ══════════════════════════════════════════════════════════════════
    #  TOPBAR
    # ══════════════════════════════════════════════════════════════════
    topbar = build_topbar(navigate)       

    # ══════════════════════════════════════════════════════════════════
    #  PAGES
    # ══════════════════════════════════════════════════════════════════
    pages["detail"]     = build_detail_page(page, navigate, topbar)
    pages["finder"]     = build_finder_page(page, show_detail_fn=pages["detail"].show)
    pages["home"]       = make_placeholder("Home")
    pages["my-recipes"] = MyRecipesPage(page, navigate)
    pages["for-you"]    = make_placeholder("For You")
    pages["info"]       = InfoPage(page)
    pages["home"].visible = True

    # ══════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════════════
    sidebar = build_sidebar(page, navigate)

    # ══════════════════════════════════════════════════════════════════
    #  SNACKBAR
    # ══════════════════════════════════════════════════════════════════
    snack = ft.SnackBar(
        content  = ft.Text("Saved", color=GREEN),
        bgcolor  = BG3(),
        duration = 3000,
    )
    
    # ══════════════════════════════════════════════════════════════════
    #  THEME REBUILD LISTENER
    # ══════════════════════════════════════════════════════════════════
    def rebuild_on_theme_change():
        page.bgcolor    = BG()
        sidebar.bgcolor = BG2()
        topbar.bgcolor  = BG2()

        results_column = pages["finder"].results_column
        for ctrl in results_column.controls:
            if isinstance(ctrl, ft.Container):
                ctrl.bgcolor = BG3()
                ctrl.border  = ft.Border.all(1, BORDER())

        def update_colors(ctrl):
            if isinstance(ctrl, ft.Text):
                ctrl.color = TEXT()
            if hasattr(ctrl, "controls"):
                for c in ctrl.controls:
                    update_colors(c)

        update_colors(results_column)
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
            ft.VerticalDivider(width=5, color=BORDER()),
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
    pages["my-recipes"].refresh()

    def window_resized(e):
        if e.width and e.width < 800 and sidebar.width == 200:
            sidebar.toggle_sidebar()
            page.update()

    page.on_resize = window_resized
    page.update()


# ft.run(main, assets_dir=".")
