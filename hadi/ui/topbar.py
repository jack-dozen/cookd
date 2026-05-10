import flet as ft
from rafy.theme import theme_mgr,ORANGE,WHITE


def BG2():    return theme_mgr.get("BG2")
def TEXT():   return theme_mgr.get("TEXT")
def BORDER(): return theme_mgr.get("BORDER")


def build_topbar(navigate_fn) -> ft.Container:
    title_text  = ft.Text("CookD", size=20, color=TEXT(), weight=ft.FontWeight.BOLD, font_family="Font")
    sub_text    = ft.Text("Cari resep dari bahan yang kamu punya", size=10, opacity=0.5, color=TEXT())
    
    back_btn_container = ft.Container(
        content=ft.FloatingActionButton(
            icon=ft.Icons.ARROW_BACK_IOS,
            bgcolor=ORANGE,
            foreground_color=WHITE,
            mini=True,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_click=lambda e: navigate_fn("finder"),
        ),
        visible=False,
        padding=0,
    )
    
    container = ft.Container(
        width=float("inf"),
        content=ft.Row(
            controls=[
                back_btn_container,
                ft.Column(
                    controls=[title_text, sub_text],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        bgcolor=BG2(),
        padding=ft.Padding.symmetric(horizontal=20, vertical=15),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def set_recipe(name: str | None):
        if name is None:
            # normal pages
            title_text.value           = "CookD"
            sub_text.visible           = True
            back_btn_container.visible = False
        elif name == "":
            # detail page, not scrolled
            title_text.value           = ""
            sub_text.visible           = False
            back_btn_container.visible = True
        else:
            # detail page, scrolled
            title_text.value           = name
            sub_text.visible           = False
            back_btn_container.visible = True
                
        
    container.set_recipe = set_recipe
    return container
