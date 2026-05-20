import flet as ft
import os
import sys
from rafy.theme import ORANGE_GLOW, theme_mgr, ORANGE, WHITE


def BG2():    return theme_mgr.get("BG2")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")

#navigation windows
def _win_btn(icon, hover_color, on_click_fn):
    ico = ft.Icon(icon, size=18, color="#555555")
    
    def on_hover(e):
        ico.color = hover_color if e.data == "true" else "#555555"
        ico.update()

    return ft.GestureDetector(
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=on_click_fn,
        on_enter=lambda e: (setattr(ico, 'color', hover_color), ico.update()),
        on_exit=lambda e: (setattr(ico, 'color', '#555555'), ico.update()),
        content=ft.Container(
            content=ico,
            width=32,
            height=32,
            alignment=ft.Alignment.CENTER,
            border_radius=6,
            ink=True,
            ink_color="#ff660017",
        ),
    )



PAGE_TITLES = {
    "home":       ("Home"),
    "finder":     ("Finder"),
    "my-recipes": ("My Recipes"),
    "for-you":    ("For You"),
    "info":       ("Info"),
}


def _topbar_gradient():
    return ft.LinearGradient(
        begin=ft.Alignment(-1, 0),
        end=ft.Alignment(1, 0),
        colors=["#18f04f23", "#08f04f23", BG2()],
        stops=[0.0, 0.3, 1.0],
    )


def build_topbar(navigate_fn, page) -> ft.Container:
    win_buttons = ft.Row(
        controls=[
            _win_btn(ft.Icons.REMOVE,      "#aaaaaa", lambda _: setattr(page.window, 'minimized', True)),
            _win_btn(ft.Icons.CROP_SQUARE_ROUNDED, "#aaaaaa", lambda _: setattr(page.window, 'maximized', not page.window.maximized)),
            _win_btn(ft.Icons.CLOSE_SHARP,       "#ff3700", lambda _: page.run_task(page.window.close)),
        ],
        spacing=4,
    )
    
    prev_page = {"name": "finder"}

    title_text = ft.Text(
        "Finder",
        size=16,
        color=TEXT(),
        weight=ft.FontWeight.W_700,
        font_family="Font",
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )



    back_icon = ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, color=TEXT(), size=20)
    back_btn_container = ft.Container(
        content=ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e: navigate_fn(prev_page["name"]),
            content=back_icon,
        ),
        visible=False,
        padding=ft.Padding.all(4),
        margin=ft.Margin.only(right=4),
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        on_hover=lambda e: (
            setattr(back_icon, "color", ORANGE if e.data else TEXT()),
            back_icon.update(),
        ),
    )

    container = ft.Container(
        width=float("inf"),
        height=40,
        content= ft.Stack(
            controls=[ 
                ft.Row(
                    controls=[
                        back_btn_container,
                        title_text,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    margin=ft.Margin.only(left=5),
                    expand=True,
                ),
                ft.Row(
                    controls=[
                        win_buttons,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        ),
        gradient=_topbar_gradient(),
        padding=ft.Padding.only(left=10, right=5, top=6, bottom=6),
        border=ft.Border.only(bottom=ft.BorderSide(0.5, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def rebuild():
        container.gradient = _topbar_gradient()
        title_text.color   = TEXT()
        back_icon.color    = TEXT()
        container.update()
        title_text.update()
        back_icon.update()

    theme_mgr.add_listener(rebuild)

    def set_page(page_name: str):
        prev_page["name"]          = page_name
        t                          = PAGE_TITLES.get(page_name)
        title_text.value           = t
        back_btn_container.visible = False
        title_text.expand          = True
        title_text.text_align      = ft.TextAlign.CENTER 
        title_text.update()
        back_btn_container.update()
        container.update()

    def set_recipe(name: str | None):
        back_icon.color = TEXT()
        back_icon.update()
        if name is None:
            t = PAGE_TITLES.get(prev_page["name"], ("CookD", ""))
            title_text.value           = t
            back_btn_container.visible = False
            title_text.expand          = False
            title_text.text_align      = ft.TextAlign.CENTER 
        elif name == "":
            title_text.value           = ""
            back_btn_container.visible = True
            title_text.expand          = False
            title_text.text_align      = ft.TextAlign.CENTER 
        else:
            title_text.value           = name
            title_text.expand          = True
            title_text.text_align      = ft.TextAlign.CENTER
            back_btn_container.visible = True
        title_text.update()
        back_btn_container.update()
        container.update()

    container.set_recipe = set_recipe
    container.set_page   = set_page
    return container