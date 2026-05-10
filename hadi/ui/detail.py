import webbrowser
import asyncio
import flet as ft
import flet_video as ftv
from hadi import CookpadScraper
from rafy.theme import theme_mgr, ORANGE, WHITE
from zaky.price_panel import run_price_calculation


def BG():     return theme_mgr.get("BG")
def BG3():    return theme_mgr.get("BG3")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")



def build_detail_page(page: ft.Page, navigate_fn, topbar) -> ft.Container:
    """
    Returns the full detail page container.
    Call container.show(recipe) to populate and display a recipe.
    """

    detail_content = ft.Column(
        controls=[],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    
    detail_active = False
    
    def on_scroll(e: ft.OnScrollEvent):
        if not detail_active:
            return
        if e.pixels > 420:
            topbar.set_recipe(current_recipe.get("name", ""))
        else:
            topbar.set_recipe("")
        topbar.update()
    
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

    def _meta_pill(icon, text):
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
                        ft.Icon(ft.Icons.OPEN_IN_NEW, color=ORANGE, size=16),
                        ft.Text("Link", color=TEXT(), size=13),
                    ],
                    spacing=6,
                    tight=True,
                ),
            ),
            bgcolor=BG3(),
            border=ft.Border.all(1, ORANGE),
            border_radius=ft.BorderRadius.all(20),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            on_click=confirm_open,
            ink=True,
        )

    def _ingredient_card(ingredients: list) -> ft.Container:
        items = []
        for ing in ingredients:
            if isinstance(ing, dict) and "qty" in ing:
                qty  = ing.get("qty", "")
                name = ing.get("name", "")
            else:
                qty  = ""
                name = ing.get("name", ing) if isinstance(ing, dict) else ing

            if ing.get("is_header") or (":" in name and not qty):
                items.append(ft.Container(height=8))
                items.append(
                    ft.Container(
                        content=ft.Text(name, color=ORANGE, weight=ft.FontWeight.BOLD, size=16),
                        padding=ft.Padding.only(left=5, top=15, bottom=15),
                        expand=True,
                        width=float("inf"),
                        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                    )
                )
                continue

            row_controls = [
                ft.Container(width=8, height=8, bgcolor=ORANGE, border_radius=ft.BorderRadius.all(4)),
            ]
            if qty:
                row_controls.append(ft.Text(qty, color=TEXT(), weight=ft.FontWeight.BOLD, size=14))
            row_controls.append(ft.Text(name, color=TEXT(), size=14, expand=True))

            items.append(
                ft.Container(
                    content=ft.Row(controls=row_controls, spacing=10),
                    padding=ft.Padding.symmetric(horizontal=5, vertical=10),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                )
            )

        return ft.Container(
            content=ft.Column(controls=items, spacing=0,scroll=ft.ScrollMode.AUTO),
            bgcolor=BG3(),
            border_radius=ft.BorderRadius.all(10),
            expand=True,
        )

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
                    ft.Image(src=src, width=160, height=128, fit="cover",
                            border_radius=ft.BorderRadius.all(8))
                )

            for vid in videos:
                print(f"VID: {vid}")
                href  = vid.get("href", "")
                thumb = vid.get("thumb", "")
                if not href:
                    continue
                
                vid_player = ftv.Video(
                    playlist=[ftv.VideoMedia(href)],
                    width=160,
                    height=128,
                    autoplay=False,
                    controls=None,
                    fit=ft.BoxFit.COVER,
                )

                icon = ft.Icon(ft.Icons.PLAY_ARROW, color=WHITE, size=28)
                icon_bg = ft.Container(
                    content=icon,
                    bgcolor="#88000000",
                    border_radius=ft.BorderRadius.all(50),
                    padding=ft.Padding.all(8),
                )
                overlay = ft.Container(
                    alignment=ft.Alignment.CENTER, 
                    content=icon_bg,
                    visible=True,
                )

                async def on_tap(e, vp=vid_player, ic=icon, ov=overlay):
                    playing = await vp.is_playing()
                    await vp.play_or_pause()
                    if playing:
                        ic.icon = ft.Icons.PLAY_ARROW
                        ov.visible = True
                    else:
                        ic.icon = ft.Icons.PAUSE
                        ov.visible = True
                        ov.update()
                        ic.update()
                        await asyncio.sleep(0.8)
                        ov.visible = False
                    ov.update()
                    ic.update()

                async def on_complete(e, ic=icon, ov=overlay):
                    ic.icon = ft.Icons.PLAY_ARROW
                    ov.visible = True
                    ov.update()
                    ic.update()

                vid_player.on_complete = on_complete
                vid_player.on_load = lambda e, ov=overlay, ic=icon: (
                    setattr(ov, "visible", True),
                    ov.update(),
                )

                media_controls.append(
                    ft.Container(
                        width=160,
                        height=128,
                        border_radius=ft.BorderRadius.all(8),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=ft.GestureDetector(
                            mouse_cursor=ft.MouseCursor.CLICK,
                            on_tap=on_tap,
                            content=ft.Stack(
                                controls=[
                                    vid_player,
                                    overlay,
                                ],
                            ),
                        ),
                    )
                )

            media_row = ft.Row(
                controls=media_controls,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ) if media_controls else ft.Container()

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
                            ft.Column(
                                controls=[
                                    ft.Text(text, color=TEXT(), size=14, expand=True),
                                    media_row,
                                ],
                                spacing=8,
                                expand=True,
                            ),
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                )
            )

        return ft.Container(
            content=ft.Column(controls=items, spacing=0,scroll=ft.ScrollMode.AUTO,),
            bgcolor=BG3(),
            border_radius=ft.BorderRadius.all(10),
            expand=True,
        )
        
    current_recipe: dict = {}
    def show(recipe: dict):
        nonlocal current_recipe, detail_active
        detail_active = True
        topbar.set_recipe("")
        topbar.update()
        current_recipe = recipe
        detail_content.controls.clear()
        
        ingredient_count = len(recipe.get("ingredients", []))
        steps_count      = len(recipe.get("steps", []))

        MAX_HEIGHT = page.window.height - 200
        ITEM_HEIGHT      = 100
        STEP_HEIGHT      = 150
        ingredient_height = min(ingredient_count * ITEM_HEIGHT, MAX_HEIGHT)
        steps_height      = min(steps_count * STEP_HEIGHT, MAX_HEIGHT)
        panel_height      = max(ingredient_height, steps_height)

        ing_container_height  = ingredient_height if ingredient_height < MAX_HEIGHT else panel_height
        step_container_height = steps_height      if steps_height      < MAX_HEIGHT else panel_height

        price_area_ref = ft.Ref[ft.Container]()
        kalk_btn_ref   = ft.Ref[ft.ElevatedButton]()

        # Hero
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
                            padding=ft.Padding.symmetric(horizontal=30, vertical=20),
                            content=ft.Column(
                                controls=[
                                    ft.Text(recipe.get("name", ""), size=28,
                                            weight=ft.FontWeight.BOLD, color=WHITE),
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

        # Meta pills
        detail_content.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        _meta_pill(ft.Icons.PEOPLE_OUTLINE, recipe.get("portion", "")),
                        _meta_pill(ft.Icons.TIMER_OUTLINED, recipe.get("cook_time", "")),
                        _meta_pill_link(recipe),
                        ft.Row(expand=True),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=30, vertical=16),
                border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
            )
        )

        # Ingredients + Steps
        detail_content.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text("Bahan-bahan", size=22, weight=ft.FontWeight.BOLD, color=TEXT()),
                                ft.Container(
                                    content=_ingredient_card(recipe.get("ingredients", [])),
                                    height=ing_container_height if ingredient_height >= MAX_HEIGHT else None,
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE if ingredient_height >= MAX_HEIGHT else ft.ClipBehavior.NONE,
                                ),
                            ],
                            spacing=16,
                            expand=1,
                        ),
                        ft.Container(width=30),
                        ft.Column(
                            controls=[
                                ft.Text("Cara Membuat", size=22, weight=ft.FontWeight.BOLD, color=TEXT()),
                                ft.Container(
                                    content=_steps_card(recipe.get("steps", [])),
                                    height=step_container_height if steps_height >= MAX_HEIGHT else None,
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE if steps_height >= MAX_HEIGHT else ft.ClipBehavior.NONE,
                                ),
                            ],
                            spacing=16,
                            expand=2,
                        ),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    expand=True,
                ),
                padding=ft.Padding.symmetric(horizontal=30, vertical=24),
                expand=True,
            )
        )

        # Price calculator
        detail_content.controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.ElevatedButton(
                            ref=kalk_btn_ref,
                            content=ft.Text("💰 Kalkulasi Harga Bahan", color=WHITE),
                            on_click=lambda e: run_price_calculation(
                                page, recipe, price_area_ref, kalk_btn_ref
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=ORANGE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding.symmetric(horizontal=24, vertical=14),
                            ),
                        ),
                        ft.Container(
                            ref=price_area_ref,
                            visible=False,
                            expand=True,
                        ),
                    ],
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.Padding.symmetric(horizontal=30, vertical=20),
                border=ft.Border.only(top=ft.BorderSide(1, BORDER())),
            )
        )

        navigate_fn("detail")
        page.update()

    container.show = show
    container.detail_active = False
    return container
