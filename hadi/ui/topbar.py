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
        colors=["#18f04f23", "#08f04f23", BG2()],
        stops=[0.0, 0.3, 1.0],
    )


def build_topbar(navigate_fn) -> ft.Container:
    prev_page = {"name": "finder"}

    title_text = ft.Text(
        "Finder",
        size=20,
        color=TEXT(),
        weight=ft.FontWeight.W_600,
        font_family="Font",
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    dot_sep = ft.Text("·", size=20, color=TEXT2())

    sub_text = ft.Text(
        "Cari resep dari bahan yang kamu punya",
        size=10,
        color=TEXT2(),
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
        content=ft.Row(
            controls=[
                back_btn_container,
                title_text,
                dot_sep,
                ft.Container(content=sub_text,margin=ft.Margin.only(top=4)),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        gradient=_topbar_gradient(),
        padding=ft.Padding.only(left=20, right=28, top=15, bottom=15),
        border=ft.Border.only(bottom=ft.BorderSide(0.5, BORDER())),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    def rebuild():
        container.gradient = _topbar_gradient()
        container.border   = ft.Border.only(bottom=ft.BorderSide(0.5, BORDER()))
        title_text.color   = TEXT()
        sub_text.color     = TEXT2()
        dot_sep.color      = TEXT2()
        back_icon.color    = TEXT()
        container.update()
        title_text.update()
        sub_text.update()
        dot_sep.update()
        back_icon.update()

    theme_mgr.add_listener(rebuild)

    def set_page(page_name: str):
        prev_page["name"]          = page_name
        t, s                       = PAGE_TITLES.get(page_name, (page_name, ""))
        title_text.value           = t
        sub_text.value             = s
        sub_text.visible           = True
        dot_sep.visible            = True
        back_btn_container.visible = False
        title_text.update()
        sub_text.update()
        dot_sep.update()
        back_btn_container.update()

    def set_recipe(name: str | None):
        back_icon.color = TEXT()
        back_icon.update()
        if name is None:
            t, s = PAGE_TITLES.get(prev_page["name"], ("CookD", ""))
            title_text.value           = t
            sub_text.value             = s
            sub_text.visible           = True
            dot_sep.visible            = True
            back_btn_container.visible = False
        elif name == "":
            title_text.value           = ""
            sub_text.visible           = False
            dot_sep.visible            = False
            back_btn_container.visible = True
        else:
            title_text.value           = name
            sub_text.visible           = False
            dot_sep.visible            = False
            back_btn_container.visible = True
        title_text.update()
        sub_text.update()
        dot_sep.update()
        back_btn_container.update()

    container.set_recipe = set_recipe
    container.set_page   = set_page
    return container