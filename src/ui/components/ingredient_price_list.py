"""
ingredient_price_list.py — CookD Ingredient Price List (formerly rafy/ingredient_price_list.py)
"""

import webbrowser
import flet as ft
from src.core.theme import theme_mgr, ORANGE, GREEN, BLACK, WHITE, TOK_COLOR, ALFA_COLOR, AEON_COLOR


def BG():
    return theme_mgr.get("BG")


def BG3():
    return theme_mgr.get("BG3")


def BG4():
    return theme_mgr.get("BG4")


def TEXT():
    return theme_mgr.get("TEXT")


def TEXT2():
    return theme_mgr.get("TEXT2")


def TEXT3():
    return theme_mgr.get("TEXT3")


def BORDER():
    return theme_mgr.get("BORDER")


def _fmt_rp(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")


STORE_LABELS = {"tokopedia": "Tokopedia", "alfagift": "Alfagift", "aeon": "AEON Store"}
STORE_COLORS = {"tokopedia": TOK_COLOR, "alfagift": ALFA_COLOR, "aeon": AEON_COLOR}


def _build_ingr_popup(page, keyword, store_prices):
    def _store_card(isp):
        if not isp.found or isp.price <= 0:
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(content=ft.Text(STORE_LABELS[isp.store], color=WHITE, size=11, weight=ft.FontWeight.BOLD), bgcolor=STORE_COLORS[isp.store], border_radius=ft.BorderRadius.all(20), padding=ft.Padding.symmetric(horizontal=10, vertical=4)),
                        ft.Text("Tidak tersedia", color=TEXT3(), size=12, expand=True),
                    ],
                    spacing=10,
                ),
                bgcolor=BG4(), border=ft.Border.all(1, BORDER()), border_radius=ft.BorderRadius.all(10), padding=ft.Padding.all(12), opacity=0.5,
            )
        found_prices = [s.price_recipe for s in store_prices if s.found and s.price_recipe > 0]
        is_cheapest = found_prices and isp.price_recipe == min(found_prices)
        cheapest_badge = ft.Container(content=ft.Text("Termurah", color=WHITE, size=9, weight=ft.FontWeight.BOLD), bgcolor=GREEN, border_radius=ft.BorderRadius.all(20), padding=ft.Padding.symmetric(horizontal=6, vertical=2), visible=is_cheapest)
        product_url = isp.url

        def _open_url(e):
            if product_url:
                webbrowser.open(product_url)

        bg = "#1B3D28" if is_cheapest else BG4()
        bd = ft.Border.all(1, GREEN if is_cheapest else BORDER())
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=ft.Text(STORE_LABELS[isp.store], color=WHITE, size=11, weight=ft.FontWeight.BOLD), bgcolor=STORE_COLORS[isp.store], border_radius=ft.BorderRadius.all(20), padding=ft.Padding.symmetric(horizontal=10, vertical=4), width=90),
                    ft.Column(
                        controls=[
                            ft.Text(isp.name, color=TEXT2(), size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(controls=[ft.Text(_fmt_rp(isp.price_recipe), color=GREEN if is_cheapest else ORANGE, size=15, weight=ft.FontWeight.BOLD), cheapest_badge], spacing=6),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.ElevatedButton("Beli", bgcolor=GREEN if is_cheapest else ORANGE, color=WHITE, on_click=_open_url, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(horizontal=14, vertical=8))),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=bg, border=bd, border_radius=ft.BorderRadius.all(10), padding=ft.Padding.all(12),
        )

    def _close(e):
        dlg.open = False
        page.update()

    cards = [_store_card(isp) for isp in store_prices]
    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=BG3(),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=ft.Row(
            controls=[
                ft.Text(keyword.title(), color=TEXT(), size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(ft.Icons.CLOSE, icon_color=TEXT2(), on_click=_close),
            ],
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Bandingkan harga dari 3 toko", color=TEXT3(), size=11),
                    ft.Divider(color=BORDER()),
                ] + cards + [ft.Container(height=4)],
                spacing=10,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=500,
        ),
        open=True,
    )
    page.overlay.append(dlg)
    page.update()


def build_ingredient_list(result, page):
    if not result.per_ingredient:
        return ft.Container()

    rows = []
    _themed_rows = []
    _keyword_texts = []
    _header_texts = []
    _chevrons = []

    for keyword, store_prices in result.per_ingredient.items():
        found = [s for s in store_prices if s.found and s.price_recipe > 0]
        cheapest_price = min(s.price_recipe for s in found) if found else 0
        cheapest_store = next((s.store for s in found if s.price_recipe == cheapest_price), None) if found else None

        store_dot = ft.Container(width=8, height=8, bgcolor=STORE_COLORS.get(cheapest_store, TEXT3()) if cheapest_store else TEXT3(), border_radius=ft.BorderRadius.all(4))
        price_text = ft.Text(_fmt_rp(cheapest_price) if cheapest_price else "Tidak tersedia", color=GREEN if cheapest_price else TEXT3(), size=12, weight=ft.FontWeight.W_600)
        store_badge = ft.Container(content=ft.Text(STORE_LABELS.get(cheapest_store, ""), color=WHITE, size=9), bgcolor=STORE_COLORS.get(cheapest_store, TEXT3()) if cheapest_store else TEXT3(), border_radius=ft.BorderRadius.all(20), padding=ft.Padding.symmetric(horizontal=6, vertical=2), visible=cheapest_store is not None)
        hint = ft.Text("Klik untuk detail", color=ORANGE, size=10, opacity=0, animate_opacity=ft.Animation(150))
        keyword_text = ft.Text(keyword.title(), color=TEXT(), size=13, expand=True)
        chevron = ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT3(), size=16)
        _keyword_texts.append(keyword_text)
        _chevrons.append(chevron)

        row = ft.Container(
            content=ft.Row(
                controls=[store_dot, keyword_text, price_text, store_badge, hint, chevron],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=BG3(), border=ft.Border.all(1, BORDER()), border_radius=ft.BorderRadius.all(8),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            on_hover=lambda e, h=hint: (setattr(h, "opacity", 1 if e.data == "true" else 0), page.update()),
            on_click=lambda e, kw=keyword, sp=store_prices: (_build_ingr_popup(page, kw, sp)),
            ink=True,
        )
        rows.append(row)
        _themed_rows.append(row)

    header_text = ft.Text("Harga per Bahan", color=TEXT(), size=14, weight=ft.FontWeight.BOLD)
    _header_texts.append(header_text)

    outer = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, color=ORANGE, size=16),
                        header_text,
                        ft.Container(content=ft.Text("klik bahan untuk detail", color=ORANGE, size=10), bgcolor=ft.Colors.with_opacity(0.12, ORANGE), border_radius=ft.BorderRadius.all(20), padding=ft.Padding.symmetric(horizontal=8, vertical=3)),
                    ],
                    spacing=8,
                ),
                ft.Container(height=4),
            ] + rows,
            spacing=6,
        ),
    )

    def _rebuild_ingr():
        for r in _themed_rows:
            r.bgcolor = BG3()
            r.border = ft.Border.all(1, BORDER())
            r.update()
        for t in _keyword_texts:
            t.color = TEXT()
            t.update()
        for c in _chevrons:
            c.color = TEXT3()
            c.update()
        for t in _header_texts:
            t.color = TEXT()
            t.update()

    theme_mgr.add_listener(_rebuild_ingr)
    return outer
