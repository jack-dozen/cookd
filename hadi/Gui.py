import flet as ft
import json
import asyncio
from hadi import CookpadScraper
import subprocess
from fadhil.my_recipes import MyRecipesPage
from rafy.theme import theme_mgr, ORANGE, GREEN, AMBER, BLUE, WHITE, BLACK
from rafy.sidebar import build_sidebar_extras

# ─────────────────────────────────────────────────────────────────────
# COLORS — live dari theme_mgr
# ─────────────────────────────────────────────────────────────────────
def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


def main(page: ft.Page):

    # ══════════════════════════════════════════════════════════════════
    #  PAGE
    # ══════════════════════════════════════════════════════════════════
    page.title             = "CookD"
    page.bgcolor           = BG()
    page.padding           = 0
    page.window.width      = 720
    page.window.height     = 1200
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

    def navigate(name: str):
        for key, container in pages.items():
            container.visible = (key == name)
        page.update()

    # ══════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════════════
    state = {"active_index": 1}

    def build_nav_item(icon, label, index):
        is_active = state["active_index"] == index
        icon_obj = ft.Icon(icon, color=ORANGE if is_active else TEXT2(), size=24)
        text_obj = ft.Text(value=label, color=ORANGE if is_active else TEXT2(), size=15, weight="w500")

        def on_hover(e):
            if state["active_index"] == index:
                return
            is_hovered = e.data
            icon_obj.color    = ORANGE if is_hovered else TEXT2()
            text_obj.color    = ORANGE if is_hovered else TEXT2()
            e.control.bgcolor = BG3() if is_hovered else ft.Colors.TRANSPARENT
            icon_obj.update()
            text_obj.update()
            e.control.update()

        def on_click(e):
            state["active_index"] = index
            update_highlights()
            navigate(["home", "finder", "my-recipes", "for-you", "info"][index - 1])

        return ft.Container(
            content=ft.Row(controls=[icon_obj, text_obj], spacing=15),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=10,
            bgcolor=BG3() if is_active else ft.Colors.TRANSPARENT,
            on_hover=on_hover,
            on_click=on_click,
        )

    def update_highlights():
        for i in range(2, len(sidebar.content.controls)):
            item = sidebar.content.controls[i]
            if isinstance(item, ft.Container) and isinstance(item.content, ft.Row):
                btn_index = i - 1
                is_active = state["active_index"] == btn_index
                item.bgcolor                   = BG3() if is_active else ft.Colors.TRANSPARENT
                item.content.controls[0].color = ORANGE if is_active else TEXT2()
                item.content.controls[1].color = ORANGE if is_active else TEXT2()
        sidebar.update()

    def toggle_sidebar(e):
        is_collapsing = sidebar.width == 200
        sidebar.width = 60 if is_collapsing else 200
        for item in sidebar.content.controls:
            if isinstance(item, ft.Container) and isinstance(item.content, ft.Row):
                item.content.controls[1].visible = not is_collapsing
        page.update()

    sidebar = ft.Container(
        width=200,
        bgcolor=BG2(),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.MENU, color=TEXT2()),
                    padding=15,
                    border_radius=10,
                    bgcolor=ft.Colors.TRANSPARENT,
                    on_hover=lambda e: (
                        setattr(e.control, "bgcolor", BG3() if e.data else ft.Colors.TRANSPARENT),
                        e.control.update()
                    ),
                    on_click=toggle_sidebar,
                ),
                ft.Divider(height=1, color="transparent"),
                build_nav_item(ft.Icons.HOME_OUTLINED,   "Home",       1),
                build_nav_item(ft.Icons.SEARCH_OUTLINED, "Finder",     2),
                build_nav_item(ft.Icons.BOOK_OUTLINED,   "My Recipes", 3),
                build_nav_item(ft.Icons.STAR_OUTLINE,    "For You",    4),
                build_nav_item(ft.Icons.INFO_OUTLINE,    "Info",       5),
                *build_sidebar_extras(page),
            ],
            spacing=5,
            expand=True,
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    #  SNACKBAR
    # ══════════════════════════════════════════════════════════════════
    snack = ft.SnackBar(
        content  = ft.Text("Saved", color=GREEN),
        bgcolor  = BG3(),
        duration = 3000,
    )

    # ══════════════════════════════════════════════════════════════════
    #  PAGES
    # ══════════════════════════════════════════════════════════════════
    def make_page(label: str) -> ft.Container:
        return ft.Container(
            expand  = True,
            bgcolor = BG(),
            visible = False,
            content = ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Work In Progress", color=TEXT2(), font_family="Font", weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                                    "Cras condimentum, lorem nec porttitor tincidunt, felis lorem egestas odio.",
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

    pages["home"]       = make_page("Home")
    pages["my-recipes"] = MyRecipesPage(page, navigate)
    pages["for-you"]    = make_page("For You")
    pages["info"]       = make_page("Info")
    pages["home"].visible = True

    # ══════════════════════════════════════════════════════════════════
    #  DETAIL PAGE
    # ══════════════════════════════════════════════════════════════════
    detail_content = ft.Column(
        controls=[],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    pages["detail"] = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        content=ft.Column(
            controls=[
                ft.TextButton(
                    "← Back",
                    on_click=lambda e: navigate("finder"),
                    style=ft.ButtonStyle(color=ORANGE),
                ),
                detail_content,
            ],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    def show_detail(recipe: dict):
        detail_content.controls.clear()

        # ── Hero ──
        detail_content.controls.append(
            ft.Container(
                height=500,
                content=ft.Stack(
                    controls=[
                        ft.Image(
                            src=recipe.get("image_url", ""),
                            width=float("inf"),
                            height=500,
                            fit="cover",
                        ),
                        ft.Container(
                            width=float("inf"),
                            height=500,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment(0, 1),
                                end=ft.Alignment(0, -1),
                                colors=["#EE000000", "#44000000"],
                            ),
                        ),
                        ft.Container(
                            bottom=0, left=0, right=0,
                            padding=ft.padding.symmetric(horizontal=30, vertical=20),
                            content=ft.Column(
                                controls=[
                                    ft.Text(recipe.get("name", ""), size=28, weight=ft.FontWeight.BOLD, color=WHITE),
                                    ft.Text(f"oleh {recipe.get('author', '')}", size=13, color=TEXT2()),
                                ],
                                spacing=4,
                            ),
                        ),
                    ],
                ),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            )
        )

        # ── Meta pills ──
        def meta_pill(icon, text):
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(icon, color=ORANGE, size=16),
                        ft.Text(text, color=TEXT(), size=13),
                    ],
                    spacing=6,
                    tight=True,
                ),
                bgcolor=BG3(),
                border=ft.Border.all(1, ORANGE),
                border_radius=ft.BorderRadius.all(20),
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
            )

        detail_content.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        meta_pill(ft.Icons.PEOPLE_OUTLINE, recipe.get("portion", "")),
                        meta_pill(ft.Icons.TIMER_OUTLINED, recipe.get("cook_time", "")),
                        ft.Row(expand=True),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(horizontal=30, vertical=16),
                border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
            )
        )

        # ── Ingredients ──
        def ingredient_card(ingredients: list) -> ft.Container:
            items = []
            for ing in ingredients:
                name = ing.get("name", ing) if isinstance(ing, dict) else ing
                items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(width=10, height=10, bgcolor=ORANGE, border_radius=ft.BorderRadius.all(5)),
                                ft.Text(name, color=TEXT(), weight=ft.FontWeight.BOLD, size=14, expand=True),
                            ],
                            spacing=12,
                        ),
                        padding=ft.padding.symmetric(horizontal=5, vertical=12),
                        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                    )
                )
            return ft.Container(
                content=ft.Column(controls=items, spacing=0),
                bgcolor=BG3(),
                border_radius=ft.BorderRadius.all(10),
            )

        # ── Steps ──
        def steps_card(steps: list) -> ft.Container:
            items = []
            for i, step in enumerate(steps, start=1):
                text = step.get("text", step) if isinstance(step, dict) else step
                items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(str(i), color=WHITE, size=13, weight=ft.FontWeight.BOLD),
                                    width=32, height=32,
                                    bgcolor=ORANGE,
                                    border_radius=ft.BorderRadius.all(16),
                                    alignment=ft.Alignment(0, 0),
                                ),
                                ft.Text(text, color=TEXT(), size=14, expand=True),
                            ],
                            spacing=16,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=14),
                        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                    )
                )
            return ft.Container(
                content=ft.Column(controls=items, spacing=0),
                bgcolor=BG3(),
                border_radius=ft.BorderRadius.all(10),
            )

        detail_content.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text("Bahan-bahan", size=22, weight=ft.FontWeight.BOLD, color=TEXT()),
                                ingredient_card(recipe.get("ingredients", [])),
                            ],
                            spacing=16,
                            expand=1,
                        ),
                        ft.Container(width=30),
                        ft.Column(
                            controls=[
                                ft.Text("Cara Membuat", size=22, weight=ft.FontWeight.BOLD, color=TEXT()),
                                steps_card(recipe.get("steps", [])),
                            ],
                            spacing=16,
                            expand=2,
                        ),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    expand=True,
                ),
                padding=ft.padding.symmetric(horizontal=30, vertical=24),
                expand=True,
            )
        )

        navigate("detail")
        page.update()

    # ══════════════════════════════════════════════════════════════════
    #  FINDER PAGE
    # ══════════════════════════════════════════════════════════════════
    results_column = ft.Column(
        controls=[],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def on_search(e):
        async def run_search():
            ingredients = search_field.value.strip()
            if not ingredients:
                return

            results_column.controls.clear()
            results_column.controls.append(ft.ProgressRing(color=ORANGE))
            page.update()

            process = subprocess.Popen(
                ["python", "./hadi/CookpadScraper.py", ingredients],
                cwd=".",
            )
            await asyncio.get_event_loop().run_in_executor(None, process.wait)

            try:
                with open(CookpadScraper.OUTPUT_FILE, "r", encoding="utf-8") as f:
                    results = json.load(f)
            except Exception as ex:
                results_column.controls.clear()
                results_column.controls.append(ft.Text(f"Error: {ex}", color="red"))
                page.update()
                return

            results_column.controls.clear()
            for r in results:
                def make_click(recipe):
                    return lambda e: show_detail(recipe)

                results_column.controls.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(r["name"], color=TEXT(), weight=ft.FontWeight.BOLD, size=15),
                                ft.Text(r.get("portion", ""),   color=TEXT2(), size=12),
                                ft.Text(r.get("author", ""),    color=TEXT2(), size=12),
                                ft.Text(r.get("cook_time", ""), color=TEXT2(), size=12),
                                ft.Image(
                                    src=r["image_url"],
                                    width=float("inf"),
                                    height=150,
                                    fit="cover",
                                    border_radius=ft.BorderRadius.all(8),
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=BG3(),
                        border_radius=10,
                        padding=ft.padding.all(14),
                        border=ft.Border.all(1, BORDER()),
                        ink=True,
                        on_click=make_click(r),
                    )
                )
            page.update()

        page.run_task(run_search)

    search_field = ft.TextField(
        hint_text="cth: bawang putih, tomat...",
        bgcolor=BG3(),
        color=TEXT(),
        focused_border_color=ORANGE,
        border_color=BORDER(),
        expand=True,
        on_submit=on_search,
    )

    pages["finder"] = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(controls=[
                        search_field,
                        ft.ElevatedButton("Cari", bgcolor=ORANGE, color=WHITE, on_click=on_search),
                    ]),
                    padding=ft.padding.all(20),
                ),
                results_column,
            ],
            spacing=0,
            expand=True,
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    #  TOPBAR
    # ══════════════════════════════════════════════════════════════════
    topbar = ft.Container(
        width=float("inf"),
        content=ft.Column(
            controls=[
                ft.Text("CookD", size=20, color=TEXT(), weight=ft.FontWeight.BOLD, font_family="Font"),
                ft.Text("Cari resep dari bahan yang kamu punya", size=10, opacity=0.5, color=TEXT()),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=BG2(),
        padding=ft.padding.symmetric(horizontal=40, vertical=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
    )

    # ══════════════════════════════════════════════════════════════════
    #  THEME REBUILD LISTENER
    # ══════════════════════════════════════════════════════════════════
    def rebuild_on_theme_change():
        page.bgcolor    = BG()
        sidebar.bgcolor = BG2()
        topbar.bgcolor  = BG2()
        topbar.border   = ft.Border.only(bottom=ft.BorderSide(1, BORDER()))
        for ctrl in topbar.content.controls:
            if isinstance(ctrl, ft.Text):
                ctrl.color = TEXT()

        # rebuild static pages so text colors refresh
        stack = root.controls[2].controls[1].content  # the ft.Stack holding pages
        for key in ["home", "for-you", "info"]:
            was_visible = pages[key].visible
            new_page = make_page(key)
            new_page.visible = was_visible
            idx = stack.controls.index(pages[key])
            stack.controls[idx] = new_page
            pages[key] = new_page

        for p in pages.values():
            p.bgcolor = BG()

        update_highlights()
        page.update()

    theme_mgr.add_listener(rebuild_on_theme_change)

    # ══════════════════════════════════════════════════════════════════
    #  ROOT
    # ══════════════════════════════════════════════════════════════════
    page.padding = ft.padding.all(0)
    root = ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            sidebar,
            ft.VerticalDivider(width=1, color=BORDER()),
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
            toggle_sidebar(e)
            page.update()

    page.on_resize = window_resized
    page.update()


# ft.run(main, assets_dir=".")