import flet as ft
from rafy.theme import theme_mgr, ORANGE, ORANGE_GLOW2
from rafy.sidebar import build_sidebar_extras


def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")


def build_sidebar(page: ft.Page, navigate_fn) -> ft.Container:
    state = {"active_index": 1}
    PAGE_NAMES = ["home", "finder", "my-recipes", "for-you", "info"]
    nav_items_ref: list = []
    sidebar_ref: list[ft.Container] = []

    def build_nav_item(icon, label, index):
        is_active = state["active_index"] == index

        icon_obj = ft.Icon(icon, color=ORANGE if is_active else TEXT2(), size=22)
        text_obj = ft.Text(
            value=label,
            color=ORANGE if is_active else TEXT2(),
            size=14,
            weight="w500",
            font_family="Font",
        )

        indicator = ft.Container(
            width=3,
            height=28,
            bgcolor=ORANGE if is_active else ft.Colors.TRANSPARENT,
            border_radius=ft.BorderRadius.only(top_right=4, bottom_right=4),
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        )

        inner = ft.Container(
            content=ft.Row(controls=[icon_obj, text_obj], spacing=13),
            padding=ft.Padding.symmetric(horizontal=14, vertical=11),
            border_radius=10,
            bgcolor=ORANGE_GLOW2 if is_active else ft.Colors.TRANSPARENT,
            expand=True,
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            scale=ft.Scale(scale=1.0),
        )

        def on_hover(e):
            if state["active_index"] == index:
                return
            is_hovered = e.data
            icon_obj.color = ORANGE if is_hovered else TEXT2()
            text_obj.color = ORANGE if is_hovered else TEXT2()
            inner.bgcolor  = BG3() if is_hovered else ft.Colors.TRANSPARENT
            icon_obj.update()
            text_obj.update()
            inner.update()

        async def on_click(e):
            import asyncio
            inner.scale = ft.Scale(scale=0.95)
            inner.update()
            await asyncio.sleep(0.08)
            inner.scale = ft.Scale(scale=1.0)
            inner.update()
            state["active_index"] = index
            _update_highlights()
            navigate_fn(PAGE_NAMES[index - 1])

        row = ft.Container(
            content=ft.Row(
                controls=[indicator, inner],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_hover=on_hover,
            on_click=on_click,
        )

        nav_items_ref.append({
            "index":     index,
            "indicator": indicator,
            "inner":     inner,
            "icon":      icon_obj,
            "text":      text_obj,
        })

        return row

    def _update_highlights():
        for item in nav_items_ref:
            is_active = state["active_index"] == item["index"]
            item["indicator"].bgcolor = ORANGE if is_active else ft.Colors.TRANSPARENT
            item["inner"].bgcolor     = ORANGE_GLOW2 if is_active else ft.Colors.TRANSPARENT
            item["icon"].color        = ORANGE if is_active else TEXT2()
            item["text"].color        = ORANGE if is_active else TEXT2()
            item["indicator"].update()
            item["inner"].update()
            item["icon"].update()
            item["text"].update()

    def toggle_sidebar(e=None):
        sidebar = sidebar_ref[0]
        is_collapsing = sidebar.width == 200
        sidebar.width = 60 if is_collapsing else 200
        logo_text.visible = not is_collapsing
        logo_text.update()
        for item in nav_items_ref:
            item["text"].visible = not is_collapsing
            item["text"].update()
        for ctrl in sidebar.content.controls:
            content = getattr(ctrl, "content", None)
            if isinstance(content, ft.Row):
                for c in content.controls:
                    if isinstance(c, ft.Text):
                        c.visible = not is_collapsing
                        c.update()
        page.update()

    def rebuild():
        sidebar = sidebar_ref[0]
        sidebar.bgcolor = BG2()
        sidebar.border  = ft.Border.only(right=ft.BorderSide(1, BORDER()))
        for item in nav_items_ref:
            is_active = state["active_index"] == item["index"]
            item["icon"].color    = ORANGE if is_active else TEXT2()
            item["text"].color    = ORANGE if is_active else TEXT2()
            item["inner"].bgcolor = ORANGE_GLOW2 if is_active else ft.Colors.TRANSPARENT
            item["icon"].update()
            item["text"].update()
            item["inner"].update()
        logo_text.color = TEXT()
        logo_text.update()
        sidebar.update()

    theme_mgr.add_listener(rebuild)

    logo_icon = ft.Container(
        content=ft.Icon(ft.Icons.MENU, color=TEXT2(), size=22),
        padding=ft.Padding.all(4),
    )

    logo_text = ft.Text(
        "CookD",
        size=17,
        weight=ft.FontWeight.BOLD,
        color=TEXT(),
        font_family="Font",
    )

    logo_row = ft.Container(
        content=ft.Row(controls=[logo_icon, logo_text], spacing=10),
        padding=ft.Padding.symmetric(horizontal=14, vertical=14),
        border_radius=10,
        bgcolor=ft.Colors.TRANSPARENT,
        on_hover=lambda e: (
            setattr(e.control, "bgcolor", BG3() if e.data else ft.Colors.TRANSPARENT),
            e.control.update(),
        ),
        on_click=toggle_sidebar,
    )

    sidebar = ft.Container(
        width=200,
        bgcolor=BG2(),
        border=ft.Border.only(right=ft.BorderSide(1, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            controls=[
                logo_row,
                ft.Container(height=4),
                build_nav_item(ft.Icons.HOME_OUTLINED,   "Home",       1),
                build_nav_item(ft.Icons.SEARCH_OUTLINED, "Finder",     2),
                build_nav_item(ft.Icons.BOOK_OUTLINED,   "My Recipes", 3),
                build_nav_item(ft.Icons.STAR_OUTLINE,    "For You",    4),
                build_nav_item(ft.Icons.INFO_OUTLINE,    "Info",       5),
                *build_sidebar_extras(page),
            ],
            spacing=3,
            expand=True,
        ),
    )

    sidebar_ref.append(sidebar)
    sidebar.toggle_sidebar = toggle_sidebar
    return sidebar
