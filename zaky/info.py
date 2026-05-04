"""
info.py
Halaman Info: tentang aplikasi, cara menggunakan, dan sumber data.
"""

import flet as ft
from rafy.theme import theme_mgr, ORANGE, GREEN, BLUE, AMBER, WHITE
from rafy.theme import TOK_COLOR, ALFA_COLOR, AEON_COLOR


# ─────────────────────────────────────────────────────────────────────
# HELPERS — baca live dari theme_mgr
# ─────────────────────────────────────────────────────────────────────
def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


# ─────────────────────────────────────────────────────────────────────
# INFO PAGE
# ─────────────────────────────────────────────────────────────────────
def InfoPage(page: ft.Page) -> ft.Container:
    """
    Buat halaman Info CookD.

    Params:
        page : ft.Page aktif

    Return:
        ft.Container — langsung masuk ke pages["info"]
    """

    # ── Hero banner ──────────────────────────────────────────────────
    hero = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            ft.Container(
                                width=64, height=64,
                                bgcolor=ORANGE,
                                border_radius=ft.BorderRadius.all(16),
                            ),
                            ft.Container(
                                width=64, height=64,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(
                                    ft.Icons.SEARCH_ROUNDED,
                                    color=WHITE,
                                    size=32,
                                ),
                            ),
                        ],
                    ),
                    padding=ft.padding.only(right=20),
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Tentang CookD",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=WHITE,
                            font_family="Font",
                        ),
                        ft.Text(
                            "CookD membantu kamu menemukan resep dari bahan yang tersedia, "
                            "lengkap dengan perbandingan harga bahan dari Tokopedia, "
                            "Alfagift, dan AEON Store.",
                            size=13,
                            color="#FFDDCC",
                            font_family="Font",
                            max_lines=3,
                        ),
                    ],
                    spacing=6,
                    expand=True,
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ORANGE,
        border_radius=ft.BorderRadius.all(16),
        padding=ft.padding.symmetric(horizontal=28, vertical=24),
        margin=ft.margin.only(bottom=20),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color="#66E8440A",
            offset=ft.Offset(0, 6),
        ),
    )

    # ── Step item builder ────────────────────────────────────────────
    def step_item(number: int, title: str, description: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text(
                            str(number),
                            color=WHITE,
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            font_family="Font",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        width=34,
                        height=34,
                        bgcolor=ORANGE,
                        border_radius=ft.BorderRadius.all(17),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT(),
                                font_family="Font",
                            ),
                            ft.Text(
                                description,
                                size=12,
                                color=TEXT2(),
                                font_family="Font",
                                max_lines=3,
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        )

    cara_menggunakan = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "Cara Menggunakan",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT(),
                        font_family="Font",
                    ),
                    padding=ft.padding.symmetric(horizontal=20, vertical=16),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                ),
                step_item(
                    1,
                    "Masukkan Bahan",
                    'Buka Recipe Finder, ketik bahan yang kamu punya, pisahkan dengan koma. '
                    'Contoh: "bawang putih, tomat, garam, telur"',
                ),
                step_item(
                    2,
                    "Pilih Resep",
                    "Resep ditampilkan dengan persentase kecocokan bahan. "
                    "Hijau = semua bahan ada, kuning = hampir lengkap.",
                ),
                step_item(
                    3,
                    "Kalkulasi Harga",
                    'Di halaman detail resep, klik "Kalkulasi Harga Bahan" untuk melihat '
                    "perbandingan harga dari 3 toko. Klik tiap bahan untuk popup harga detail "
                    "dan tombol beli langsung.",
                ),
                step_item(
                    4,
                    "Simpan Resep",
                    "Klik ♥ untuk menyimpan resep ke My Recipes agar mudah diakses kembali.",
                ),
            ],
            spacing=0,
        ),
        bgcolor=BG2(),
        border_radius=ft.BorderRadius.all(14),
        border=ft.Border.all(1, BORDER()),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        margin=ft.margin.only(bottom=16),
    )

    # ── Source badge builder ─────────────────────────────────────────
    def source_badge(dot_color: str, label: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=10, height=10,
                        bgcolor=dot_color,
                        border_radius=ft.BorderRadius.all(5),
                    ),
                    ft.Text(
                        label,
                        size=12,
                        color=TEXT(),
                        font_family="Font",
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=BG3(),
            border_radius=ft.BorderRadius.all(20),
            border=ft.Border.all(1, dot_color + "55"),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )

    sumber_data = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "Sumber Data",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT(),
                        font_family="Font",
                    ),
                    padding=ft.padding.symmetric(horizontal=20, vertical=16),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    source_badge(ORANGE,     "Cookpad — Resep"),
                                    source_badge(TOK_COLOR,  "Tokopedia — Harga"),
                                    source_badge(ALFA_COLOR, "Alfagift — Harga"),
                                    source_badge(AEON_COLOR, "AEON Store — Harga"),
                                ],
                                spacing=8,
                                wrap=True,
                                run_spacing=8,
                            ),
                            ft.Text(
                                "Harga adalah estimasi hasil scraping dan dapat berubah sewaktu-waktu.",
                                size=11,
                                color=TEXT3(),
                                font_family="Font",
                                italic=True,
                            ),
                        ],
                        spacing=14,
                    ),
                    padding=ft.padding.symmetric(horizontal=20, vertical=16),
                ),
            ],
            spacing=0,
        ),
        bgcolor=BG2(),
        border_radius=ft.BorderRadius.all(14),
        border=ft.Border.all(1, BORDER()),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        margin=ft.margin.only(bottom=16),
    )

    # ── Footer ───────────────────────────────────────────────────────
    footer = ft.Container(
        content=ft.Text(
            "CookD v1.0.0 · Proyek Kuliah 2025",
            size=12,
            color=TEXT3(),
            font_family="Font",
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        padding=ft.padding.symmetric(vertical=20),
    )

    # ── Assemble scroll column ───────────────────────────────────────
    scroll_content = ft.Column(
        controls=[
            hero,
            cara_menggunakan,
            sumber_data,
            footer,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        padding=ft.padding.symmetric(horizontal=28, vertical=24),
        content=scroll_content,
    )
