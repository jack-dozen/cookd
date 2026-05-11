import asyncio
import flet as ft
import flet_lottie as ftl
from hadi import CookpadScraper
from rafy.theme import theme_mgr, ORANGE, ORANGE_GLOW, GREEN, AMBER, WHITE


def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
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
    loader_label = ft.Text(COOKING_STAGES[0][0], color=ORANGE, size=14, italic=True)
    loader_sub   = ft.Text(COOKING_STAGES[0][1], color=TEXT2(), size=11)
    loader_ring  = ftl.Lottie(
        src="https://lottie.host/7748923e-58e6-4db0-bff7-7454e10aa489/L8lGN5kMvc.json",
        width=100, height=100, repeat=True, visible=True,
        scale=ft.Scale(scale=1.2),
    )
    loader_dots = [
        ft.Container(
            width=8, height=8,
            border_radius=ft.BorderRadius.all(4),
            bgcolor=BG3(),
            border=ft.Border.all(1, BORDER()),
        )
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

    # ── Empty state ──────────────────────────────────────────────────
    empty_state = ft.Container(
        visible=True,
        expand=True,
        content=ft.Column(
            controls=[
                ft.Text("🍳", size=72),
                ft.Container(height=16),
                ft.Text(
                    "Masukkan bahan yang kamu punya",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT(),
                    font_family="Font",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                ft.Text(
                    "CookD akan carikan resep terbaik\nsesuai bahan di dapurmu 🥘",
                    size=14,
                    color=TEXT2(),
                    font_family="Font",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=24),
                ft.Row(
                    controls=[
                        ft.Text("🧄", size=28),
                        ft.Text("🍅", size=22),
                        ft.Text("🥚", size=26),
                        ft.Text("🧅", size=20),
                        ft.Text("🌶️", size=24),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        ),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1.0,
    )

    results_column = ft.Column(
        controls=[],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        visible=False,
    )

    def _card_gradient():
        return ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[BG3(), BG2()],
        )

    def _not_found_card() -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("😔", size=40),
                    ft.Text(
                        "Resep tidak ditemukan",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT(),
                        font_family="Font",
                    ),
                    ft.Text(
                        "Coba bahan lain atau tambah lebih banyak bahan",
                        size=13,
                        color=TEXT2(),
                        font_family="Font",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            gradient=_card_gradient(),
            border_radius=ft.BorderRadius.all(16),
            border=ft.Border.all(1, BORDER()),
            padding=ft.Padding.symmetric(horizontal=24, vertical=32),
            alignment=ft.Alignment(0, 0),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN),
            animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            opacity=1.0,
            offset=ft.Offset(0, 0),
        )

    def _build_card(r: dict) -> ft.Container:
        score     = r.get("match_score", 0)
        score_pct = f"Match {round(score * 100)}%"
        bg_score, fg_score = (
            ("#1B3D28", GREEN)     if score >= 0.8 else
            ("#3D2E0A", AMBER)    if score >= 0.5 else
            ("#3D1A1A", "#ef4444")
        )

        thumb = ft.Container(
            width=96, height=96,
            border_radius=ft.BorderRadius.all(12),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Image(
                src=r.get("image_url", ""),
                width=96, height=96, fit="cover",
            ),
        )

        async def on_card_click(e):
            card.scale   = ft.Scale(scale=0.97)
            card.bgcolor = BG3()
            card.border  = ft.Border.all(1, BORDER())
            card.update()
            await asyncio.sleep(0.1)
            card.scale = ft.Scale(scale=1.0)
            card.update()
            show_detail_fn(r)

        card = ft.Container(
            data=score,
            scale=ft.Scale(scale=1.0),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN),
            animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            opacity=0.0,
            offset=ft.Offset(0, 0.1),
            gradient=_card_gradient(),
            content=ft.Row(
                controls=[
                    thumb,
                    ft.Column(
                        controls=[
                            ft.Text(
                                r["name"],
                                color=TEXT(),
                                weight=ft.FontWeight.BOLD,
                                size=16,
                                font_family="Font",
                            ),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=TEXT2(), size=14),
                                    ft.Text(r.get("portion", ""),    color=TEXT2(), size=13),
                                    ft.Text("·",                     color=TEXT3(), size=13),
                                    ft.Icon(ft.Icons.TIMER_OUTLINED, color=TEXT2(), size=14),
                                    ft.Text(r.get("cook_time", ""),  color=TEXT2(), size=13),
                                ],
                                spacing=4,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    r.get("source", "Cookpad"),
                                    color=TEXT3(), size=12,
                                ),
                                bgcolor=BG4(),
                                border_radius=ft.BorderRadius.all(6),
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ],
                        spacing=7,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Text(
                                    score_pct,
                                    color=fg_score,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                bgcolor=bg_score,
                                border_radius=ft.BorderRadius.all(20),
                                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            ),
                            ft.OutlinedButton(
                                "Lihat →",
                                style=ft.ButtonStyle(
                                    color=ORANGE,
                                    side=ft.BorderSide(1, ORANGE),
                                    mouse_cursor=ft.MouseCursor.CLICK,
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                ),
                                on_click=lambda e, rec=r: show_detail_fn(rec),
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            border_radius=ft.BorderRadius.all(16),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            border=ft.Border.all(1, BORDER()),
            on_hover=lambda e: (
                setattr(e.control, "gradient",
                        ft.LinearGradient(
                            begin=ft.Alignment(-1, -1),
                            end=ft.Alignment(1, 1),
                            colors=["#42190d", BG2()],
                        ) if e.data else _card_gradient()),
                setattr(e.control, "border",
                        ft.Border.all(1, ORANGE if e.data else BORDER())),
                e.control.update(),
            ),
            on_click=on_card_click,
        )
        return card

    async def _animate_card_in(card: ft.Container):
        await asyncio.sleep(0.05)
        card.opacity = 1.0
        card.offset  = ft.Offset(0, 0)
        card.update()

    def on_search(e):
        async def run_search():
            results_column.controls.clear()
            ingredients = search_field.value.strip()
            if not ingredients:
                return

            empty_state.visible  = False
            results_column.visible = True
            empty_state.update()
            results_column.update()

            _set_loading_stage(0)
            page.update()

            user_ingredients = [k.strip() for k in ingredients.split(",") if k.strip()]
            loop = asyncio.get_event_loop()
            found_any = {"value": False}

            def on_recipe_found(recipe):
                async def update_ui():
                    found_any["value"] = True
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
                    await _animate_card_in(new_card)
                asyncio.run_coroutine_threadsafe(update_ui(), loop)

            def run():
                CookpadScraper.main(user_ingredients, on_recipe_found=on_recipe_found)

            await asyncio.get_event_loop().run_in_executor(None, run)
            _set_loading_stage(-1)

            if not found_any["value"]:
                not_found = _not_found_card()
                results_column.controls.append(not_found)
                page.update()

            page.update()

        page.run_task(run_search)

    search_field = ft.TextField(
        hint_text="cth: bawang putih, tomat, telur...",
        hint_style=ft.TextStyle(color=TEXT3()),
        bgcolor=BG3(),
        color=TEXT(),
        focused_border_color=ORANGE,
        border_color=BORDER(),
        border_radius=ft.BorderRadius.all(14),
        content_padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        expand=True,
        on_submit=on_search,
    )

    search_btn = ft.ElevatedButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SEARCH, color=WHITE, size=16),
                ft.Text("Cari", color=WHITE, weight=ft.FontWeight.BOLD),
            ],
            spacing=6,
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor=ORANGE,
            shape=ft.RoundedRectangleBorder(radius=14),
            mouse_cursor=ft.MouseCursor.CLICK,
            padding=ft.Padding.symmetric(horizontal=24, vertical=14),
        ),
        on_click=on_search,
    )

    def rebuild():
        container.bgcolor         = BG()
        search_field.bgcolor      = BG3()
        search_field.color        = TEXT()
        search_field.border_color = BORDER()
        search_field.update()
        for ctrl in results_column.controls:
            if not isinstance(ctrl, ft.Container):
                continue
            ctrl.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[BG3(), BG2()],
            )
            ctrl.border = ft.Border.all(1, BORDER())
            ctrl.update()
            row = getattr(ctrl, "content", None)
            if not isinstance(row, ft.Row):
                continue
            for child in row.controls:
                if isinstance(child, ft.Column):
                    for item in child.controls:
                        if isinstance(item, ft.Text):
                            item.color = TEXT() if item.weight == ft.FontWeight.BOLD else TEXT2()
                            item.update()
                        elif isinstance(item, ft.Container):
                            item.bgcolor = BG4()
                            item.update()
                            if isinstance(getattr(item, "content", None), ft.Text):
                                item.content.color = TEXT3()
                                item.content.update()
                        elif isinstance(item, ft.Row):
                            for sub in item.controls:
                                if isinstance(sub, ft.Text):
                                    sub.color = TEXT2()
                                    sub.update()
                                elif isinstance(sub, ft.Icon):
                                    sub.color = TEXT2()
                                    sub.update()
        page.update()

    theme_mgr.add_listener(rebuild)

    container = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[search_field, search_btn],
                        spacing=10,
                    ),
                    padding=ft.Padding.symmetric(horizontal=24, vertical=18),
                ),
                sticky_loader,
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=24),
                    margin=ft.Margin.only(top=4),
                    content=ft.Stack(
                        controls=[
                            empty_state,
                            results_column,
                        ],
                        expand=True,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        ),
    )

    container.results_column = results_column
    return container