"""
price_panel.py
═══════════════════════════════════════════════════════════════════════════════
Modul UI untuk visualisasi hasil kalkulasi harga bahan resep.

komponen utama:
    1. build_loading_panel()  → animasi loading "mencari harga"
    2. build_price_panel()    → price cards + bar chart perbandingan 3 toko
═══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
import threading
import asyncio
import time
import math
import os
import sys

# ── Path resolver ──────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from rafy.theme import (
    theme_mgr, ORANGE, GREEN, AMBER, BLUE, WHITE, BLACK,
    TOK_COLOR, ALFA_COLOR, AEON_COLOR,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")

def _fmt_rp(amount: int) -> str:
    """Format angka jadi Rupiah ringkas: 178500 → 'Rp 178.500'"""
    return f"Rp {amount:,.0f}".replace(",", ".")

STORE_LABELS = {
    "tokopedia": "Tokopedia",
    "alfagift":  "Alfagift",
    "aeon":      "AEON Store",
}

STORE_COLORS = {
    "tokopedia": TOK_COLOR,
    "alfagift":  ALFA_COLOR,
    "aeon":      AEON_COLOR,
}

STORE_ICONS = {
    "tokopedia": ft.Icons.SHOPPING_BAG_OUTLINED,
    "alfagift":  ft.Icons.STORE_OUTLINED,
    "aeon":      ft.Icons.STOREFRONT_OUTLINED,
}

# Loading messages yang berganti-ganti — tone casual, tidak teknis
_LOADING_MESSAGES = [
    "Mencari bahan terbaik untukmu...",
    "Membandingkan harga dari 3 toko...",
    "Menghitung estimasi biaya resep...",
    "Menyiapkan rekomendasi terbaik...",
    "Hampir selesai...",
    "Biarkan Rafy memasak...",
]


# ══════════════════════════════════════════════════════════════════════════════
# LOADING PANEL
# ══════════════════════════════════════════════════════════════════════════════

def build_loading_panel(page: ft.Page) -> tuple[ft.Container, callable]:
    """
    Buat loading panel animasi.

    Returns:
        (container, stop_fn) — stop_fn() dipanggil untuk menghentikan animasi
    """
    _running = [True]

    # ── Teks pesan berputar ───────────────────────────────────────────────────
    msg_text = ft.Text(
        value=_LOADING_MESSAGES[0],
        color=TEXT2(),
        size=14,
        weight=ft.FontWeight.W_500,
        text_align=ft.TextAlign.CENTER,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
    )

    # ── Tiga dot animasi (bounce) ─────────────────────────────────────────────
    dot_refs = [ft.Ref[ft.Container]() for _ in range(3)]
    dot_colors = [ORANGE, AMBER, GREEN]

    def make_dot(ref, color):
        return ft.Container(
            ref=ref,
            width=10,
            height=10,
            bgcolor=color,
            border_radius=ft.BorderRadius.all(5),
            animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
            opacity=0.4,
        )

    dots_row = ft.Row(
        controls=[make_dot(dot_refs[i], dot_colors[i]) for i in range(3)],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
    )

    # ── Progress bar samar ────────────────────────────────────────────────────
    progress_bar = ft.ProgressBar(
        width=260,
        color=ORANGE,
        bgcolor=BG4(),
        border_radius=ft.BorderRadius.all(4),
        value=None,  # indeterminate
    )

    # ── Tiga status toko ──────────────────────────────────────────────────────
    store_status_texts = {
        "tokopedia": ft.Ref[ft.Text](),
        "alfagift":  ft.Ref[ft.Text](),
        "aeon":      ft.Ref[ft.Text](),
    }

    def make_store_status(store: str, ref) -> ft.Row:
        dot = ft.Container(
            width=7, height=7,
            bgcolor=TEXT3(),
            border_radius=ft.BorderRadius.all(4),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )
        return ft.Row(
            controls=[
                dot,
                ft.Text(
                    ref=ref,
                    value=STORE_LABELS[store],
                    color=TEXT3(),
                    size=11,
                    animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
                ),
            ],
            spacing=6,
            tight=True,
        )

    stores_row = ft.Row(
        controls=[
            make_store_status(s, store_status_texts[s])
            for s in ["tokopedia", "alfagift", "aeon"]
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
    )

    # ── Layout loading panel ──────────────────────────────────────────────────
    container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(height=16),
                dots_row,
                ft.Container(height=16),
                msg_text,
                ft.Container(height=12),
                progress_bar,
                ft.Container(height=14),
                stores_row,
                ft.Container(height=16),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor=BG3(),
        border_radius=ft.BorderRadius.all(14),
        padding=ft.padding.symmetric(horizontal=30, vertical=20),
        border=ft.Border.all(1, BORDER()),
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
    )

    # ── Animasi loop ──────────────────────────────────────────────────────────
    _msg_index = [0]
    _dot_phase  = [0]

    def _animate_loop():
        while _running[0]:
            # Bounce dots — satu demi satu
            phase = _dot_phase[0] % 3
            for i, ref in enumerate(dot_refs):
                if ref.current:
                    if i == phase:
                        ref.current.opacity = 1.0
                        ref.current.height  = 13
                    else:
                        ref.current.opacity = 0.3
                        ref.current.height  = 10
            _dot_phase[0] += 1
            try:
                page.update()
            except Exception:
                pass

            time.sleep(0.35)

            # Ganti pesan setiap ~2 detik (setiap 6 tick)
            if _dot_phase[0] % 6 == 0:
                _msg_index[0] = (_msg_index[0] + 1) % len(_LOADING_MESSAGES)
                if msg_text:
                    msg_text.opacity = 0
                    try: page.update()
                    except: pass
                    time.sleep(0.15)
                    msg_text.value   = _LOADING_MESSAGES[_msg_index[0]]
                    msg_text.opacity = 1
                    try: page.update()
                    except: pass

    anim_thread = threading.Thread(target=_animate_loop, daemon=True)
    anim_thread.start()

    def update_store_status(store: str, done: bool):
        """Dipanggil dari luar untuk update status toko (done=True → hijau)."""
        ref = store_status_texts.get(store)
        if ref and ref.current:
            ref.current.color = GREEN if done else TEXT2()
            try: page.update()
            except: pass

    def stop():
        _running[0] = False

    return container, stop, update_store_status


# ══════════════════════════════════════════════════════════════════════════════
# PRICE CARDS
# ══════════════════════════════════════════════════════════════════════════════

def _build_price_cards(result) -> ft.Container:
    """
    Tiga card: Harga Total Bahan | Harga Resep | Harga per Porsi.
    Dengan dropdown pilih toko di atas.
    """
    stores      = ["tokopedia", "alfagift", "aeon"]
    cheapest    = result.cheapest_store
    store_data  = result.per_store   # dict[store, StoreTotal]
    portions    = result.portions

    # ── Refs untuk card values ────────────────────────────────────────────────
    val_total   = ft.Ref[ft.Text]()
    val_resep   = ft.Ref[ft.Text]()
    val_porsi   = ft.Ref[ft.Text]()
    badge_ref   = ft.Ref[ft.Container]()
    card_resep  = ft.Ref[ft.Container]()

    def _fill(store: str):
        st = store_data.get(store)
        if not st:
            return
        if val_total.current:
            val_total.current.value = _fmt_rp(st.harga_total)
        if val_resep.current:
            val_resep.current.value = _fmt_rp(st.harga_resep)
        if val_porsi.current:
            val_porsi.current.value = _fmt_rp(st.harga_per_porsi)

        is_cheap = (store == cheapest)
        if badge_ref.current:
            badge_ref.current.visible = is_cheap
        if card_resep.current:
            card_resep.current.bgcolor = "#1B3D28" if is_cheap else BG4()
            card_resep.current.border  = ft.Border.all(1, GREEN if is_cheap else BORDER())

    # ── Dropdown ──────────────────────────────────────────────────────────────
    store_options = [
        ft.dropdown.Option(key=s, text=STORE_LABELS[s]) for s in stores
    ]
    dd = ft.Dropdown(
        options=store_options,
        value=cheapest if cheapest else "tokopedia",
        width=150,
        bgcolor=BG4(),
        border_color=BORDER(),
        color=TEXT(),
        text_size=12,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
        on_select=lambda e: (_fill(e.control.value), page_ref[0].update())
                  if page_ref[0] else None,
    )
    page_ref = [None]  # set after, workaround closure

    # ── Badge "Termurah ⭐" ────────────────────────────────────────────────────
    badge = ft.Container(
        ref=badge_ref,
        content=ft.Text("Termurah ⭐", color=WHITE, size=9, weight=ft.FontWeight.BOLD),
        bgcolor=GREEN,
        border_radius=ft.BorderRadius.all(20),
        padding=ft.padding.symmetric(horizontal=7, vertical=3),
        visible=True,
    )

    def _card(label: str, val_ref, sub: str, ref=None, extra_top=None) -> ft.Container:
        top_row = ft.Row(
            controls=[
                ft.Text(label, color=TEXT2(), size=11, weight=ft.FontWeight.W_500),
                extra_top or ft.Container(),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        return ft.Container(
            ref=ref,
            content=ft.Column(
                controls=[
                    top_row,
                    ft.Text(
                        ref=val_ref,
                        value="—",
                        color=ORANGE,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        font_family="Font",
                    ),
                    ft.Text(sub, color=TEXT3(), size=10),
                ],
                spacing=4,
            ),
            bgcolor=BG4(),
            border=ft.Border.all(1, BORDER()),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.padding.all(14),
            expand=True,
            animate=ft.Animation(250, ft.AnimationCurve.EASE_IN_OUT),
        )

    card_total = _card("Harga Total Bahan", val_total, "total semua bahan satuan penuh")
    card_r = _card(
        "Harga Resep", val_resep,
        "estimasi sesuai kebutuhan resep",
        ref=card_resep,
        extra_top=badge,
    )
    card_p = _card("Harga per Porsi", val_porsi, f"untuk {portions} porsi")

    cards_row = ft.Row(
        controls=[card_total, card_r, card_p],
        spacing=10,
    )

    # ── Header dengan dropdown ────────────────────────────────────────────────
    header = ft.Row(
        controls=[
            ft.Text("Perbandingan Harga", color=TEXT(), size=16, weight=ft.FontWeight.BOLD),
            dd,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    container = ft.Container(
        content=ft.Column(
            controls=[header, cards_row],
            spacing=14,
        ),
    )

    # Isi nilai awal setelah build
    def _init_fill(page: ft.Page):
        page_ref[0] = page
        dd.on_select = lambda e: (_fill(e.control.value), page.update())
        _fill(dd.value)

    container._init_fill = _init_fill
    return container


# ══════════════════════════════════════════════════════════════════════════════
# BAR CHART
# ══════════════════════════════════════════════════════════════════════════════

def _build_bar_chart(result) -> ft.Container:
    """
    Bar chart perbandingan 3 toko: Total Bahan vs Harga Resep.

    Setiap toko punya dua bar berdampingan (total vs resep).
    Toko tanpa data → tampilkan placeholder 'Data N/A'.
    Bar + label nilai tidak saling overlap karena layout pakai Stack
    dengan posisi absolut untuk label, bukan Column tumpuk.
    """
    stores     = ["tokopedia", "alfagift", "aeon"]
    store_data = result.per_store
    cheapest   = result.cheapest_store

    CHART_H = 140   # tinggi area bar murni (px)
    LABEL_H = 18    # tinggi zona label nilai di atas bar — TERPISAH dari CHART_H
    BAR_W   = 26    # lebar tiap bar
    TOTAL_H = CHART_H + LABEL_H  # total tinggi kolom tiap grup

    def _fmt_rp_short(v: int) -> str:
        if v >= 1_000_000:
            return f"Rp {v/1_000_000:.1f}jt"
        if v >= 1_000:
            return f"Rp {v//1_000}rb"
        return f"Rp {v}"

    # Kumpulkan semua nilai > 0 untuk normalisasi
    all_vals = []
    for s in stores:
        st = store_data.get(s)
        if st:
            if st.harga_total > 0: all_vals.append(st.harga_total)
            if st.harga_resep > 0: all_vals.append(st.harga_resep)

    max_val = max(all_vals) if all_vals else 1

    def _norm(v: int) -> int:
        """Nilai → tinggi pixel dalam CHART_H. Min 6px agar bar kelihatan."""
        if v <= 0: return 0
        return max(6, int((v / max_val) * CHART_H))

    # ── Sumbu Y ───────────────────────────────────────────────────────────────
    y_levels = [0, 0.25, 0.5, 0.75, 1.0]
    y_axis_labels = ft.Column(
        controls=[
            ft.Text(
                _fmt_rp_short(int(max_val * lvl)) if lvl > 0 else "0",
                size=9,
                color=TEXT3(),
                text_align=ft.TextAlign.RIGHT,
            )
            for lvl in reversed(y_levels)
        ],
        spacing=0,
        height=TOTAL_H,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # ── Satu bar: Stack(label di atas, bar di bawah) ──────────────────────────
    def _bar(h: int, col: str, val: int, label_suffix: str = "") -> ft.Container:
        """
        Satu bar dengan label nilai di atasnya.

        Kunci fix bar chart: gunakan Stack dengan ukuran tetap TOTAL_H.
        Label nilai diletakkan di atas (top=0), bar body di bawah (bottom=0).
        Dengan begitu, label tidak pernah 'mendorong' bar keluar area.
        """
        if h <= 0:
            # Bar tidak ada datanya → kembalikan container kosong setinggi TOTAL_H
            return ft.Container(width=BAR_W, height=TOTAL_H)

        return ft.Container(
            width=BAR_W,
            height=TOTAL_H,
            content=ft.Stack(
                controls=[
                    # Label nilai — selalu di zona atas (LABEL_H px pertama)
                    ft.Container(
                        content=ft.Text(
                            _fmt_rp_short(val) + label_suffix,
                            size=8,
                            color=TEXT2(),
                            text_align=ft.TextAlign.CENTER,
                            no_wrap=True,
                        ),
                        width=BAR_W,
                        height=LABEL_H,
                        alignment=ft.Alignment(0, 1),  # bottom_center
                        top=0,
                    ),
                    # Bar body — tumbuh dari bawah
                    ft.Container(
                        width=BAR_W,
                        height=h,
                        bgcolor=col,
                        border_radius=ft.BorderRadius.only(
                            top_left=3, top_right=3,
                            bottom_left=0, bottom_right=0,
                        ),
                        bottom=0,
                    ),
                ],
            ),
        )

    # ── Grup dua bar untuk satu toko ─────────────────────────────────────────
    def _build_group(store: str) -> ft.Column:
        st       = store_data.get(store)
        is_cheap = (store == cheapest)
        color    = STORE_COLORS[store]
        has_data = st is not None and (st.harga_total > 0 or st.harga_resep > 0)

        label_color = GREEN if is_cheap else (TEXT2() if has_data else TEXT3())
        store_label = ft.Text(
            STORE_LABELS[store] + (" ⭐" if is_cheap else ""),
            size=10,
            color=label_color,
            weight=ft.FontWeight.W_600 if is_cheap else ft.FontWeight.NORMAL,
            text_align=ft.TextAlign.CENTER,
        )

        if not has_data:
            # Placeholder kalau data tidak tersedia
            placeholder = ft.Container(
                height=TOTAL_H,
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.REMOVE_CIRCLE_OUTLINE, color=TEXT3(), size=16),
                        ft.Text("Data N/A", size=9, color=TEXT3(),
                                text_align=ft.TextAlign.CENTER),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                alignment=ft.Alignment(0, 0),  # center
            )
            return ft.Column(
                controls=[placeholder, store_label],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )

        h_total = _norm(st.harga_total)
        h_resep = _norm(st.harga_resep)

        # Total Bahan selalu ORANGE (sesuai legenda)
        # Harga Resep = warna toko; kalau termurah → GREEN
        col_total = ORANGE
        col_resep = GREEN if is_cheap else color

        bars = ft.Row(
            controls=[
                _bar(h_total, col_total, st.harga_total),
                _bar(h_resep, col_resep, st.harga_resep,
                     " ⭐" if is_cheap else ""),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        return ft.Column(
            controls=[bars, store_label],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    groups = ft.Row(
        controls=[_build_group(s) for s in stores],
        alignment=ft.MainAxisAlignment.SPACE_AROUND,
        vertical_alignment=ft.CrossAxisAlignment.END,
        expand=True,
    )

    # ── Area chart ────────────────────────────────────────────────────────────
    chart_area = ft.Row(
        controls=[
            ft.Container(content=y_axis_labels, width=56),
            ft.Container(width=1, height=TOTAL_H, bgcolor=BORDER()),  # sumbu Y
            ft.Container(width=8),
            ft.Column(
                controls=[
                    groups,
                    ft.Container(height=1, bgcolor=BORDER(), expand=True),  # sumbu X
                ],
                spacing=0,
                expand=True,
            ),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.END,
        expand=True,
    )

    # ── Legenda ───────────────────────────────────────────────────────────────
    def _legend_item(color: str, label: str) -> ft.Row:
        return ft.Row(
            controls=[
                ft.Container(
                    width=10, height=10,
                    bgcolor=color,
                    border_radius=ft.BorderRadius.all(2),
                ),
                ft.Text(label, color=TEXT2(), size=10),
            ],
            spacing=5,
            tight=True,
        )

    legend = ft.Row(
        controls=[
            _legend_item(ORANGE, "Total Bahan"),
            _legend_item(AEON_COLOR, "Harga Resep"),
            _legend_item(GREEN, "Termurah (Harga Resep)"),
        ],
        spacing=16,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Perbandingan Harga Resep — 3 Toko",
                    color=TEXT2(),
                    size=12,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=12),
                chart_area,
                ft.Container(height=10),
                legend,
            ],
            spacing=0,
        ),
        bgcolor=BG4(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(10),
        padding=ft.padding.all(14),
    )


# ══════════════════════════════════════════════════════════════════════════════
# FULL PRICE PANEL
# ══════════════════════════════════════════════════════════════════════════════

def build_price_panel(result, page: ft.Page) -> ft.Container:
    """
    Build panel perbandingan harga lengkap.
    Dipanggil setelah PriceComparisonService.run() selesai.

    Args:
        result : PriceResult dari PriceComparisonService
        page   : ft.Page aktif

    Returns:
        ft.Container siap ditambah ke detail_content
    """
    if not result.success:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=AMBER, size=18),
                    ft.Text(
                        result.error_message or "Kalkulasi gagal.",
                        color=TEXT2(),
                        size=13,
                    ),
                ],
                spacing=10,
            ),
            bgcolor=BG3(),
            border=ft.Border.all(1, AMBER),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.padding.all(16),
        )

    print("[price_panel] Mulai build price cards...")
    cards_widget = _build_price_cards(result)
    print("[price_panel] Price cards selesai")

    print("[price_panel] Mulai build bar chart...")
    chart_widget = _build_bar_chart(result)
    print("[price_panel] Bar chart selesai")

    disclaimer = ft.Text(
        "* Harga estimasi berdasarkan data scraping real-time. Harga aktual di toko dapat berbeda.",
        color=TEXT3(),
        size=10,
        italic=True,
    )

    panel = ft.Container(
        content=ft.Column(
            controls=[
                # Divider
                ft.Container(
                    height=1,
                    bgcolor=BORDER(),
                    margin=ft.margin.only(bottom=20),
                ),
                cards_widget,
                ft.Container(height=14),
                chart_widget,
                ft.Container(height=8),
                disclaimer,
            ],
            spacing=0,
        ),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        opacity=0,
    )

    # Simpan _init_fill sebagai attribute agar bisa dipanggil dari luar
    # PERBAIKAN: Tidak pakai thread terpisah — cukup expose fungsi _init_fill
    # supaya caller (_work di run_price_calculation) yang manage update
    panel._init_fill = lambda: cards_widget._init_fill(page)

    return panel


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR — dipanggil langsung dari tombol di Gui.py
# ══════════════════════════════════════════════════════════════════════════════

def run_price_calculation(
    page       : ft.Page,
    recipe     : dict,
    price_area : ft.Ref,
    btn        : ft.Ref | None = None,
):
    """
    Entry point utama. Dipanggil saat user klik tombol "Kalkulasi Harga Bahan".

    Flow:
        1. Tampilkan loading panel
        2. Jalankan PriceComparisonService.run() di thread terpisah
        3. Setelah selesai, ganti loading panel dengan build_price_panel()

    Args:
        page       : ft.Page aktif
        recipe     : dict resep (harus punya 'recipe_id')
        price_area : ft.Ref[ft.Container] — container tempat panel ditempatkan
        btn        : ft.Ref[ft.ElevatedButton] opsional — untuk disable selama loading
    """
    # Guard: kalau sudah ada hasil, scroll ke sana
    if price_area.current and getattr(price_area.current, "_price_done", False):
        price_area.current.scroll_to(offset=0)
        return

    recipe_id = recipe.get("recipe_id") or recipe.get("id", "")
    if not recipe_id:
        # Fallback: pakai recipe name sebagai ID jika tidak ada
        recipe_id = recipe.get("name", "unknown")

    # Disable tombol
    if btn and btn.current:
        btn.current.disabled = True
        btn.current.content  = ft.Text("⏳ Menghitung...", color=WHITE)
        page.update()

    # Bangun loading panel
    loading_panel, stop_loading, update_store = build_loading_panel(page)

    if price_area.current:
        price_area.current.content = loading_panel
        price_area.current.visible = True
        page.update()

    def _work():
        try:
            from zaky.PriceComparisonService import PriceComparisonService
            service = PriceComparisonService()

            def _progress(msg: str):
                parts = [p.strip() for p in msg.split("·") if p.strip()]
                for part in parts:
                    for store in ["tokopedia", "alfagift", "aeon"]:
                        label = STORE_LABELS[store].split()[0].lower()
                        if part.lower().startswith(label):
                            update_store(store, "✓" in part)

            result = service.run(recipe_id=recipe_id, progress_cb=_progress)

        except Exception as ex:
            try:
                from zaky.PriceComparisonService import PriceResult
                result = PriceResult(success=False, error_message=str(ex))
            except Exception:
                class _FallbackResult:
                    success = False
                    error_message = str(ex)
                result = _FallbackResult()

        stop_loading()
        print("[price_panel] Service selesai, mulai build panel hasil...")

        panel = build_price_panel(result, page)
        print("[price_panel] Panel hasil berhasil dibangun")

        # ── PERBAIKAN UI tidak update ──────────────────────────────────────
        # Flet pakai asyncio event loop internal. page.update() dari thread
        # biasa kadang tidak ter-flush ke UI sampai ada event lain (minimize, dll).
        # Solusi: schedule update sebagai coroutine di event loop Flet,
        # persis seperti pattern asyncio.run_coroutine_threadsafe di Gui.py.
        async def _apply_ui():
            if price_area.current:
                price_area.current.content = panel
                price_area.current._price_done = True
                if hasattr(panel, "_init_fill"):
                    try:
                        panel._init_fill()
                    except Exception as e:
                        print(f"[price_panel] _init_fill error: {e}")
                panel.opacity = 1
                page.update()
            print("[price_panel] UI berhasil diupdate")

            if btn and btn.current:
                btn.current.disabled = False
                btn.current.content  = ft.Text("💰 Lihat Perbandingan Harga", color=WHITE)
                page.update()

        # page.run_task() adalah cara yang benar di Flet untuk schedule
        # coroutine dari worker thread — works di semua platform termasuk Windows
        page.run_task(_apply_ui)

    threading.Thread(target=_work, daemon=True).start()
