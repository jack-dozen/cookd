import flet as ft
from rafy.theme import ORANGE_GLOW, theme_mgr, ORANGE, WHITE


def BG2():    return theme_mgr.get("BG2")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def BORDER(): return theme_mgr.get("BORDER")


PAGE_TITLES = {
    "home":       ("Home",        "Selamat datang di CookD"),
    "finder":     ("Finder",      "Cari resep dari bahan yang kamu punya"),
    "my-recipes": ("My Recipes",  "Resep yang kamu simpan"),
    "for-you":    ("For You",     "Rekomendasi untukmu"),
    "info":       ("Info",        "Informasi aplikasi"),
}


def _topbar_gradient():
    return ft.LinearGradient(
        begin=ft.Alignment(-1, 0),
        end=ft.Alignment(1, 0),
        colors=["#22ff6a20", "#0aff6a20", BG2()],
        stops=[0.0, 0.25, 1.0],
    )


def build_topbar(navigate_fn) -> ft.Container:
    prev_page = {"name": "finder"}

    title_text = ft.Text(
        "Finder",
        size=22,
        color=TEXT(),
        weight=ft.FontWeight.BOLD,
        font_family="Font",
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    sub_text = ft.Text(
        "Cari resep dari bahan yang kamu punya",
        size=12,
        color=TEXT2(),
        font_family="Font",
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    back_icon = ft.Icon(ft.Icons.ARROW_BACK_IOS, color=TEXT(), size=28)
    back_btn_container = ft.Container(
        content=ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e: navigate_fn(prev_page["name"]),
            content=back_icon,
        ),
        visible=False,
        padding=ft.Padding.all(4),
        margin=ft.Margin.only(left=10),
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        on_hover=lambda e: (
            setattr(back_icon, "color", ORANGE if e.data else TEXT()),
            back_icon.update(),
        ),
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
        gradient=_topbar_gradient(),
        padding=ft.Padding.only(left=20, right=28, top=14, bottom=14),
        border=ft.Border.only(bottom=ft.BorderSide(0.5, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def rebuild():
        container.gradient = _topbar_gradient()
        container.border   = ft.Border.only(bottom=ft.BorderSide(0.5, BORDER()))
        title_text.color   = TEXT()
        sub_text.color     = TEXT2()
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
        back_icon.color = TEXT()
        back_icon.update()
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