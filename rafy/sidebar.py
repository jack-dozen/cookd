"""
rafy/sidebar.py (updated) — CookD
Widget tambahan untuk sidebar bagian bawah.

Perubahan: import_export_btn sekarang membuka dialog konfirmasi
           lalu memanggil exporter.py atau importer.py dari fadhil/

Cara pakai (sama seperti sebelumnya):
    from rafy.sidebar import build_sidebar_extras
    *build_sidebar_extras(page),
"""

import flet as ft
from rafy.theme import theme_mgr, build_theme_toggle


def build_sidebar_extras(page: ft.Page, on_import_done=None) -> list:
    """
    Buat list widget untuk bagian bawah sidebar:
    - Spacer
    - Tombol Import / Export  ← sekarang ada fungsinya
    - Theme toggle (dark/light)
    - Bottom padding

    Params:
        page           : ft.Page aktif
        on_import_done : callback() dipanggil setelah import berhasil
                         (gunakan untuk refresh halaman My Recipes)

    Return:
        list of ft.Control — langsung unpack ke sidebar controls
    """

    # ── Dialog konfirmasi Import / Export ─────────────────────────────────────
    def show_import_export_dialog(e):
        """Tampilkan dialog: mau Import atau Export?"""

        def do_export(e):
            dialog.open = False
            page.update()
            from fadhil.exporter import export_my_recipes
            export_my_recipes(page)

        def do_import(e):
            dialog.open = False
            page.update()
            from fadhil.importer import import_my_recipes

            def on_done(imported, skipped):
                if on_import_done:
                    on_import_done()

            import_my_recipes(page, on_done=on_done)

        def on_cancel(e):
            dialog.open = False
            page.update()

        BG2    = theme_mgr.get("BG2") or "#242424"
        BG3    = theme_mgr.get("BG3") or "#2E2E2E"
        BG4    = "#363636"
        TEXT   = theme_mgr.get("TEXT") or "#F0F0EC"
        TEXT2  = theme_mgr.get("TEXT2") or "#B0B0AB"
        TEXT3  = theme_mgr.get("TEXT3") or "#707070"
        ORANGE = "#E8440A"
        GREEN  = "#2E9E5B"

        dialog = ft.AlertDialog(
            modal   = True,
            bgcolor = BG2,
            title   = ft.Row(
                controls=[
                    ft.Icon(ft.Icons.IMPORT_EXPORT, color=ORANGE, size=22),
                    ft.Text("Import / Export", color=TEXT,
                            weight=ft.FontWeight.BOLD, size=16),
                ],
                spacing=10,
            ),
            content = ft.Container(
                width=380,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Pilih tindakan yang ingin dilakukan:",
                            color=TEXT2, size=13,
                        ),
                        ft.Container(height=8),
                        # Tombol Export
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Icon(
                                            ft.Icons.DOWNLOAD_OUTLINED,
                                            color=ORANGE, size=22,
                                        ),
                                        bgcolor=BG4,
                                        border_radius=ft.BorderRadius.all(8),
                                        padding=ft.Padding.all(8),
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text("Export", color=TEXT,
                                                    weight=ft.FontWeight.BOLD,
                                                    size=14),
                                            ft.Text(
                                                "Simpan resep tersimpan ke file JSON",
                                                color=TEXT3, size=11,
                                            ),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT,
                                            color=TEXT3, size=18),
                                ],
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor=BG3,
                            border_radius=ft.BorderRadius.all(10),
                            padding=ft.Padding.all(12),
                            on_click=do_export,
                            ink=True,
                        ),
                        ft.Container(height=8),
                        # Tombol Import
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Icon(
                                            ft.Icons.UPLOAD_OUTLINED,
                                            color=GREEN, size=22,
                                        ),
                                        bgcolor=BG4,
                                        border_radius=ft.BorderRadius.all(8),
                                        padding=ft.Padding.all(8),
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text("Import", color=TEXT,
                                                    weight=ft.FontWeight.BOLD,
                                                    size=14),
                                            ft.Text(
                                                "Muat resep dari file JSON",
                                                color=TEXT3, size=11,
                                            ),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT,
                                            color=TEXT3, size=18),
                                ],
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor=BG3,
                            border_radius=ft.BorderRadius.all(10),
                            padding=ft.Padding.all(12),
                            on_click=do_import,
                            ink=True,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton(
                    "Batal",
                    style=ft.ButtonStyle(color=TEXT3),
                    on_click=on_cancel,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ── Tombol Import / Export di sidebar ────────────────────────────────────
    import_export_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.IMPORT_EXPORT,
                        color=theme_mgr.get("TEXT2"), size=18),
                ft.Text("Import / Export",
                        color=theme_mgr.get("TEXT2"), size=13,
                        opacity=1.0,
                        animate_opacity=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT)),
            ],
            spacing=10,
        ),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border_radius=10,
        bgcolor=ft.Colors.TRANSPARENT,
        on_hover=lambda e: (
            setattr(e.control, "bgcolor",
                    theme_mgr.get("BG3") if e.data else ft.Colors.TRANSPARENT),
            e.control.update(),
        ),
        on_click=show_import_export_dialog,
    )

    return [
        ft.Container(expand=True),
        import_export_btn,
        build_theme_toggle(page, show_label=True),
        ft.Container(height=8),
    ]
