"""
ingredient_price_list.py
════════════════════════
Komponen UI: daftar bahan resep yang bisa diklik untuk melihat 
harga per toko dan link beli langsung.

Dipanggil dari zaky/price_panel.py setelah kalkulasi selesai.
"""

import flet as ft
from rafy.theme import (
    theme_mgr, ORANGE, GREEN, AMBER, WHITE,
    TOK_COLOR, ALFA_COLOR, AEON_COLOR,
)

def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")

STORE_LABELS = {"tokopedia": "Tokopedia", "alfagift": "Alfagift", "aeon": "AEON Store"}
STORE_COLORS = {"tokopedia": TOK_COLOR,   "alfagift": ALFA_COLOR,  "aeon": AEON_COLOR}

def _fmt_rp(v: int) -> str:
    return f"Rp {v:,.0f}".replace(",", ".")


def _build_ingr_popup(page: ft.Page, keyword: str, store_prices: list) -> None:
    """Buka bottom sheet dengan harga 3 toko + tombol Beli."""

    def _store_card(isp) -> ft.Container:
        if not isp.found or isp.price <= 0:
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(STORE_LABELS[isp.store], color=WHITE,
                                        size=11, weight=ft.FontWeight.BOLD),
                        bgcolor=STORE_COLORS[isp.store],
                        border_radius=ft.BorderRadius.all(20),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    ),
                    ft.Text("Tidak tersedia", color=TEXT3(), size=12, expand=True),
                ], spacing=10),
                bgcolor=BG4(),
                border=ft.Border.all(1, BORDER()),
                border_radius=ft.BorderRadius.all(10),
                padding=ft.Padding.all(12),
                opacity=0.5,
            )

        # Cari termurah dari yang found
        found_prices = [s.price_recipe for s in store_prices
                        if s.found and s.price_recipe > 0]
        is_cheapest = found_prices and isp.price_recipe == min(found_prices)

        cheapest_badge = ft.Container(
            content=ft.Text("Termurah ⭐", color=WHITE, size=9,
                            weight=ft.FontWeight.BOLD),
            bgcolor=GREEN,
            border_radius=ft.BorderRadius.all(20),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            visible=is_cheapest,
        )

        def _open_url(e, url=isp.url):
            page.launch_url(url)

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(STORE_LABELS[isp.store], color=WHITE,
                                    size=11, weight=ft.FontWeight.BOLD),
                    bgcolor=STORE_COLORS[isp.store],
                    border_radius=ft.BorderRadius.all(20),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    width=90,
                ),
                ft.Column([
                    ft.Text(isp.name, color=TEXT2(), size=11,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row([
                        ft.Text(_fmt_rp(isp.price_recipe), color=GREEN if is_cheapest else ORANGE,
                                size=15, weight=ft.FontWeight.BOLD),
                        cheapest_badge,
                    ], spacing=6),
                ], spacing=2, expand=True),
                ft.ElevatedButton(
                    text="Beli",
                    bgcolor=GREEN if is_cheapest else ORANGE,
                    color=WHITE,
                    on_click=_open_url,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    ),
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1B3D28" if is_cheapest else BG4(),
            border=ft.Border.all(1, GREEN if is_cheapest else BORDER()),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.Padding.all(12),
        )

    bs = ft.BottomSheet(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(keyword.title(), color=TEXT(), size=16,
                            weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=TEXT2(),
                                  on_click=lambda e: setattr(bs, "open", False) or page.update()),
                ]),
                ft.Text("Bandingkan harga dari 3 toko — klik Beli untuk membeli",
                        color=TEXT3(), size=11),
                ft.Divider(color=BORDER()),
                *[_store_card(isp) for isp in store_prices],
                ft.Container(height=8),
            ], spacing=10, tight=True),
            padding=ft.Padding.all(20),
            bgcolor=BG3(),
        ),
        open=True,
    )
    page.overlay.append(bs)
    page.update()


def build_ingredient_list(result, page: ft.Page) -> ft.Container:
    """
    Daftar bahan resep yang bisa diklik.
    Tiap baris = nama bahan + harga termurah + indikator toko.
    Klik → popup harga lengkap 3 toko + tombol Beli.

    Args:
        result : PriceResult dari PriceComparisonService
        page   : ft.Page aktif
    """
    if not result.per_ingredient:
        return ft.Container()

    rows = []
    for keyword, store_prices in result.per_ingredient.items():
        found = [s for s in store_prices if s.found and s.price_recipe > 0]
        cheapest_price = min(s.price_recipe for s in found) if found else 0
        cheapest_store = next(
            (s.store for s in found if s.price_recipe == cheapest_price), None
        ) if found else None

        # Titik warna toko termurah
        store_dot = ft.Container(
            width=8, height=8,
            bgcolor=STORE_COLORS.get(cheapest_store, TEXT3()) if cheapest_store else TEXT3(),
            border_radius=ft.BorderRadius.all(4),
        )

        price_text = ft.Text(
            _fmt_rp(cheapest_price) if cheapest_price else "Tidak tersedia",
            color=GREEN if cheapest_price else TEXT3(),
            size=12,
            weight=ft.FontWeight.W_600,
        )

        # Badge toko termurah
        store_badge = ft.Container(
            content=ft.Text(
                STORE_LABELS.get(cheapest_store, ""), color=WHITE, size=9,
            ),
            bgcolor=STORE_COLORS.get(cheapest_store, TEXT3()) if cheapest_store else TEXT3(),
            border_radius=ft.BorderRadius.all(20),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            visible=cheapest_store is not None,
        )

        hint = ft.Text("Klik untuk detail →", color=ORANGE, size=10,
                       opacity=0, animate_opacity=ft.Animation(150))

        row = ft.Container(
            content=ft.Row([
                store_dot,
                ft.Text(keyword.title(), color=TEXT(), size=13, expand=True),
                price_text,
                store_badge,
                hint,
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT3(), size=16),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=BG3(),
            border=ft.Border.all(1, BORDER()),
            border_radius=ft.BorderRadius.all(8),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            on_hover=lambda e, h=hint: (
                setattr(h, "opacity", 1 if e.data == "true" else 0), page.update()
            ),
            on_click=lambda e, kw=keyword, sp=store_prices: (
                _build_ingr_popup(page, kw, sp)
            ),
            ink=True,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
        )
        rows.append(row)

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, color=ORANGE, size=16),
                ft.Text("Harga per Bahan", color=TEXT(), size=14,
                        weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text("klik bahan untuk detail & link beli",
                                    color=ORANGE, size=10),
                    bgcolor=ft.Colors.with_opacity(0.12, ORANGE),
                    border_radius=ft.BorderRadius.all(20),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                ),
            ], spacing=8),
            ft.Container(height=4),
            *rows,
        ], spacing=6),
    )