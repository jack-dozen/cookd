import flet as ft
from rafy.theme import theme_mgr, ORANGE
from rafy.sidebar import build_sidebar_extras


def BG2():   return theme_mgr.get("BG2")
def BG3():   return theme_mgr.get("BG3")
def TEXT2(): return theme_mgr.get("TEXT2")


def build_sidebar(page: ft.Page, navigate_fn) -> ft.Container:
    """
    Returns the sidebar Container. navigate_fn(name) switches pages.
    The returned container also exposes a .toggle() method via a closure
    stored on the container as container.toggle_sidebar.
    """

    state = {"active_index": 1}
    PAGE_NAMES = ["home", "finder", "my-recipes", "for-you", "info"]

    sidebar_ref: list[ft.Container] = []  # will hold [sidebar] after creation

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
            _update_highlights()
            navigate_fn(PAGE_NAMES[index - 1])

        return ft.Container(
            content=ft.Row(controls=[icon_obj, text_obj], spacing=15),
            padding=ft.Padding.symmetric(horizontal=15, vertical=12),
            border_radius=10,
            bgcolor=BG3() if is_active else ft.Colors.TRANSPARENT,
            on_hover=on_hover,
            on_click=on_click,
        )

    def _update_highlights():
        sidebar = sidebar_ref[0]
        for i in range(2, len(sidebar.content.controls)):
            item = sidebar.content.controls[i]
            if isinstance(item, ft.Container) and isinstance(item.content, ft.Row):
                btn_index = i - 1
                is_active = state["active_index"] == btn_index
                item.bgcolor                   = BG3() if is_active else ft.Colors.TRANSPARENT
                item.content.controls[0].color = ORANGE if is_active else TEXT2()
                item.content.controls[1].color = ORANGE if is_active else TEXT2()
        sidebar.update()

    def toggle_sidebar(e=None):
        sidebar = sidebar_ref[0]
        is_collapsing = sidebar.width == 200
        sidebar.width = 60 if is_collapsing else 200

        for item in sidebar.content.controls:
            content = getattr(item, "content", None)
            if isinstance(content, ft.Row) or isinstance(item, ft.Row):
                row = content if isinstance(content, ft.Row) else item
                for ctrl in row.controls:
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
                        e.control.update(),
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

    sidebar_ref.append(sidebar)
    sidebar.toggle_sidebar = toggle_sidebar  # expose for gui.py window_resized
    return sidebar
