import webbrowser
import asyncio
import flet as ft
import flet_video as ftv
from hadi import CookpadScraper
from rafy.theme import theme_mgr, ORANGE, ORANGE_GLOW2, WHITE
from zaky.price_panel import run_price_calculation


def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


def build_detail_page(page: ft.Page, navigate_fn, topbar) -> ft.Container:
    detail_content = ft.Column(
        controls=[],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    detail_active = False

    # Keep explicit refs to themed widgets for correct rebuild
    _themed_widgets: list = []  # list of (widget, attr, fn) tuples

    def _track(widget, attr: str, fn):
        """Register a widget attribute for theme rebuild."""
        _themed_widgets.append((widget, attr, fn))
        return widget

    def on_scroll(e: ft.OnScrollEvent):
        if not detail_active:
            return
        if e.pixels > 380:
            topbar.set_recipe(current_recipe.get("name", ""))
        else:
            topbar.set_recipe("")
        topbar.update()

    prev_page = {"name": "finder"}

    container = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        content=ft.Stack(
            controls=[
                ft.Column(
                    controls=[detail_content],
                    spacing=0,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    on_scroll=on_scroll,
                ),
            ],
            expand=True,
        ),
    )

    def _go_back(e):
        navigate_fn(prev_page["name"])

    def rebuild():
        container.bgcolor = BG()
        container.update()
        # Rebuild all tracked themed widgets
        for widget, attr, fn in _themed_widgets:
            try:
                setattr(widget, attr, fn())
                widget.update()
            except Exception:
                pass

    theme_mgr.add_listener(rebuild)

    def _meta_pill(icon, text):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=ORANGE, size=15),
                    ft.Text(text, color=WHITE, size=12, font_family="Font"),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor=ORANGE_GLOW2,
            border=ft.Border.all(1, ORANGE),
            border_radius=ft.BorderRadius.all(20),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        )

    def _meta_pill_link(recipe):
        def confirm_open(e):
            def do_open(e2):
                webbrowser.open(recipe.get("source_url", ""))
                dlg.open = False
                page.update()

            def do_cancel(e2):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("Open Link?"),
                content=ft.Text("This will open the recipe link in your browser."),
                actions=[
                    ft.TextButton("Cancel", on_click=do_cancel),
                    ft.TextButton("Open", on_click=do_open, style=ft.ButtonStyle(color=ORANGE)),
                ],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        return ft.Container(
            content=ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.CLICK,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.OPEN_IN_NEW, color=ORANGE, size=15),
                        ft.Text("Link", color=WHITE, size=12, font_family="Font"),
                    ],
                    spacing=6,
                    tight=True,
                ),
            ),
            bgcolor=ORANGE_GLOW2,
            border=ft.Border.all(1, ORANGE),
            border_radius=ft.BorderRadius.all(20),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            on_click=confirm_open,
            ink=True,
        )

    def _is_header(ing: dict | str, name: str, qty: str) -> bool:
        if isinstance(ing, dict) and ing.get("is_header"):
            return True
        if qty:
            return False
        if ":" in name:
            return True
        clean = name.strip()
        while clean and not clean[0].isalpha():
            clean = clean[1:]
        words = clean.strip().split()
        if words and all(w[0].isupper() for w in words if w):
            return True
        return False

    def _ingredient_card(ingredients: list) -> ft.Container:
        items = []
        for ing in ingredients:
            if isinstance(ing, str):
                qty, name = "", ing
            elif isinstance(ing, dict):
                qty  = ing.get("qty", "")
                name = ing.get("name", "")
            else:
                qty, name = "", str(ing)

            if _is_header(ing, name, qty):
                items.append(ft.Container(height=6))
                header_text = ft.Text(
                    name, color=ORANGE,
                    weight=ft.FontWeight.BOLD, size=13,
                    font_family="Font",
                )
                header_border = ft.Container(
                    content=header_text,
                    padding=ft.Padding.only(left=12, top=10, bottom=6),
                    expand=True,
                    width=float("inf"),
                    border=ft.Border.only(top=ft.BorderSide(1, BORDER())),
                )
                _track(header_border, "border",
                       lambda: ft.Border.only(top=ft.BorderSide(1, BORDER())))
                items.append(header_border)
                continue

            row_controls = [
                ft.Container(
                    width=6,
                    bgcolor=ORANGE,
                    border_radius=ft.BorderRadius.all(3),
                ),
            ]
            #ing text
            if qty:
                qty_text = ft.Text(
                    qty, color=TEXT(), weight=ft.FontWeight.BOLD,
                    size=15, font_family="Font",
                )
                _track(qty_text, "color", TEXT)
                row_controls.append(qty_text)

            name_text = ft.Text(
                name, color=TEXT(), size=14, expand=True, weight=ft.FontWeight.W_500, font_family="Font",
            )
            _track(name_text, "color", TEXT)
            row_controls.append(name_text)

            row_container = ft.Container(
                content=ft.Row(controls=row_controls, spacing=10),
                padding=ft.Padding.symmetric(horizontal=12, vertical=9),
                border_radius=ft.BorderRadius.all(8),
                on_hover=lambda e: (
                    setattr(e.control, "bgcolor",
                            "#20ff6a20" if e.data else ft.Colors.TRANSPARENT),
                    e.control.update(),
                ),
            )
            items.append(row_container)

        def _ing_gradient():
            return ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=["#30ff6a0a", "#00ff6a0a"],
                stops=[0.0, 0.05,],
            )

        card = ft.Container(
            content=ft.Column(controls=items, spacing=0, scroll=ft.ScrollMode.AUTO),
            gradient=_ing_gradient(),
            border_radius=ft.BorderRadius.all(14),
            border=ft.Border.all(1, BORDER()),
            expand=True,
            padding=ft.Padding.symmetric(vertical=6),
            animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, 0),
        )
        _track(card, "border", lambda: ft.Border.all(1, BORDER()))
        _track(card, "gradient", _ing_gradient)
        return card

    def _steps_card(steps: list) -> ft.Container:
        items = []
        for i, step in enumerate(steps, start=1):
            text   = step.get("text",   step) if isinstance(step, dict) else step
            images = step.get("images", [])   if isinstance(step, dict) else []
            videos = step.get("videos", [])   if isinstance(step, dict) else []

            media_controls = []

            for src in images:
                if any(skip in src for skip in ["video.thumbnail", "/step_videos/", ".mp4", ".webm", ".mov"]):
                    continue
                media_controls.append(
                    ft.Container(
                        content=ft.Image(src=src, width=140, height=110, fit="cover"),
                        width=140, height=110,
                        border_radius=ft.BorderRadius.all(10),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    )
                )

            for vid in videos:
                href = vid.get("href", "")
                if not href:
                    continue

                vid_player = ftv.Video(
                    playlist=[ftv.VideoMedia(href)],
                    width=140, height=110,
                    autoplay=False,
                    controls=None,
                    fit=ft.BoxFit.COVER,
                )

                icon_img = ft.Icon(ft.Icons.PLAY_ARROW, color=WHITE, size=26)
                icon_bg  = ft.Container(
                    content=icon_img,
                    bgcolor="#88000000",
                    border_radius=ft.BorderRadius.all(50),
                    padding=ft.Padding.all(8),
                )
                overlay = ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=icon_bg,
                    visible=True,
                )

                async def on_tap(e, vp=vid_player, ic=icon_img, ov=overlay):
                    playing = await vp.is_playing()
                    await vp.play_or_pause()
                    if playing:
                        ic.name    = ft.Icons.PLAY_ARROW
                        ov.visible = True
                    else:
                        ic.name    = ft.Icons.PAUSE
                        ov.visible = True
                        ov.update()
                        ic.update()
                        await asyncio.sleep(0.8)
                        ov.visible = False
                    ov.update()
                    ic.update()

                async def on_complete(e, ic=icon_img, ov=overlay):
                    ic.name    = ft.Icons.PLAY_ARROW
                    ov.visible = True
                    ov.update()
                    ic.update()

                vid_player.on_complete = on_complete

                media_controls.append(
                    ft.Container(
                        width=140, height=110,
                        border_radius=ft.BorderRadius.all(10),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=ft.GestureDetector(
                            mouse_cursor=ft.MouseCursor.CLICK,
                            on_tap=on_tap,
                            content=ft.Stack(controls=[vid_player, overlay]),
                        ),
                    )
                )

            media_row = ft.Row(
                controls=media_controls,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ) if media_controls else None
            #step text
            step_text = ft.Text(
                text, color=TEXT(), size=15, font_family="Font",weight=ft.FontWeight.W_500,
                expand=True, selectable=True,
            )
            _track(step_text, "color", TEXT)

            step_controls = [step_text]
            if media_row:
                step_controls.append(ft.Container(height=8))
                step_controls.append(media_row)

            is_last  = i == len(steps)
            step_num = ft.Container(
                content=ft.Text(
                    str(i), color=WHITE, size=12,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=28, height=28,
                bgcolor=ORANGE,
                border_radius=ft.BorderRadius.all(14),
                alignment=ft.Alignment(0, 0),
            )

            timeline_line = ft.Container(
                width=2,
                expand=True,
                bgcolor=BORDER(),
                margin=ft.Margin.only(top=4),
            ) if not is_last else ft.Container(width=2)

            if not is_last:
                _track(timeline_line, "bgcolor", BORDER)

            items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[step_num, timeline_line],
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Column(
                                controls=step_controls,
                                spacing=4,
                                expand=True,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                )
            )

        def _step_gradient():
            return ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=["#3100a696", "#0000bc7d"],
                stops=[0.0, 0.05],
            )

        card = ft.Container(
            content=ft.Column(controls=items, spacing=0, scroll=ft.ScrollMode.AUTO),
            gradient=_step_gradient(),
            border_radius=ft.BorderRadius.all(14),
            border=ft.Border.all(1, BORDER()),
            expand=True,
            animate_offset=ft.Animation(430, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, 0),
        )
        _track(card, "border", lambda: ft.Border.all(1, BORDER()))
        _track(card, "gradient", _step_gradient)
        return card

    current_recipe: dict = {}

    def show(recipe: dict):
        nonlocal current_recipe, detail_active
        detail_active  = True
        current_recipe = recipe
        _themed_widgets.clear()
        topbar.set_recipe("")
        topbar.update()
        detail_content.controls.clear()

        ingredient_count = len(recipe.get("ingredients", []))
        steps_count      = len(recipe.get("steps", []))
        MAX_HEIGHT       = page.window.height - 220
        ITEM_HEIGHT      = 100
        STEP_HEIGHT      = 150
        ingredient_height = min(ingredient_count * ITEM_HEIGHT, MAX_HEIGHT)
        steps_height      = min(steps_count * STEP_HEIGHT, MAX_HEIGHT)

        ing_h  = ingredient_height if ingredient_height >= MAX_HEIGHT else None
        step_h = steps_height      if steps_height      >= MAX_HEIGHT else None

        price_area_ref = ft.Ref[ft.Container]()
        kalk_btn_ref   = ft.Ref[ft.ElevatedButton]()

        # ── Hero ── with scale-in animation
        hero_image = ft.Container(
            content=ft.Image(
                src=recipe.get("image_url", ""),
                width=float("inf"),
                height=460,
                fit="cover",
            ),
            width=float("inf"),
            height=460,
            scale=ft.Scale(scale=1.06),
            animate_scale=ft.Animation(600, ft.AnimationCurve.EASE_OUT),
        )

        detail_content.controls.append(
            ft.Container(
                height=460,
                content=ft.Stack(
                    controls=[
                        hero_image,
                        # Deep gradient layers
                        ft.Container(
                            width=float("inf"),
                            height=460,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment(0, 1),
                                end=ft.Alignment(0, -0.3),
                                colors=["#F8000000", "#40000000", "#00000000"],
                                stops=[0.0, 0.5, 1.0],
                            ),
                        ),
                        # Warm radial glow at center-bottom
                        ft.Container(
                            width=float("inf"),
                            height=460,
                            gradient=ft.RadialGradient(
                                center=ft.Alignment(0, 1.2),
                                radius=1.0,
                                colors=["#30ff6a20", "#00000000"],
                            ),
                        ),
                        ft.Container(
                            bottom=0, left=0, right=0,
                            padding=ft.Padding.symmetric(horizontal=32, vertical=24),
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        recipe.get("name", ""),
                                        size=42,
                                        weight=ft.FontWeight.W_900,
                                        color=WHITE,
                                        font_family="Font",
                                    ),
                                    ft.Text(
                                        f"oleh {recipe.get('author', '')}",
                                        size=12, color="#aaffffff",
                                        font_family="Font",
                                    ),
                                    ft.Container(height=10),
                                    ft.Row(
                                        controls=[
                                            _meta_pill(ft.Icons.PEOPLE_OUTLINE, recipe.get("portion", "")),
                                            _meta_pill(ft.Icons.TIMER_OUTLINED, recipe.get("cook_time", "")),
                                            _meta_pill_link(recipe),
                                        ],
                                        spacing=8,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ),
                    ],
                ),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                border_radius=ft.BorderRadius.all(0),
            )
        )

        # Build cards with slide-in offsets (reset to 0 via animation after render)
        ing_card  = _ingredient_card(recipe.get("ingredients", []))
        step_card = _steps_card(recipe.get("steps", []))
        ing_card.offset  = ft.Offset(-0.08, 0)
        step_card.offset = ft.Offset(0.08, 0)

        bahan_label = ft.Text("BAHAN-BAHAN",  size=15, weight=ft.FontWeight.BOLD,
                            color=TEXT(), font_family="Font",
                            style=ft.TextStyle(letter_spacing=1.5))
        cara_label  = ft.Text("CARA MEMBUAT", size=15, weight=ft.FontWeight.BOLD,
                            color=TEXT(), font_family="Font",
                            style=ft.TextStyle(letter_spacing=1.5))
        _track(bahan_label, "color", TEXT2)
        _track(cara_label,  "color", TEXT2)

        # ── Ingredients + Steps side by side ──
        detail_content.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                bahan_label,
                                ft.Container(
                                    content=ing_card,
                                    height=ing_h,
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE if ing_h else ft.ClipBehavior.NONE,
                                    expand=ing_h is None,
                                ),
                            ],
                            spacing=10,
                            expand=1,
                        ),
                        ft.Container(width=20),
                        ft.Column(
                            controls=[
                                cara_label,
                                ft.Container(
                                    content=step_card,
                                    height=step_h,
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE if step_h else ft.ClipBehavior.NONE,
                                    expand=step_h is None,
                                ),
                            ],
                            spacing=10,
                            expand=2,
                        ),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    expand=True,
                ),
                padding=ft.Padding.symmetric(horizontal=28, vertical=22),
                expand=True,
            )
        )

        # ── Price calculator ──
        # Divider di luar container agar tidak kena padding horizontal → full width
        divider = ft.Container(height=1, bgcolor=BORDER())
        _track(divider, "bgcolor", BORDER)
        detail_content.controls.append(divider)

        detail_content.controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.ElevatedButton(
                            ref=kalk_btn_ref,
                            content=ft.Row(
                                controls=[
                                    ft.Text("💰", size=16),
                                    ft.Text(
                                        "Kalkulasi Harga Bahan",
                                        color=WHITE,
                                        weight=ft.FontWeight.BOLD,
                                        font_family="Font",
                                    ),
                                ],
                                spacing=8,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            on_click=lambda e: run_price_calculation(
                                page, recipe, price_area_ref, kalk_btn_ref
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=ORANGE,
                                shape=ft.RoundedRectangleBorder(radius=14),
                                padding=ft.Padding.symmetric(horizontal=28, vertical=16),
                                mouse_cursor=ft.MouseCursor.CLICK,
                                overlay_color={"hovered": "#d94410", "pressed": "#c03b0d", "": ORANGE},
                            ),
                        ),
                        ft.Container(
                            ref=price_area_ref,
                            visible=False,
                            expand=True,
                        ),
                    ],
                    spacing=16,
                    # STRETCH → tombol melebar penuh mengikuti lebar column
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                padding=ft.Padding.symmetric(horizontal=28, vertical=20),
                expand=True,
            )
        )

        navigate_fn("detail")
        page.update()

        # Trigger slide-in and hero scale-down after first render
        async def _animate_in():
            await asyncio.sleep(0.05)
            hero_image.scale     = ft.Scale(scale=1.0)
            ing_card.offset  = ft.Offset(0, 0)
            step_card.offset = ft.Offset(0, 0)
            hero_image.update()
            ing_card.update()
            step_card.update()

        page.run_task(_animate_in)

    container.show          = show
    container.detail_active = False
    return container
