import flet as ft


# ─────────────────────────────────────────────────────────────────────
# COLORS  (mirrors CSS :root variables)
# ─────────────────────────────────────────────────────────────────────
BG     = "#1A1A1A"
BG2    = "#242424"
BG3    = "#2E2E2E"
BG4    = "#363636"
TEXT   = "#F0F0EC"
TEXT2  = "#B0B0AB"
TEXT3  = "#707070"
ORANGE = "#E8440A"
BORDER = "#000000"
GREEN  = "#2E9E5B"
AMBER  = "#E09020"
BLUE   = "#1A6FBF"


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
    page.scroll           = ft.ScrollMode.HIDDEN
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

    def navigate(name: str):
        for key, container in pages.items():
            container.visible = (key == name)
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


    # ── ft.NavigationRail ─────────────────────────────────────────────
    def toggle_sidebar(e):
        if sidebar.visible == True:
            sidebar.visible = False
            sidebarOff.visible = True
        else :
            sidebar.visible = True
            sidebarOff.visible = False
        page.update()
    
    def nav_handle(e):
        index = e.control.selected_index
        if e.control.selected_index == 0:
            toggle_sidebar(e)
            e.control.selected_index = 1 
        else:
            paths = ["menu", "home", "finder", "my-recipes", "for-you", "info"]
            navigate(paths[index])
    
        e.control.update()
        
    navOff = ft.NavigationRail(
        width=75,                
        height=page.window_height,
        selected_index     = None,
        extended           = True,
        bgcolor            = BG2,
        label_type         = ft.NavigationRailLabelType.ALL,
        indicator_color=ft.Colors.TRANSPARENT,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.MENU,
                label=""
            ),
        ],
        on_change=toggle_sidebar,
    )
    
    nav = ft.NavigationRail(
        width=200,                
        height=page.window_height,
        extended           = True,
        selected_index     = 1,
        bgcolor            = BG2,
        label_type         = ft.NavigationRailLabelType.ALL,
        indicator_color    = ORANGE,
        selected_label_text_style=ft.TextStyle(color=ORANGE),
        unselected_label_text_style=ft.TextStyle(color=TEXT2),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.MENU_OUTLINED,
                selected_icon=ft.Icons.MENU,
                label=""
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label="Home"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SEARCH_OUTLINED,
                selected_icon=ft.Icons.SEARCH,
                label="Finder"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BOOK_OUTLINED,
                selected_icon=ft.Icons.BOOK,
                label="My Recipes"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.STAR_OUTLINE,
                selected_icon=ft.Icons.STAR,
                label="For You"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INFO_OUTLINE,
                selected_icon=ft.Icons.INFO,
                label="Info"
            ),
        ],
        
        on_change=nav_handle,
        
    )
    
    sidebar = ft.Container(
        content=nav,
        animate_size=300,
    )
    sidebarOff = ft.Container(
        content=navOff,
        visible=False,
        animate_size=300,
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
                            controls = [
                            ft.Text(label, size=20, color=TEXT, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.LEFT, expand=True,font_family="Font"),
                            ft.Text(f"Cari resep dari bahan yang kamu punya", size=10,opacity = 0.5, color=TEXT, text_align=ft.TextAlign.LEFT, expand=True),
                            ],
                            spacing=0,
                        ),
                        
                        alignment=ft.Alignment.CENTER_LEFT,
                        bgcolor = BG2,
                        padding = ft.Padding.symmetric(horizontal=40 , vertical=14),
                        border  = ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
                    ),
                    ft.Container(
                        content = ft.Column(
                            controls =[
                            ft.Text(f"Work In Progress", color=TEXT2,font_family="Font",weight=ft.FontWeight.BOLD),
                            ft.Text(f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras condimentum, lorem nec porttitor tincidunt, felis lorem egestas odio, ac dignissim velit justo sed sapien. Donec bibendum odio ac ex facilisis, eget interdum justo mollis. Maecenas vestibulum, ipsum quis faucibus hendrerit, nulla orci varius magna, quis efficitur odio neque eget purus. Nunc dolor velit, volutpat vulputate erat vel, mattis tempus ipsum. Vivamus nec interdum neque. Praesent eleifend nunc enim, quis molestie ante ornare non. Duis in tellus diam. Aenean eleifend varius felis in volutpat. Aliquam a urna felis.", color=TEXT2,font_family="Font"),
                            ],
                            spacing=10,
                        ),
                        padding = ft.Padding.all(24),
                    ),
                ],
                spacing=0,
            ),
        )

    pages["home"] = make_page("Home")
    pages["finder"] = make_page("Finder")
    pages["my-recipes"] = make_page("My Recipes")
    pages["for-you"] = make_page("For You")
    pages["info"] = make_page("Info")

    pages["home"].visible = True


    # ── ROOT / Main ──────────────────────────────────────────────────────────
    root = ft.Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar,
            sidebarOff,
            ft.VerticalDivider(width=1, color=BORDER),
            ft.Container(
                expand=True,
                height=page.window_height,
                content=ft.Stack(list(pages.values())),
            ),
        ],
    )

    page.add(root)
    
    def window_resized(e):
        width = e.width

        #print("WIDTH:", width)  

        if width < 800:
            sidebar.visible = False
            sidebarOff.visible = True
        else:
            if sidebar.visible != True:
                sidebar.visible = True
                sidebarOff.visible = False

        page.update()

    page.on_resize = window_resized

    # run once at start
    #on_resize(None)


ft.run(main, assets_dir=".")