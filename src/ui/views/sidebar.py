"""
sidebar.py — CookD Sidebar (formerly hadi/ui/sidebar.py)
"""

import flet as ft
import asyncio
from src.core.theme import theme_mgr, ORANGE, ORANGE_GLOW2
from src.ui.components.sidebar_extras import build_sidebar_extras


def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")


def _active_gradient():
    return ft.LinearGradient(
        begin=ft.Alignment(-1, 0),
        end=ft.Alignment(1, 0),
        colors=["#40ff7a06", "#00ff7a06"],
        stops=[0.0, 0.5],
    )


def _sidebar_gradient():
    return ft.LinearGradient(
        begin=ft.Alignment(0, -1),
        end=ft.Alignment(0, 1),
        colors=[BG(), BG2(), BG()],
        stops=[0.0, 0.5, 1.0],
    )


def build_sidebar(page: ft.Page, navigate_fn, on_import_done=None) -> ft.Container:
    state = {"active_index": 1}
    PAGE_NAMES = ["home", "finder", "my-recipes", "for-you", "info"]
    nav_items_ref: list = []
    sidebar_ref: list[ft.Container] = []
    _sidebar_extras_ref: list = []

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
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

        inner = ft.Container(
            content=ft.Row(controls=[icon_obj, text_obj], spacing=13),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            margin=ft.Margin.only(right=3),
            border_radius=ft.BorderRadius.all(10),
            gradient=_active_gradient() if is_active else None,
            bgcolor=None if is_active else ft.Colors.TRANSPARENT,
            expand=True,
            scale=ft.Scale(scale=1.0),
        )

        def on_hover(e):
            if state["active_index"] == index:
                return
            is_hovered = e.data
            icon_obj.color = ORANGE if is_hovered else TEXT2()
            text_obj.color = ORANGE if is_hovered else TEXT2()
            inner.bgcolor  = BG3() if is_hovered else ft.Colors.TRANSPARENT
            inner.gradient = None
            icon_obj.update()
            text_obj.update()
            inner.update()

        async def on_click(e):
            state["active_index"] = index
            _update_highlights()
            navigate_fn(PAGE_NAMES[index - 1])

            inner.scale = ft.Scale(scale=0.93)
            inner.update()
            await asyncio.sleep(0.07)
            inner.scale = ft.Scale(scale=1.04)
            inner.update()
            await asyncio.sleep(0.07)
            inner.scale = ft.Scale(scale=1.0)
            inner.update()

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
            item["indicator"].bgcolor  = ORANGE if is_active else ft.Colors.TRANSPARENT
            item["inner"].gradient     = _active_gradient() if is_active else None
            item["inner"].bgcolor      = None if is_active else ft.Colors.TRANSPARENT
            item["icon"].color         = ORANGE if is_active else TEXT2()
            item["text"].color         = ORANGE if is_active else TEXT2()
            item["indicator"].update()
            item["inner"].update()
            item["icon"].update()
            item["text"].update()

    def toggle_sidebar(e=None):
        sidebar = sidebar_ref[0]
        is_collapsing = sidebar.width == 200
        sidebar.width = 57 if is_collapsing else 200
        logo_text.visible = not is_collapsing
        logo_text.update()
        for item in nav_items_ref:
            item["text"].visible = not is_collapsing
            item["text"].update()

            if is_collapsing:
                item["inner"].expand = False
                item["inner"].width = sidebar.width - 8
                item["inner"].padding = ft.Padding.symmetric(vertical=10)
                item["inner"].content.alignment = ft.MainAxisAlignment.CENTER
                logo_text.visible = False
                logo.expand = False
                logo.width = sidebar.width - 8
                logo.content.alignment = ft.MainAxisAlignment.CENTER
            else:
                item["inner"].expand = True
                item["inner"].width = None
                item["inner"].padding = ft.Padding.only(left=13.5, right=3, top=10, bottom=10)
                item["inner"].content.alignment = ft.MainAxisAlignment.START
                logo_text.visible = True
                logo.width = None
                logo.expand = True
                logo.content.alignment = ft.MainAxisAlignment.START
            item["inner"].update()
            logo_row.update()

        for item in _sidebar_extras_ref:
            item["text"].opacity = 0.0 if is_collapsing else 1.0
            item["text"].update()
            if item.get("switch"):
                item["switch"].visible = not is_collapsing
                item["switch"].update()
        page.update()

    def rebuild():
        sidebar = sidebar_ref[0]
        sidebar.gradient = _sidebar_gradient()
        sidebar.border   = ft.Border.only(right=ft.BorderSide(1, BORDER()))
        for item in nav_items_ref:
            is_active = state["active_index"] == item["index"]
            item["icon"].color     = ORANGE if is_active else TEXT2()
            item["text"].color     = ORANGE if is_active else TEXT2()
            item["inner"].gradient = _active_gradient() if is_active else None
            item["inner"].bgcolor  = None if is_active else ft.Colors.TRANSPARENT
            item["icon"].update()
            item["text"].update()
            item["inner"].update()
        sidebar.update()

    theme_mgr.add_listener(rebuild)

    logo_icon = ft.Container(
        content=ft.Icon(ft.Icons.MENU, color=TEXT2(), size=22),
    )

    def _rebuild_logo():
        logo_icon.content.color = TEXT2()
        logo_icon.content.update()

    theme_mgr.add_listener(_rebuild_logo)

    logoHeight = 28
    logo_text = ft.Image(
        src="assets/Cookd-text.png",
        height=logoHeight,
    )
    logo = ft.Container(
        content=ft.Row(controls=[logo_icon, logo_text]),
        height=50,
        border_radius=ft.BorderRadius.all(10),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        margin=ft.Margin.only(right=3),
        bgcolor=ft.Colors.TRANSPARENT,
        expand=True,
    )

    def logo_hover(e):
        is_hovered = e.data
        logo_icon.color = ORANGE if is_hovered else TEXT2()
        logo.bgcolor = BG3() if is_hovered else ft.Colors.TRANSPARENT
        logo.update()

    logo_row = ft.Container(
        content=ft.Row(controls=[ft.Container(width=3), logo], spacing=0),
        on_hover=logo_hover,
        on_click=toggle_sidebar,
    )
    _extras = build_sidebar_extras(page, on_import_done=on_import_done)

    import_btn = _extras[1]
    try:
        import_label = next(c for c in import_btn.content.controls if isinstance(c, ft.Text))
    except Exception:
        import_label = None

    theme_toggle = _extras[2]
    toggle_label  = getattr(theme_toggle, "_label_text", None)
    toggle_switch = getattr(theme_toggle, "_switch", None)

    if import_label:
        _sidebar_extras_ref.append({"text": import_label, "switch": None})
    if toggle_label:
        _sidebar_extras_ref.append({"text": toggle_label, "switch": toggle_switch})

    sidebar = ft.Container(
        width=200,
        gradient=_sidebar_gradient(),
        border=ft.Border.only(right=ft.BorderSide(1, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            controls=[
                ft.Container(height=4),
                logo_row,
                ft.Container(height=2),
                build_nav_item(ft.Icons.HOME_OUTLINED,   "Home",       1),
                build_nav_item(ft.Icons.SEARCH_OUTLINED, "Finder",     2),
                build_nav_item(ft.Icons.BOOK_OUTLINED,   "My Recipes", 3),
                build_nav_item(ft.Icons.STAR_OUTLINE,    "For You",    4),
                build_nav_item(ft.Icons.INFO_OUTLINE,    "Info",       5),
                *_extras,
            ],
            spacing=1,
            expand=True,
        ),
    )

    sidebar_ref.append(sidebar)

    sidebar.toggle_sidebar = toggle_sidebar

    def set_active(name: str):
        if name in PAGE_NAMES:
            state["active_index"] = PAGE_NAMES.index(name) + 1
            _update_highlights()

    sidebar.set_active = set_active

    return sidebar
