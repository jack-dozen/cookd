import flet as ft
import flet_lottie as ftl
import json
import asyncio
import webbrowser
from hadi import CookpadScraper
import subprocess
from fadhil.my_recipes import MyRecipesPage
from rafy.theme import theme_mgr, ORANGE, GREEN, AMBER, BLUE, WHITE, BLACK
from rafy.sidebar import build_sidebar_extras
from zaky.info import InfoPage
from zaky.price_panel import run_price_calculation

# ─────────────────────────────────────────────────────────────────────
# COLORS & THEME
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
        if name == "detail" and recipe:
            show_detail(recipe)
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
            padding=ft.Padding.symmetric(horizontal=15, vertical=12),
            border_radius=10,
            bgcolor=BG3() if is_active else ft.Colors.TRANSPARENT,
            on_hover=on_hover,
            on_click=on_click
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
            # Check if the item has a 'content' attribute (like a Container)
            content = getattr(item, "content", None)
            
            # If it's a Row (or a Container holding a Row)
            if isinstance(content, ft.Row) or isinstance(item, ft.Row):
                row = content if isinstance(content, ft.Row) else item
                # Look through everything in the row
                for ctrl in row.controls:
                    # Hide anything that is a Text object
                    if isinstance(ctrl, ft.Text):
                        ctrl.visible = not is_collapsing
                    
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
        content=ft.Stack(
            controls=[
                ft.Column(
                    controls=[
                        detail_content,
                    ],
                    spacing=0,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.Container(
                    content=ft.FloatingActionButton(
                        icon=ft.Icons.ARROW_BACK_IOS,
                        bgcolor=ORANGE,
                        foreground_color=WHITE,
                        mini=True,
                        mouse_cursor=ft.MouseCursor.CLICK,
                        on_click=lambda e: navigate("finder"),
                    ),
                    top=5,
                    left=5,
                ),
            ],
            expand=True,
        ),
    )

    def show_detail(recipe: dict):
        detail_content.controls.clear()
        price_area_ref = ft.Ref[ft.Container]()
        kalk_btn_ref   = ft.Ref[ft.ElevatedButton]()

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
                            padding=ft.Padding.symmetric(horizontal=30, vertical=20),
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
                padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            )
            
        def meta_pill_link():
            return ft.Container(
                content=ft.GestureDetector(  # ← add content=
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
            
        def confirm_open(e):
            def do_open(e2):
                import webbrowser
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
                    ft.TextButton("Cancel",  on_click=do_cancel),
                    ft.TextButton("Open",   on_click=do_open,   style=ft.ButtonStyle(color=ORANGE)),
                ],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        
        detail_content.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        meta_pill(ft.Icons.PEOPLE_OUTLINE, recipe.get("portion", "")),
                        meta_pill(ft.Icons.TIMER_OUTLINED, recipe.get("cook_time", "")),
                        meta_pill_link(),
                        ft.Row(expand=True),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=30, vertical=16),
                border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
            )
        )

        # ── Ingredients ──
        def ingredient_card(ingredients: list) -> ft.Container:
            items = []
            for ing in ingredients:
                if isinstance(ing, dict) and "qty" in ing:
                    qty  = ing.get("qty", "")
                    name = ing.get("name", "")
                else:
                    # fallback for old scraped data without qty field
                    qty  = ""
                    name = ing.get("name", ing) if isinstance(ing, dict) else ing
    
                #print(f"DEBUG: qty='{qty}' name='{name}' is_header={ing.get('is_header')} has_colon={':' in name}")  # ← here

                # Detect section headers (no qty, name ends with ":" or all caps)
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
                content=ft.Column(controls=items, spacing=0),
                bgcolor=BG3(),
                border_radius=ft.BorderRadius.all(10),
                expand=True,
            )
            

        # ── Steps ──
        def steps_card(steps: list) -> ft.Container:
            items = []      
            for i, step in enumerate(steps, start=1):
                text   = step.get("text", step)   if isinstance(step, dict) else step
                images = step.get("images", [])   if isinstance(step, dict) else []
                videos = step.get("videos", []) if isinstance(step, dict) else []

                media_controls = []
                
                for src in images:
                    if any(skip in src for skip in ["video.thumbnail", "/step_videos/", ".mp4", ".webm", ".mov"]):
                        continue
                    media_controls.append(
                        ft.Image(src=src, width=160, height=128, fit="cover",
                                border_radius=ft.BorderRadius.all(8))
                    )

                for vid in videos:
                    href  = vid.get("href", "")
                    thumb = vid.get("thumb", "")
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = CookpadScraper.BASE_URL + href

                    media_controls.append(
                        ft.GestureDetector(
                            mouse_cursor=ft.MouseCursor.CLICK,
                            on_tap=lambda e, url=href: webbrowser.open(url),
                            content=ft.Stack(controls=[
                                ft.Image(src=thumb, width=160, height=128, fit="cover",
                                    border_radius=ft.BorderRadius.all(8)),
                                ft.Container(
                                    width=160, height=128,
                                    border_radius=ft.BorderRadius.all(8),
                                    bgcolor="#88000000",
                                    alignment=ft.alignment.center,
                                    content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED, color=WHITE, size=40),
                                ),
                            ]),
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
                content=ft.Column(controls=items, spacing=0),
                bgcolor=BG3(),
                border_radius=ft.BorderRadius.all(10),
                expand=True,
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
                padding=ft.Padding.symmetric(horizontal=30, vertical=24),
                expand=True,
            )
        )
        
        # ── Kalkulasi Harga ──
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
    
    # Build once, near results_column
    COOKING_STAGES = [
        ("Preparing ingredients...",    "Fetching page"),
        ("Cracking the recipe open...", "Parsing HTML"),
        ("Mixing the instructions...",  "Extracting steps"),
        ("Gathering ingredients...",    "Building card"),
        ("Sliding into the oven...",    "Almost done"),
        ("Recipe served! 🍽",           "Loaded"),
    ]
    

    loader_label  = ft.Text(COOKING_STAGES[0][0], color=ORANGE, size=14, italic=True)
    loader_sub    = ft.Text(COOKING_STAGES[0][1], color=TEXT2(), size=11)
    loader_ring = ftl.Lottie(
        src="https://lottie.host/7748923e-58e6-4db0-bff7-7454e10aa489/L8lGN5kMvc.json",
        width=100,
        height=100,
        repeat=True,
        visible=True,
        scale=ft.Scale(scale=1.2),
    )
    loader_dots   = [
        ft.Container(width=8, height=8, border_radius=ft.BorderRadius.all(4),
                    bgcolor=BG3(), border=ft.Border.all(1, BORDER()))
        for _ in range(6)
    ]

    sticky_loader = ft.Container(
        visible=False,
        bgcolor=BG2(),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        padding=ft.Padding.symmetric(horizontal=24, vertical=15),
        content=ft.Row(
            controls=[
                ft.Container(content=loader_ring, width=60, height=60,
                            bgcolor=BG3(), border_radius=ft.BorderRadius.all(22),
                            alignment=ft.Alignment.CENTER,),
                ft.Column(controls=[loader_label, loader_sub], spacing=2, expand=True),
                ft.Column(controls=[
                    ft.Row(controls=loader_dots, spacing=6, tight=True),
                ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.END),
            ],
            spacing=30,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def build_loading_card(stage):
        if stage < 0:
            sticky_loader.visible = False
            page.update()
            return
        sticky_loader.visible = True
        s = COOKING_STAGES[min(stage, len(COOKING_STAGES)-1)]
        loader_label.value  = s[0]
        loader_sub.value    = s[1]
        loader_ring.visible = stage < 5
        loader_ring.play = stage < 5
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

    def on_search(e):
        async def run_search():
            results_column.controls.clear()

            ingredients = search_field.value.strip()
            if not ingredients:
                return

            build_loading_card(0)
            page.update()

            user_ingredients = [k.strip() for k in ingredients.split(",") if k.strip()]
            loop = asyncio.get_event_loop()

            def on_recipe_found(recipe):
                async def update_ui():
                    n = len(results_column.controls)
                    build_loading_card(min(1 + n, 4))

                    new_card = build_card(recipe)
                    insert_at = len(results_column.controls)
                    for i, ctrl in enumerate(results_column.controls):
                        if recipe["match_score"] > (ctrl.data or 0):
                            insert_at = i
                            break

                    results_column.controls.insert(insert_at, new_card)
                    page.update()
                asyncio.run_coroutine_threadsafe(update_ui(), loop)

            def run():
                CookpadScraper.find_recipe(user_ingredients, on_recipe_found=on_recipe_found)

            await asyncio.get_event_loop().run_in_executor(None, run)

            build_loading_card(-1)
            page.update()

        page.run_task(run_search)
        
        
    def make_click(recipe):
        return lambda e: show_detail(recipe)
    
    def build_card(r):
        score = r.get("match_score", 0)
        score_pct = f"{round(score * 100)}% cocok"
        bg_score, fg_score = ("#1B3D28", GREEN) if score >= 0.8 else \
                            ("#3D2E0A", AMBER) if score >= 0.5 else \
                            ("#3D1A1A", "#C0392B")
                            
        def on_card_click(e):
            # Reset hover state before navigating
            card.bgcolor = BG3()
            card.border  = ft.Border.all(1, BORDER())
            card.update()
            show_detail(r)
        card = ft.Container(
            data=score,
            content=ft.Row(
                controls=[
                    # thumbnail
                    ft.Container(
                        width=90, height=90,
                        border_radius=ft.BorderRadius.all(8),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=ft.Image(
                            src=r.get("image_url", ""),
                            width=90, height=90,
                            fit="cover",
                        ),
                    ),
                    # info
                    ft.Column(
                        controls=[
                            ft.Text(r["name"], color=TEXT(), weight=ft.FontWeight.BOLD, size=15),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=TEXT2(), size=13),
                                ft.Text(r.get("portion", ""), color=TEXT2(), size=12),
                                ft.Text("·", color=TEXT3(), size=12),
                                ft.Icon(ft.Icons.TIMER_OUTLINED, color=TEXT2(), size=13),
                                ft.Text(r.get("cook_time", ""), color=TEXT2(), size=12),
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
                    # right side — score + button
                    ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Text(score_pct, color=fg_score, size=12, weight=ft.FontWeight.BOLD),
                                bgcolor=bg_score,
                                border_radius=ft.BorderRadius.all(20),
                                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            ),
                            ft.OutlinedButton(
                                "Lihat",
                                style=ft.ButtonStyle(color=ORANGE, side=ft.BorderSide(1, ORANGE),mouse_cursor=ft.MouseCursor.CLICK,),
                                on_click=make_click(r),
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
                e.control.update()          
            ),
            on_click=on_card_click,
        )
        return card


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
                        ft.ElevatedButton("Cari", bgcolor=ORANGE, color=WHITE, on_click=on_search,style=ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK,),),
                    ]),
                    padding=ft.Padding.all(20),
                    ink=True,
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
    
    pages["home"]       = make_page("Home")
    pages["my-recipes"] = MyRecipesPage(page, navigate)
    pages["for-you"]    = make_page("For You")
    pages["info"]       = InfoPage(page)
    pages["home"].visible = True

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
        padding=ft.Padding.symmetric(horizontal=40, vertical=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
    )

    # ══════════════════════════════════════════════════════════════════
    #  THEME REBUILD LISTENER
    # ══════════════════════════════════════════════════════════════════
    def rebuild_on_theme_change():
        page.bgcolor    = BG()
        sidebar.bgcolor = BG2()
        topbar.bgcolor  = BG2()
        
        # Force results cards to re-render with new colors
        for ctrl in results_column.controls:
            if isinstance(ctrl, ft.Container):
                ctrl.bgcolor = BG3()
                ctrl.border  = ft.Border.all(1, BORDER())
        
        # Update text colors in results
        def update_colors(ctrl):
            if isinstance(ctrl, ft.Text):
                ctrl.color = TEXT()
            if hasattr(ctrl, 'controls'):
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
            toggle_sidebar(e)
            page.update()

    page.on_resize = window_resized
    page.update()

#gui test standalone
# ft.run(main, assets_dir=".")