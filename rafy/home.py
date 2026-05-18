"""
home.py — CookD
════════════════════════════════════════════════════════════════
Halaman Home: landing page pertama yang dilihat user.

Konten:
  • Greeting dinamis (pagi / siang / sore / malam)
  • Search bar shortcut → navigate ke Finder
  • Hero card  : "Resep Hari Ini" (ambil dari DB, logika sama dgn for_you_ui)
  • Stat cards : Resep Tersimpan  |  Terakhir Dibuka
  • Rekomendasi berdasarkan waktu (ganti Menu Cepat)


════════════════════════════════════════════════════════════════
"""

import asyncio
import os
import sys
from datetime import datetime

import flet as ft

# ── Path resolver ──────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from rafy.theme import theme_mgr, ORANGE, WHITE
from tinydb import TinyDB

_DB_PATH  = os.path.join(_ROOT, "data", "base.json")
_db_cache = None


def _get_db() -> TinyDB:
    global _db_cache
    if _db_cache is None:
        _db_cache = TinyDB(_DB_PATH)
    return _db_cache


# ── Theme helpers ──────────────────────────────────────────────────────────────
def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _load_all_recipes() -> list[dict]:
    try:
        return _get_db().table("cookpad_recipes").all()
    except Exception as e:
        print(f"[home] Gagal baca cookpad_recipes: {e}")
        return []


def _load_my_recipes() -> list[dict]:
    try:
        return _get_db().table("my_recipes").all()
    except Exception as e:
        print(f"[home] Gagal baca my_recipes: {e}")
        return []


def _get_resep_hari_ini(recipes: list[dict]) -> dict | None:
    """Resep terbaru (scraped_at) dengan match_score tertinggi."""
    if not recipes:
        return None
    from datetime import date

    def _parse(r: dict):
        try:
            return datetime.strptime(r.get("scraped_at", ""), "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            return date.min

    latest_date  = max(_parse(r) for r in recipes)
    latest_group = [r for r in recipes if _parse(r) == latest_date]
    return max(latest_group, key=lambda r: r.get("match_score", 0))


def _get_last_opened() -> str:
    """Nama resep yang terakhir dibuka (dari tabel 'results', sorted by timestamp)."""
    try:
        results = _get_db().table("results").all()
        if not results:
            return "—"
        latest = max(results, key=lambda r: r.get("opened_at", ""))
        return latest.get("name", "—")
    except Exception:
        return "—"


def _parse_minutes(cook_time_str: str) -> int:
    """Parse '1 jam 30 menit' → 90, '45 menit' → 45, dll."""
    import re
    total = 0
    jam   = re.search(r'(\d+)\s*jam',   cook_time_str or "", re.IGNORECASE)
    menit = re.search(r'(\d+)\s*menit', cook_time_str or "", re.IGNORECASE)
    if jam:   total += int(jam.group(1)) * 60
    if menit: total += int(menit.group(1))
    return total if total > 0 else 60


def _get_rekomendasi(recipes: list[dict], hour: int, n: int = 3) -> list[dict]:
    """Ambil n resep terbaik berdasarkan jam + match_score + cook_time."""
    if not recipes:
        return []

    def _score(r):
        menit = _parse_minutes(r.get("cook_time", ""))
        match = r.get("match_score", 0)
        if hour < 11:        # Pagi → sarapan ringan, prioritas cepat
            t = 1.0 if menit <= 30 else (0.5 if menit <= 60 else 0.2)
        elif hour < 15:      # Siang → makanan berat, prioritas match_score
            t = 1.0
        elif hour < 19:      # Sore → cemilan, sangat cepat
            t = 1.0 if menit <= 20 else (0.5 if menit <= 40 else 0.15)
        else:                # Malam → masakan cepat
            t = 1.0 if menit <= 30 else (0.4 if menit <= 60 else 0.1)
        return match * t

    return sorted(recipes, key=_score, reverse=True)[:n]


def _rek_label_for_hour(hour: int) -> str:
    if hour < 11:   return "Sarapan Ringan ☀️"
    elif hour < 15: return "Makan Siang 🍛"
    elif hour < 19: return "Cemilan Sore 🌤"
    else:           return "Masakan Cepat Malam 🌙"


# ── Greeting ───────────────────────────────────────────────────────────────────

def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 11:   return "Selamat pagi ☀️"
    elif hour < 15: return "Selamat siang 🌤"
    elif hour < 19: return "Selamat sore 🌇"
    else:           return "Selamat malam 🌙"


# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _ghost_badge(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, color=WHITE, size=11, weight=ft.FontWeight.W_500),
        bgcolor=ft.Colors.with_opacity(0.22, WHITE),
        border_radius=ft.BorderRadius.all(20),
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.35, WHITE)),
    )


def _section_title(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=15,
        weight=ft.FontWeight.BOLD,
        color=TEXT(),
        font_family="Font",
    )


# ── Hero card ──────────────────────────────────────────────────────────────────

def _build_hero(recipe: dict, on_detail) -> ft.Container:
    name    = recipe.get("name", "Resep")
    img_url = recipe.get("image_url", "")
    portion = recipe.get("portion", "—")
    ctime   = recipe.get("cook_time", "—")

    hero = ft.Container(
        content=ft.Stack([
            ft.Image(
                src=img_url or "",
                width=float("inf"),
                height=220,
                fit=ft.BoxFit.COVER,
                error_content=ft.Container(
                    bgcolor=BG4(),
                    content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3(), size=48),
                    alignment=ft.Alignment(0, 0),
                    width=float("inf"),
                    height=220,
                ),
            ),
            ft.Container(
                width=float("inf"),
                height=220,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(0, 1),
                    end=ft.Alignment(0, -0.3),
                    colors=["#E0000000", "#60000000", "#00000000"],
                ),
            ),
            ft.Container(
                width=float("inf"),
                height=220,
                alignment=ft.Alignment(-1, 1),
                padding=ft.Padding.only(left=18, right=18, bottom=16),
                content=ft.Column(
                    controls=[
                        ft.Text(
                            name,
                            color=WHITE,
                            size=22,
                            weight=ft.FontWeight.W_800,
                            font_family="Font",
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            controls=[
                                _ghost_badge(f"👥 {portion}"),
                                _ghost_badge(f"⏱ {ctime}"),
                            ],
                            spacing=6,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
            ),
            ft.Container(
                width=float("inf"),
                height=220,
                alignment=ft.Alignment(1, 1),
                padding=ft.Padding.only(right=16, bottom=16),
                content=ft.Container(
                    content=ft.Text(
                        "Lihat Resep →",
                        color=WHITE,
                        size=12.5,
                        weight=ft.FontWeight.W_600,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.18, WHITE),
                    border_radius=ft.BorderRadius.all(20),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=7),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.4, WHITE)),
                    on_click=lambda e: on_detail(recipe),
                    ink=True,
                    ink_color=ft.Colors.with_opacity(0.15, WHITE),
                ),
            ),
        ]),
        border_radius=ft.BorderRadius.all(14),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        height=220,
        on_click=lambda e: on_detail(recipe),
        ink=True,
        animate=ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT),
    )

    return hero


def _build_hero_empty() -> ft.Container:
    return ft.Container(
        height=220,
        bgcolor=BG3(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(14),
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, color=TEXT3(), size=44),
                ft.Container(height=8),
                ft.Text(
                    "Belum ada resep",
                    color=TEXT2(), size=14,
                    weight=ft.FontWeight.BOLD,
                    font_family="Font",
                ),
                ft.Text(
                    "Cari resep di Finder agar muncul di sini",
                    color=TEXT3(), size=12,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            tight=True,
        ),
    )


# ── Rekomendasi card ───────────────────────────────────────────────────────────

def _build_rekomendasi_card(recipe: dict, on_detail) -> ft.Container:
    img_url = recipe.get("image_url", "")
    name    = recipe.get("name", "Resep")
    ctime   = recipe.get("cook_time", "—")

    return ft.Container(
        expand=True,
        content=ft.Column(
            controls=[
                ft.Container(
                    height=150,
                    border_radius=ft.BorderRadius.all(10),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Image(
                        src=img_url,
                        fit=ft.BoxFit.COVER,
                        width=float("inf"),
                        height=150,
                        error_content=ft.Container(
                            bgcolor=BG4(),
                            content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3(), size=32),
                            alignment=ft.Alignment(0, 0),
                        ),
                    ),
                ),
                ft.Container(height=8),
                ft.Text(
                    name, size=13, weight=ft.FontWeight.W_600,
                    color=TEXT(), font_family="Font",
                    max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TIMER_OUTLINED, size=11, color=TEXT3()),
                        ft.Text(ctime, size=12, color=TEXT3(), font_family="Font"),
                    ],
                    spacing=3,
                ),
            ],
            spacing=0,
            tight=True,
        ),
        bgcolor=BG3(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(14),
        padding=ft.Padding.all(12),
        on_click=lambda e: on_detail(recipe),
        ink=True,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )


# ── Stat cards ─────────────────────────────────────────────────────────────────

def _build_stat_card(val: str, label: str, icon: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(icon, size=22),
                ft.Container(height=2),
                ft.Text(
                    val,
                    size=20,
                    weight=ft.FontWeight.W_800,
                    color=ORANGE,
                    font_family="Font",
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    label,
                    size=11,
                    color=TEXT2(),
                    font_family="Font",
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=2,
            tight=True,
        ),
        bgcolor=BG3(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(12),
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        expand=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — build_home_page
# ══════════════════════════════════════════════════════════════════════════════

def build_home_page(
    page        : ft.Page,
    navigate_fn : callable,
    on_detail   : callable,
) -> ft.Container:

    _refs: dict = {}

    # ── Greeting ──────────────────────────────────────────────────────────────
    greeting_text = ft.Text(
        _greeting(),
        size=24,
        weight=ft.FontWeight.W_800,
        color=TEXT(),
        font_family="Font",
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
    )
    sub_text = ft.Text(
        "Mau masak apa hari ini?",
        size=13,
        color=TEXT2(),
        font_family="Font",
    )

    # ── Search field ──────────────────────────────────────────────────────────
    search_field = ft.TextField(
        hint_text="cth: bawang putih, tomat, telur...",
        hint_style=ft.TextStyle(color=TEXT3()),
        bgcolor=BG3(),
        color=TEXT(),
        focused_border_color=ORANGE,
        border_color=BORDER(),
        border_radius=ft.BorderRadius.all(28),
        content_padding=ft.Padding.symmetric(horizontal=24, vertical=14),
        expand=True,
    )

    search_btn_container = ft.Container(
        scale=ft.Scale(scale=1.0),
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
    )

    def _do_search(e):
        async def _anim():
            search_btn_container.scale = ft.Scale(scale=0.93)
            search_btn_container.update()
            await asyncio.sleep(0.08)
            search_btn_container.scale = ft.Scale(scale=1.0)
            search_btn_container.update()
            query = search_field.value.strip()
            navigate_fn("finder", query=query)
        page.run_task(_anim)

    search_field.on_submit = _do_search

    search_btn = ft.ElevatedButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SEARCH, color=WHITE, size=16),
                ft.Text("Cari", color=WHITE, weight=ft.FontWeight.BOLD, font_family="Font"),
            ],
            spacing=6,
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor=ORANGE,
            shape=ft.RoundedRectangleBorder(radius=28),
            mouse_cursor=ft.MouseCursor.CLICK,
            padding=ft.Padding.symmetric(horizontal=26, vertical=14),
            overlay_color={"hovered": "#d94410", "pressed": "#c03b0d", "": ORANGE},
        ),
        on_click=_do_search,
    )
    search_btn_container.content = search_btn

    # ── Hero card ─────────────────────────────────────────────────────────────
    recipes  = _load_all_recipes()
    hari_ini = _get_resep_hari_ini(recipes)

    hero_inner = (
        _build_hero(hari_ini, on_detail)
        if hari_ini
        else _build_hero_empty()
    )

    hero_wrap = ft.Container(
        content=hero_inner,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        opacity=0.0,
        offset=ft.Offset(0, 0.08),
    )

    # ── Stat cards ────────────────────────────────────────────────────────────
    my_recipes  = _load_my_recipes()
    last_opened = _get_last_opened()

    saved_val_text = ft.Text(
        str(len(my_recipes)),
        size=20, weight=ft.FontWeight.W_800,
        color=ORANGE, font_family="Font",
        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
    )
    last_val_text = ft.Text(
        last_opened,
        size=14 if len(last_opened) > 10 else 20,
        weight=ft.FontWeight.W_800,
        color=ORANGE, font_family="Font",
        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
    )

    def _make_stat_card(val_text: ft.Text, label: str, icon: str):
        label_text = ft.Text(
            label, size=11, color=TEXT2(),
            font_family="Font",
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        )
        card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(icon, size=22),
                    ft.Container(height=2),
                    val_text,
                    label_text,
                ],
                spacing=2,
                tight=True,
            ),
            bgcolor=BG3(),
            border=ft.Border.all(1, BORDER()),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            expand=True,
        )
        return card, label_text

    saved_card, saved_label_text = _make_stat_card(saved_val_text, "Resep Tersimpan", "📚")
    last_card,  last_label_text  = _make_stat_card(last_val_text,  "Terakhir Dibuka", "🕐")

    stat_row = ft.Row(controls=[saved_card, last_card], spacing=12)

    # ── Rekomendasi berdasarkan waktu ─────────────────────────────────────────
    # FIX: blok ini harus di dalam build_home_page, bukan di module level
    _hour     = datetime.now().hour
    _rek_data = _get_rekomendasi(recipes, _hour)

    title_rekomendasi = ft.Text(
        _rek_label_for_hour(_hour),
        size=15, weight=ft.FontWeight.BOLD,
        color=TEXT(), font_family="Font",
    )

    rekomendasi_row = ft.Row(
        controls=(
            [_build_rekomendasi_card(r, on_detail) for r in _rek_data]
            if _rek_data else
            [ft.Text("Belum ada data resep.", color=TEXT3(), size=12, font_family="Font")]
        ),
        spacing=12,
        expand=True,
    )

    # ── Named refs untuk theme rebuild ───────────────────────────────────────
    hint_text      = ft.Text(
        "💡 Pisahkan bahan dengan koma, tekan Enter atau Cari",
        size=11.5, color=TEXT3(), font_family="Font", italic=True,
    )
    title_hari_ini = ft.Text(
        "Resep Hari Ini 🔥", size=15, weight=ft.FontWeight.BOLD,
        color=TEXT(), font_family="Font",
    )

    # ── Assemble scroll content ───────────────────────────────────────────────
    scroll_col = ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[greeting_text, sub_text],
                    spacing=4, tight=True,
                ),
                padding=ft.Padding.only(bottom=18),
            ),
            ft.Container(
                content=ft.Row(
                    controls=[search_field, search_btn_container],
                    spacing=10,
                ),
                padding=ft.Padding.only(bottom=4),
            ),
            hint_text,
            ft.Container(height=20),

            title_hari_ini,
            ft.Container(height=8),
            hero_wrap,
            ft.Container(height=20),

            stat_row,
            ft.Container(height=20),

            title_rekomendasi,
            ft.Container(height=8),
            rekomendasi_row,
            ft.Container(height=24),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    container = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Container(
            content=scroll_col,
            padding=ft.Padding.symmetric(horizontal=24, vertical=20),
            expand=True,
        ),
    )

    # ── Entrance animation ────────────────────────────────────────────────────
    async def _entrance():
        await asyncio.sleep(0.05)
        hero_wrap.opacity = 1.0
        hero_wrap.offset  = ft.Offset(0, 0)
        if hero_wrap.page:
            hero_wrap.update()

    page.run_task(_entrance)

    # ── Refresh data ──────────────────────────────────────────────────────────
    def refresh():
        new_recipes  = _load_all_recipes()
        new_hari_ini = _get_resep_hari_ini(new_recipes)
        new_my       = _load_my_recipes()
        new_last     = _get_last_opened()

        greeting_text.value = _greeting()

        hero_wrap.content = (
            _build_hero(new_hari_ini, on_detail)
            if new_hari_ini
            else _build_hero_empty()
        )

        saved_val_text.value = str(len(new_my))
        last_val_text.value  = new_last
        last_val_text.size   = 14 if len(new_last) > 10 else 20

        # Update rekomendasi
        new_hour  = datetime.now().hour
        new_rek   = _get_rekomendasi(new_recipes, new_hour)
        title_rekomendasi.value  = _rek_label_for_hour(new_hour)
        rekomendasi_row.controls = (
            [_build_rekomendasi_card(r, on_detail) for r in new_rek]
            if new_rek else
            [ft.Text("Belum ada data resep.", color=TEXT3(), size=12)]
        )

        # Reset scroll ke atas
        try:
            scroll_col.scroll_to(offset=0, duration=0)
        except Exception:
            pass

        try:
            greeting_text.update()
            hero_wrap.update()
            saved_val_text.update()
            last_val_text.update()
            title_rekomendasi.update()
            rekomendasi_row.update()
        except Exception:
            pass

    container.refresh = refresh

    # ── Theme rebuild ─────────────────────────────────────────────────────────
    def _rebuild_theme():
        container.bgcolor         = BG()
        greeting_text.color       = TEXT()
        sub_text.color            = TEXT2()
        search_field.bgcolor      = BG3()
        search_field.color        = TEXT()
        search_field.border_color = BORDER()
        saved_val_text.color      = ORANGE
        last_val_text.color       = ORANGE
        saved_card.bgcolor        = BG3()
        saved_card.border         = ft.Border.all(1, BORDER())
        last_card.bgcolor         = BG3()
        last_card.border          = ft.Border.all(1, BORDER())
        saved_label_text.color    = TEXT2()
        last_label_text.color     = TEXT2()
        hint_text.color           = TEXT3()
        title_hari_ini.color      = TEXT()
        title_rekomendasi.color   = TEXT()
        for card in rekomendasi_row.controls:
            if hasattr(card, "bgcolor"):
                card.bgcolor = BG3()
                card.border  = ft.Border.all(1, BORDER())
                try:
                    card.update()
                except Exception:
                    pass
        try:
            container.update()
            greeting_text.update()
            sub_text.update()
            search_field.update()
            saved_val_text.update()
            last_val_text.update()
            saved_card.update()
            last_card.update()
            saved_label_text.update()
            last_label_text.update()
            hint_text.update()
            title_hari_ini.update()
            title_rekomendasi.update()
        except Exception:
            pass

    theme_mgr.add_listener(_rebuild_theme)

    return container