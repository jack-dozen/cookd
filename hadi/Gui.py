import flet as ft
import json
from hadi import CookpadScraper  
import threading
import subprocess
from fadhil.my_recipes import MyRecipesPage



# ─────────────────────────────────────────────────────────────────────
# COLORS  (mirrors CSS :root variables)
# ─────────────────────────────────────────────────────────────────────
BG     = "#141414"
BG2    = "#303030"
BG3    = "#252525"
BG4    = "#363636"
TEXT   = "#F0F0EC"
TEXT2  = "#B0B0AB"
TEXT3  = "#707070"
ORANGE = "#E8440A"
BORDER = "#000000"
GREEN  = "#2E9E5B"
AMBER  = "#E09020"
BLUE   = "#1A6FBF"
BLACK  = "#000000"
WHITE  = "#FFFFFF"


def main(page: ft.Page):

    # ══════════════════════════════════════════════════════════════════
    #  PAGE
    # ══════════════════════════════════════════════════════════════════
    page.title            = "CookD"
    page.bgcolor          = BG
    page.padding          = 0
    page.window_height    = 1200
    page.window_height    = 720
    page.window.min_width = 400
    page.window.min_height = 300
    page.window_resizable = True
    page.theme_mode       = ft.ThemeMode.DARK
    page.scroll           = None
    page.window_resizable = True
    page.fonts = {
        "Font": "fonts/Poppins-Regular.ttf",
    }

    page.theme = ft.Theme(font_family="Font")
    page.update()
    # ══════════════════════════════════════════════════════════════════
    #  NAVIGATION
    # ══════════════════════════════════════════════════════════════════
    pages: dict[str, ft.Container] = {}

    def show_detail(recipe: dict):
        """Fill detail page with this recipe's data then navigate to it."""
        detail_content.controls.clear()

        # Title
        detail_content.controls.append(
            ft.Text(recipe["name"], size=24, weight=ft.FontWeight.BOLD, color=TEXT)
        )

        # Steps — assumes json has "steps": ["step1", "step2", ...]
        for i, step in enumerate(recipe["steps"], start=1):
            detail_content.controls.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(str(i), color="#fff", size=12, weight=ft.FontWeight.BOLD),
                            width=26, height=26,
                            bgcolor=ORANGE,
                            border_radius=ft.BorderRadius.all(13),
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Text(step, color=TEXT2, expand=True),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )

        detail_content.update()
        navigate("detail")

    def navigate(name: str, recipe: dict = None):
        for key, container in pages.items():
            container.visible = (key == name)
        if name == "detail" and recipe:
            show_detail(recipe)
        page.update()


    # ── ft.Container ──────────────────────────────────────────────────
    _ = ft.Container(
        content       = ft.Text("inside"),
        width         = 300,
        height        = 80,
        expand        = True,
        padding       = ft.Padding.all(16),
        margin        = ft.Margin.only(bottom=8),
        bgcolor       = BG3,
        border        = ft.Border.all(1, BORDER),
        border_radius = ft.BorderRadius.all(10),
        gradient      = ft.LinearGradient(
            begin  = ft.Alignment(0, 1),
            end    = ft.Alignment(0, -1),
            colors = ["#CC000000", "#00000000"],
        ),
    )


    # ── ft.Stack ──────────────────────────────────────────────────────
    _ = ft.Stack(
        controls = [
            ft.Image(
                src="https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=600&q=70",
                fit="cover", width=600, height=220,
            ),
            ft.Container(bgcolor="#88000000", width=600, height=220),
            ft.Container(
                content = ft.Text("Rendang", color="#fff", size=22),
                bottom  = 0,
                left    = 0,
                right   = 0,
                padding = ft.Padding.all(20),
            ),
        ],
        width=600, height=220,
    )


    # ── ft.TextField ──────────────────────────────────────────────────
    _ = ft.TextField(
        hint_text            = "cth: bawang putih, tomat, garam...",
        bgcolor              = BG3,
        color                = TEXT,
        border_color         = BORDER,
        focused_border_color = ORANGE,
        content_padding      = ft.Padding.symmetric(horizontal=16, vertical=0),
    )


    # ── ft.ElevatedButton ─────────────────────────────────────────────
    _ = ft.Button(
        content  = "Cari Resep",
        icon     = "search",
        bgcolor  = ORANGE,
        color    = "#FFFFFF",
        style    = ft.ButtonStyle(
            shape   = ft.RoundedRectangleBorder(radius=24),
            padding = ft.Padding.symmetric(horizontal=20, vertical=12),
        ),
    )


    # ── Sidebar ─────────────────────────────────────────────
    state = {"active_index": 1}
    def build_nav_item(icon, label, index):
        icon_obj = ft.Icon(icon, color=ORANGE if state["active_index"] == index else TEXT2, size=24)
        text_obj = ft.Text(value=label, color=ORANGE if state["active_index"] == index else TEXT2, size=15, weight="w500")
        
        def on_hover(e):
            if state["active_index"] == index:
                return
            
            is_hovered = e.data
            icon_obj.color = ORANGE if is_hovered else TEXT2
            text_obj.color = ORANGE if is_hovered else TEXT2
            e.control.bgcolor = BG3 if is_hovered else ft.Colors.TRANSPARENT
            
            icon_obj.update()
            text_obj.update()
            e.control.update()

        def on_click(e):
            state["active_index"] = index
            update_highlights() 
            navigate(["home", "finder", "my-recipes", "for-you", "info"][index - 1])

        container = ft.Container(
            content=ft.Row(controls=[icon_obj, text_obj], spacing=15),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=10,
            bgcolor=BG3 if state["active_index"] == index else ft.Colors.TRANSPARENT, # Initial highlight
            on_hover=on_hover,
            on_click=on_click,
        )
        return container
            
    def update_highlights():
        for i in range(2, len(sidebar.content.controls)):
            item = sidebar.content.controls[i]
            if isinstance(item, ft.Container) and isinstance(item.content, ft.Row):
                btn_index = i - 1 
                is_active = state["active_index"] == btn_index
                
                item.bgcolor = BG3 if is_active else ft.Colors.TRANSPARENT
                item.content.controls[0].color = ORANGE if is_active else TEXT2 
                item.content.controls[1].color = ORANGE if is_active else TEXT2 
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
        bgcolor=BG2,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.MENU, color=TEXT2),
                    padding=15,
                    border_radius=10,
                    bgcolor=ft.Colors.TRANSPARENT,
                    on_hover=lambda e: (
                        setattr(e.control, "bgcolor", BG3 if e.data else ft.Colors.TRANSPARENT),
                        e.control.update()
                    ),
                    on_click=toggle_sidebar
                ),
                ft.Divider(height=1, color="transparent"),
                build_nav_item(ft.Icons.HOME_OUTLINED, "Home", 1),
                build_nav_item(ft.Icons.SEARCH_OUTLINED, "Finder", 2),
                build_nav_item(ft.Icons.BOOK_OUTLINED, "My Recipes", 3),
                build_nav_item(ft.Icons.STAR_OUTLINE, "For You", 4),
                build_nav_item(ft.Icons.INFO_OUTLINE, "Info", 5),
            ],
            spacing=5,
        )
    )





    # ── ft.SnackBar ───────────────────────────────────────────────────
    snack = ft.SnackBar(
        content  = ft.Text("Saved", color=GREEN),
        bgcolor  = BG3,
        duration = 3000,
    )


    # ── PAGES ─────────────────────────────────────────────────────────
    def make_page(label: str) -> ft.Container:
        return ft.Container(
            animate_size=300,
            expand  = True,
            bgcolor = BG,
            visible = False,
            content = ft.Column(
                controls=[
                    ft.Container(
                        content = ft.Column(
                            controls =[
                            ft.Text(f"Work In Progress", color=TEXT2,font_family="Font",weight=ft.FontWeight.BOLD),
                            ft.Text(f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras condimentum, lorem nec porttitor tincidunt, felis lorem egestas odio, ac dignissim velit justo sed sapien. Donec bibendum odio ac ex facilisis, eget interdum justo mollis. Maecenas vestibulum, ipsum quis faucibus hendrerit, nulla orci varius magna, quis efficitur odio neque eget purus. Nunc dolor velit, volutpat vulputate erat vel, mattis tempus ipsum. Vivamus nec interdum neque. Praesent eleifend nunc enim, quis molestie ante ornare non. Duis in tellus diam. Aenean eleifend varius felis in volutpat. Aliquam a urna felis.", color=TEXT2,font_family="Font"),
                            ],
                            spacing=0,
                        ),
                        padding = ft.Padding.all(24),
                    ),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    pages["home"] = make_page("Home")
    pages["my-recipes"] = MyRecipesPage(page, navigate)
    pages["for-you"] = make_page("For You")
    pages["info"] = make_page("Info")

    pages["home"].visible = True


    # ── Result cards ──
    results_column = ft.Column(
        controls=[],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # ── Detail page content (reuse pages["detail"]) ──
    detail_content = ft.Column(
        controls=[],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    pages["detail"] = ft.Container(
        expand=True,
        bgcolor=BG,
        visible=False,
        content=ft.Column(
            controls=[
                # back button
                ft.TextButton(
                    "← Back",
                    on_click=lambda e: navigate("finder"),
                    style=ft.ButtonStyle(color=ORANGE),
                ),
                detail_content,  # filled dynamically on card click
            ],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )


    def on_search(e):
        def run():
            ingredients = search_field.value.strip()
            if not ingredients:
                return

            # show loading
            results_column.controls.clear()
            results_column.controls.append(ft.ProgressRing(color=ORANGE))
            results_column.update()

            # run scraper as separate process, pass ingredients as argument
            subprocess.run(["python", "./hadi/CookpadScraper.py", ingredients], cwd=".")

            # read the json it produced
            try:
                with open(CookpadScraper.OUTPUT_FILE, "r", encoding="utf-8") as f:
                    results = json.load(f)
            except FileNotFoundError:
                results_column.controls.clear()
                results_column.controls.append(ft.Text("File not found", color="red"))
                results_column.update()
                return

            # build cards
            results_column.controls.clear()
            for r in results:
                def make_click(recipe):
                    return lambda e: show_detail(recipe)
                results_column.controls.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(r["name"], color=TEXT, weight=ft.FontWeight.BOLD, size=15),
                                ft.Text(r.get("portion", ""), color=TEXT2, size=12),
                                ft.Text(r.get("author", ""), color=TEXT2, size=12),
                                ft.Text(r.get("cook_time", ""), color=TEXT2, size=12),
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
                        bgcolor=BG3,
                        border_radius=10,
                        padding=ft.padding.all(14),
                        border=ft.Border.all(1, BORDER),
                        ink=True,
                        on_click=make_click(r),
                    )
                )
            results_column.update()

        threading.Thread(target=run).start()

    search_field = ft.TextField(
        hint_text="cth: bawang putih, tomat...",
        bgcolor=BG3,
        color=TEXT,
        expand=True,
        on_submit=on_search,
    )

    pages["finder"] = ft.Container(
        expand=True,
        bgcolor=BG,
        visible=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(controls=[
                        search_field,
                        ft.ElevatedButton("Cari", bgcolor=ORANGE, color="#fff", on_click=on_search),
                    ]),
                    padding=ft.padding.all(20),
                ),
                results_column,
            ],
            spacing=0,
            expand=True,
        ),
    )








    #──Top Bar ─────────────────────────────────────────────────────
    topbar = ft.Container(
        width=float("inf"),
        content=ft.Column(
            controls=[
                ft.Text("CookD", size=20, color=TEXT, weight=ft.FontWeight.BOLD, font_family="Font"),
                ft.Text("Cari resep dari bahan yang kamu punya", size=10, opacity=0.5, color=TEXT),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=BG2,
        padding=ft.padding.symmetric(horizontal=40, vertical=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
    )

    # ── ROOT / Main ──────────────────────────────────────────────────────────
    page.padding = ft.padding.all(0)
    root = ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            sidebar,
            ft.VerticalDivider(width=1, color=BORDER),
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
        width = e.width

        #print("WIDTH:", width)  

        if width < 800:
            toggle_sidebar(e)
            page.update()

    page.on_resize = window_resized
    page.update()
    # run once at start
    #on_resize(None)


#ft.run(main, assets_dir=".")