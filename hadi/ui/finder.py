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

# Floating emoji data: (emoji, base_offset_y, amplitude, period_s)
_FLOAT_EMOJIS = [
    ("🧄", 0.0,  10, 2.6),
    ("🍅", 0.0,   8, 2.1),
    ("🥚", 0.0,  12, 3.0),
    ("🧅", 0.0,   9, 2.4),
    ("🌶️", 0.0, 11, 2.8),
]


def build_finder_page(page: ft.Page, show_detail_fn) -> ft.Container:

    # ── Loader ───────────────────────────────────────────────────────
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
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            scale=ft.Scale(scale=1.0),
        )
        for _ in range(6)
    ]

    loader_ring_bg = ft.Container(
        content=loader_ring, width=60, height=60,
        bgcolor=BG3(), border_radius=ft.BorderRadius.all(22),
        alignment=ft.Alignment.CENTER,
    )

    sticky_loader = ft.Container(
        visible=False,
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        padding=ft.Padding.symmetric(horizontal=24, vertical=15),
        content=ft.Row(
            controls=[
                loader_ring_bg,
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
                dot.scale   = ft.Scale(scale=1.0)
            elif i == stage:
                # Active dot: pulse scale
                dot.bgcolor = ft.Colors.TRANSPARENT
                dot.border  = ft.Border.all(2, ORANGE)
                dot.scale   = ft.Scale(scale=1.35)
            else:
                dot.bgcolor = BG3()
                dot.border  = ft.Border.all(1, BORDER())
                dot.scale   = ft.Scale(scale=1.0)
        page.update()

    # ── Floating emoji animation state ───────────────────────────────
    _float_tasks_active = {"value": False}
    _emoji_containers: list[ft.Container] = []

    async def _float_all_emojis_loop():
        toggles = [i % 2 == 0 for i in range(len(_emoji_containers))]
        while _float_tasks_active["value"]:
            for i, c in enumerate(_emoji_containers):
                _, _, amp, period = _FLOAT_EMOJIS[i]
                c.offset = ft.Offset(0, (amp if toggles[i] else -amp) / 100)
                toggles[i] = not toggles[i]
            page.update()
            await asyncio.sleep(1.3)

    def _start_float_animations():
        _float_tasks_active["value"] = True
        page.run_task(_float_all_emojis_loop)

    def _stop_float_animations():
        _float_tasks_active["value"] = False
        for c in _emoji_containers:
            c.offset = ft.Offset(0, 0)

    # Build floating emoji row
    for emoji, _, amp, period in _FLOAT_EMOJIS:
        _emoji_containers.append(
            ft.Container(
                content=ft.Text(emoji, size=28),
                animate_offset=ft.Animation(
                    int(period * 500),
                    ft.AnimationCurve.EASE_IN_OUT,
                ),
                offset=ft.Offset(0, 0),
            )
        )

    # "or press Enter" pulsing hint
    enter_hint = ft.Container(
        content=ft.Text(
            "atau tekan Enter ↵",
            size=12,
            color=TEXT3(),
            font_family="Font",
            text_align=ft.TextAlign.CENTER,
            italic=True,
        ),
        animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
        opacity=0.5,
    )

    async def _pulse_enter_hint():
        while True:
            enter_hint.opacity = 1.0
            if enter_hint.page:
                enter_hint.update()
            await asyncio.sleep(1.2)
            enter_hint.opacity = 0.3
            if enter_hint.page:
                enter_hint.update()
            await asyncio.sleep(1.2)

    # Empty state title/subtitle refs for theme rebuilding
    empty_title = ft.Text(
        "Masukkan bahan yang kamu punya",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=TEXT(),
        font_family="Font",
        text_align=ft.TextAlign.CENTER,
    )
    empty_sub = ft.Text(
        "CookD akan carikan resep terbaik\nsesuai bahan di dapurmu 🥘",
        size=14,
        color=TEXT2(),
        font_family="Font",
        text_align=ft.TextAlign.CENTER,
    )

    empty_state = ft.Container(
        visible=True,
        expand=True,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, 0),
            radius=1.2,
            colors=["#18206a20", "#00000000"],  # AA RR GG BB
        ),
        content=ft.Column(
            controls=[
                ft.Text("🍳", size=72),
                ft.Container(height=16),
                empty_title,
                ft.Container(height=8),
                empty_sub,
                ft.Container(height=24),
                ft.Row(
                    controls=_emoji_containers,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
                ft.Container(height=16),
                enter_hint,
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
            colors=[BG3(), BG2(), BG3()],
            stops=[0.0, 0.5, 1.0],
        )

    def _card_hover_gradient():
        return ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#28ff8c40", "#18ff6a20", BG2()],
            stops=[0.0, 0.4, 1.0],
        )

    # Track all not-found / result cards for theme rebuilds
    _tracked_cards: list[ft.Container] = []

    def _not_found_card() -> ft.Container:
        sad_emoji = ft.Container(
            content=ft.Text("😔", size=52),
            animate_offset=ft.Animation(400, ft.AnimationCurve.BOUNCE_OUT),
            offset=ft.Offset(0, 0),
        )

        async def _shake_emoji():
            for dx in [0.05, -0.05, 0.04, -0.04, 0.02, -0.02, 0.0]:
                sad_emoji.offset = ft.Offset(dx, 0)
                if sad_emoji.page:
                    sad_emoji.update()
                await asyncio.sleep(0.06)

        card = ft.Container(
            content=ft.Column(
                controls=[
                    sad_emoji,
                    ft.Container(height=4),
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
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Text(
                            "Coba lagi →",
                            color=ORANGE,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            font_family="Font",
                        ),
                        bgcolor="#2a1505",
                        border=ft.Border.all(1, ORANGE),
                        border_radius=ft.BorderRadius.all(20),
                        padding=ft.Padding.symmetric(horizontal=18, vertical=8),
                        on_click=lambda e: (
                            setattr(search_field, "value", ""),
                            search_field.focus(),
                            search_field.update(),
                        ),
                        ink=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=["#2a1010", BG2(), BG3()],
                stops=[0.0, 0.5, 1.0],
            ),
            border_radius=ft.BorderRadius.all(16),
            border=ft.Border.all(1, "#7f3030"),
            padding=ft.Padding.symmetric(horizontal=24, vertical=32),
            alignment=ft.Alignment(0, 0),
            animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_IN),
            animate_offset=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            opacity=0.0,
            offset=ft.Offset(0, 0.15),
        )

        async def _animate_in():
            await asyncio.sleep(0.01)
            card.opacity = 1.0
            card.offset  = ft.Offset(0, 0)
            card.update()
            await asyncio.sleep(0.1)
            await _shake_emoji()

        page.run_task(_animate_in)
        _tracked_cards.append(card)
        return card

    def _build_card(r: dict, entrance_delay: float = 0.0) -> ft.Container:
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
            card.scale    = ft.Scale(scale=0.97)
            card.gradient = _card_gradient()
            card.border   = ft.Border.all(1, BORDER())
            card.update()
            await asyncio.sleep(0.08)
            card.scale    = ft.Scale(scale=1.0)
            card.gradient = _card_gradient()
            card.border   = ft.Border.all(1, BORDER())
            card.update()
            show_detail_fn(r)

        def on_hover(e):
            if e.data:
                card.gradient = _card_hover_gradient()
                card.border   = ft.Border.all(1, ORANGE)
                thumb.border_radius = ft.BorderRadius.all(14)
            else:
                card.gradient = _card_gradient()
                card.border   = ft.Border.all(1, BORDER())
                thumb.border_radius = ft.BorderRadius.all(12)
            card.update()
            thumb.update()

        card = ft.Container(
            data=score,
            scale=ft.Scale(scale=1.0),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_IN),
            animate_offset=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            opacity=0.0,
            offset=ft.Offset(0, 0.12),
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
                                size=21,
                                font_family="Font",
                            ),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=TEXT2(), size=13),
                                    ft.Text(r.get("portion", ""),    color=TEXT2(), size=12),
                                    ft.Text("·",                     color=TEXT3(), size=12),
                                    ft.Icon(ft.Icons.TIMER_OUTLINED, color=TEXT2(), size=13),
                                    ft.Text(r.get("cook_time", ""),  color=TEXT2(), size=12),
                                ],
                                spacing=4,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    r.get("source", "Cookpad"),
                                    color=TEXT(), size=10,
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
            on_hover=on_hover,
            on_click=on_card_click,
        )
        _tracked_cards.append(card)
        return card

    async def _animate_card_in(card: ft.Container, delay: float = 0.0):
        if delay > 0:
            await asyncio.sleep(delay)
        card.opacity = 1.0
        card.offset  = ft.Offset(0, 0)
        card.update()

    def on_search(e):
        async def run_search():
            _tracked_cards.clear()
            results_column.controls.clear()
            _stop_float_animations()
            ingredients = search_field.value.strip()
            if not ingredients:
                return

            empty_state.visible    = False
            results_column.visible = True
            empty_state.update()
            results_column.update()

            _set_loading_stage(0)
            page.update()

            user_ingredients = [k.strip() for k in ingredients.split(",") if k.strip()]
            loop = asyncio.get_event_loop()
            found_any = {"value": False}
            card_count = {"n": 0}

            def on_recipe_found(recipe):
                async def update_ui():
                    found_any["value"] = True
                    n = len(results_column.controls)
                    _set_loading_stage(min(1 + n, 4))
                    delay = card_count["n"] * 0.06
                    card_count["n"] += 1
                    new_card  = _build_card(recipe, entrance_delay=delay)
                    insert_at = len(results_column.controls)
                    for i, ctrl in enumerate(results_column.controls):
                        if recipe["match_score"] > (ctrl.data or 0):
                            insert_at = i
                            break
                    results_column.controls.insert(insert_at, new_card)
                    page.update()
                    await _animate_card_in(new_card, delay)
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
        # Update loader background
        loader_ring_bg.bgcolor = BG3()
        loader_ring_bg.update()
        loader_sub.color = TEXT2()
        loader_sub.update()
        # Update empty state colors
        empty_title.color = TEXT()
        empty_sub.color   = TEXT2()
        empty_title.update()
        empty_sub.update()
        for card in _tracked_cards:
            if not isinstance(card, ft.Container):
                continue
            # Only reset if not currently hovered (can't detect hover state; reset to base)
            card.gradient = _card_gradient()
            card.border   = ft.Border.all(1, BORDER())
            card.update()
            row = getattr(card, "content", None)
            if not isinstance(row, ft.Row):
                continue
            for child in row.controls:
                if isinstance(child, ft.Column):
                    for item in child.controls:
                        if isinstance(item, ft.Text):
                            item.color = TEXT() if item.weight == ft.FontWeight.BOLD else TEXT2()
                            item.update()
                        elif isinstance(item, ft.Container):
                            # Skip the match-score badge — it has its own fixed color
                            _is_score_badge = (
                                isinstance(getattr(item, "content", None), ft.Text)
                                and item.border_radius is not None
                                and getattr(item, "padding", None) is not None
                                and getattr(item.content, "weight", None) == ft.FontWeight.BOLD
                                and item.bgcolor not in (None, ft.Colors.TRANSPARENT, BG4())
                            )
                            if not _is_score_badge:
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

    def on_visible_change(e):
        # Start/stop float animations when page becomes visible/hidden
        if container.visible:
            if not _float_tasks_active["value"] and empty_state.visible:
                _start_float_animations()
            page.run_task(_pulse_enter_hint)
        else:
            _stop_float_animations()

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
                    bgcolor=ft.Colors.TRANSPARENT,
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

    # Kick off float animations when the finder page first becomes visible
    original_visible = property(
        lambda self: self._visible,
        lambda self, v: setattr(self, "_visible", v),
    )

    container.results_column = results_column

    # Start float animations immediately (they'll self-stop when not visible)
    _start_float_animations()
    page.run_task(_pulse_enter_hint)

    return container