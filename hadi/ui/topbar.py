import flet as ft
from rafy.theme import theme_mgr, ORANGE, WHITE


def BG2():    return theme_mgr.get("BG2")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")


PAGE_TITLES = {
    "home":       ("Home",     "Selamat datang di CookD"),
    "finder":     ("Finder",      "Cari resep dari bahan yang kamu punya"),
    "my-recipes": ("My Recipes",  "Resep yang kamu simpan"),
    "for-you":    ("For You",     "Rekomendasi untukmu"),
    "info":       ("Info",        "Informasi aplikasi"),
}


def build_topbar(navigate_fn) -> ft.Container:
    prev_page = {"name": "finder"}

    title_text = ft.Text(
        "Finder",
        size=20,
        color=TEXT(),
        weight=ft.FontWeight.BOLD,
        font_family="Font",
    )

    sub_text = ft.Text(
        "Cari resep dari bahan yang kamu punya",
        size=13,
        color=TEXT2(),
        font_family="Font",
    )

    back_btn_container = ft.Container(
        content=ft.FloatingActionButton(
            icon=ft.Icons.ARROW_BACK_IOS,
            bgcolor=ORANGE,
            foreground_color=WHITE,
            mini=True,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_click=lambda e: navigate_fn(prev_page["name"]),
        ),
        visible=False,
        padding=0,
        margin=ft.Margin.only(right=8),
    )

    container = ft.Container(
        width=float("inf"),
        content=ft.Row(
            controls=[
                back_btn_container,
                ft.Column(
                    controls=[title_text, sub_text],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG2(),
        padding=ft.Padding.only(left=20, right=28, top=14, bottom=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def rebuild():
        container.bgcolor = BG2()
        container.border  = ft.Border.only(bottom=ft.BorderSide(1, BORDER()))
        title_text.color  = TEXT()
        sub_text.color    = TEXT2()
        container.update()
        title_text.update()
        sub_text.update()

    theme_mgr.add_listener(rebuild)

    def set_page(page_name: str):
        prev_page["name"]  = page_name
        t, s               = PAGE_TITLES.get(page_name, (page_name, ""))
        title_text.value   = t
        sub_text.value     = s
        sub_text.visible   = True
        back_btn_container.visible = False
        title_text.update()
        sub_text.update()
        back_btn_container.update()

    def set_recipe(name: str | None):
        if name is None:
            t, s = PAGE_TITLES.get(prev_page["name"], ("CookD", ""))
            title_text.value           = t
            sub_text.value             = s
            sub_text.visible           = True
            back_btn_container.visible = False
        elif name == "":
            title_text.value           = ""
            sub_text.visible           = False
            back_btn_container.visible = True
        else:
            title_text.value           = name
            sub_text.visible           = False
            back_btn_container.visible = True
        title_text.update()
        sub_text.update()
        back_btn_container.update()

    container.set_recipe = set_recipe
    container.set_page   = set_page
    return container