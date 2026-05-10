import asyncio
import flet as ft
import flet_lottie as ftl
from hadi import CookpadScraper
from rafy.theme import theme_mgr, ORANGE, GREEN, AMBER, WHITE


def BG():     return theme_mgr.get("BG")
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


COOKING_STAGES = [
    ("Preparing ingredients...",    "Fetching page"),
    ("Cracking the recipe open...", "Parsing HTML"),
    ("Mixing the instructions...",  "Extracting steps"),
    ("Gathering ingredients...",    "Building card"),
    ("Sliding into the oven...",    "Almost done"),
    ("Recipe served! 🍽",           "Loaded"),
]


def build_finder_page(page: ft.Page, show_detail_fn) -> ft.Container:
    """
    Returns the Finder page container.
    show_detail_fn(recipe) navigates to and populates the detail page.
    The returned container also exposes:
    container.results_column  — for theme-rebuild access in gui.py
    """

    loader_label = ft.Text(COOKING_STAGES[0][0], color=ORANGE, size=14, italic=True)
    loader_sub   = ft.Text(COOKING_STAGES[0][1], color=TEXT2(), size=11)
    loader_ring  = ftl.Lottie(
        src="https://lottie.host/7748923e-58e6-4db0-bff7-7454e10aa489/L8lGN5kMvc.json",
        width=100, height=100, repeat=True, visible=True,
        scale=ft.Scale(scale=1.2),
    )
    loader_dots = [
        ft.Container(width=8, height=8, border_radius=ft.BorderRadius.all(4),
                    bgcolor=BG3(), border=ft.Border.all(1, BORDER()))
        for _ in range(6)
    ]

    sticky_loader = ft.Container(
        visible=False,
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        padding=ft.Padding.symmetric(horizontal=24, vertical=15),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=loader_ring, width=60, height=60,
                    bgcolor=BG3(), border_radius=ft.BorderRadius.all(22),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(controls=[loader_label, loader_sub], spacing=2, expand=True),
                ft.Column(
                    controls=[ft.Row(controls=loader_dots, spacing=6, tight=True)],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=30,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def _set_loading_stage(stage: int):
        if stage < 0:
            sticky_loader.visible = False
            page.update()
            return
        sticky_loader.visible = True
        s = COOKING_STAGES[min(stage, len(COOKING_STAGES) - 1)]
        loader_label.value  = s[0]
        loader_sub.value    = s[1]
        loader_ring.visible = stage < 5
        loader_ring.play    = stage < 5
        for i, dot in enumerate(loader_dots):
            if i < stage:
                dot.bgcolor = ORANGE
                dot.border  = ft.Border.all(1, ORANGE)
            elif i == stage:
                dot.bgcolor = "transparent"
                dot.border  = ft.Border.all(2, ORANGE)
            else:
                dot.bgcolor = BG3()
                dot.border  = ft.Border.all(1, BORDER())
        page.update()

    results_column = ft.Column(
        controls=[],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def _build_card(r: dict) -> ft.Container:
        score     = r.get("match_score", 0)
        score_pct = f"{round(score * 100)}% cocok"
        bg_score, fg_score = (
            ("#1B3D28", GREEN)    if score >= 0.8 else
            ("#3D2E0A", AMBER)   if score >= 0.5 else
            ("#3D1A1A", "#C0392B")
        )

        def on_card_click(e):
            card.bgcolor = BG3()
            card.border  = ft.Border.all(1, BORDER())
            card.update()
            show_detail_fn(r)

        card = ft.Container(
            data=score,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=90, height=90,
                        border_radius=ft.BorderRadius.all(8),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=ft.Image(
                            src=r.get("image_url", ""),
                            width=90, height=90, fit="cover",
                        ),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(r["name"], color=TEXT(), weight=ft.FontWeight.BOLD, size=15),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=TEXT2(), size=13),
                                ft.Text(r.get("portion", ""),    color=TEXT2(), size=12),
                                ft.Text("·",                     color=TEXT3(), size=12),
                                ft.Icon(ft.Icons.TIMER_OUTLINED, color=TEXT2(), size=13),
                                ft.Text(r.get("cook_time", ""),  color=TEXT2(), size=12),
                            ], spacing=4),
                            ft.Container(
                                content=ft.Text(r.get("source", "Cookpad"), color=TEXT3(), size=11),
                                bgcolor=BG4(), border_radius=4,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Text(score_pct, color=fg_score, size=12,
                                                weight=ft.FontWeight.BOLD),
                                bgcolor=bg_score,
                                border_radius=ft.BorderRadius.all(20),
                                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            ),
                            ft.OutlinedButton(
                                "Lihat",
                                style=ft.ButtonStyle(
                                    color=ORANGE,
                                    side=ft.BorderSide(1, ORANGE),
                                    mouse_cursor=ft.MouseCursor.CLICK,
                                ),
                                on_click=lambda e, rec=r: show_detail_fn(rec),
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=BG3(),
            border_radius=ft.BorderRadius.all(15),
            padding=ft.Padding.symmetric(horizontal=20, vertical=15),
            border=ft.Border.all(1, BORDER()),
            on_hover=lambda e: (
                setattr(e.control, "bgcolor", "#42190d" if e.data else BG3()),
                setattr(e.control, "border", ft.Border.all(1, ORANGE if e.data else BORDER())),
                e.control.update(),
            ),
            on_click=on_card_click,
        )
        return card

    def on_search(e):
        async def run_search():
            results_column.controls.clear()
            ingredients = search_field.value.strip()
            if not ingredients:
                return

            _set_loading_stage(0)
            page.update()

            user_ingredients = [k.strip() for k in ingredients.split(",") if k.strip()]
            loop = asyncio.get_event_loop()

            def on_recipe_found(recipe):
                async def update_ui():
                    n = len(results_column.controls)
                    _set_loading_stage(min(1 + n, 4))
                    new_card  = _build_card(recipe)
                    insert_at = len(results_column.controls)
                    for i, ctrl in enumerate(results_column.controls):
                        if recipe["match_score"] > (ctrl.data or 0):
                            insert_at = i
                            break
                    results_column.controls.insert(insert_at, new_card)
                    page.update()
                asyncio.run_coroutine_threadsafe(update_ui(), loop)

            def run():
                CookpadScraper.main(user_ingredients, on_recipe_found=on_recipe_found)
            
            await asyncio.get_event_loop().run_in_executor(None, run)
            _set_loading_stage(-1)
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

    container = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(controls=[
                        search_field,
                        ft.ElevatedButton(
                            "Cari", bgcolor=ORANGE, color=WHITE,
                            on_click=on_search,
                            style=ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK),
                        ),
                    ]),
                    padding=ft.Padding.all(20),
                ),
                sticky_loader,
                ft.Container(
                    content=results_column,
                    padding=ft.Padding.symmetric(horizontal=20),
                    margin=ft.Margin.only(top=12),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
    )

    container.results_column = results_column  # exposed for gui.py theme rebuild
    return container
