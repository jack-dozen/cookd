"""
home.py — CookD
════════════════════════════════════════════════════════════════
Halaman Home: landing page pertama yang dilihat user.

Konten:
  • Greeting dinamis (pagi / siang / sore / malam)
  • Search bar shortcut → navigate ke Finder
  • Hero card  : "Resep Hari Ini" (ambil dari DB, logika sama dgn for_you_ui)
  • Stat cards : Resep Tersimpan  |  Terakhir Dibuka
  • Quick action row: Finder, My Recipes, For You

Cara pakai (di Gui.py):
    from rafy.home import build_home_page

    home_page = build_home_page(
        page        = page,
        navigate_fn = navigate,          # fn(page_name: str)
        on_detail   = show_detail_fn,    # fn(recipe: dict)
    )
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
    """Resep terbaru (scraped_at) dengan match_score tertinggi — sama dgn for_you_ui."""
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


# ── Greeting ───────────────────────────────────────────────────────────────────

def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 11:
        return "Selamat pagi ☀️"
    elif hour < 15:
        return "Selamat siang 🌤"
    elif hour < 19:
        return "Selamat sore 🌇"
    else:
        return "Selamat malam 🌙"


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
    score   = recipe.get("match_score", 0)
    score_s = f"⭐ {score * 5:.1f}"

    hero = ft.Container(
        content=ft.Stack([
            # Gambar
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
            # Gradient gelap bawah
            ft.Container(
                width=float("inf"),
                height=220,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(0, 1),
                    end=ft.Alignment(0, -0.3),
                    colors=["#E0000000", "#60000000", "#00000000"],
                ),
            ),
            # Konten bawah
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
            # Tombol "Lihat Resep →" kanan bawah
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


# ── Quick action button ────────────────────────────────────────────────────────

def _build_quick_btn(
    icon,
    label: str,
    color: str,
    bg_color: str,
    on_click,
) -> ft.Container:
    icon_obj  = ft.Icon(icon, color=color, size=20)
    text_obj  = ft.Text(label, color=TEXT2(), size=12, font_family="Font")
    container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=icon_obj,
                    bgcolor=bg_color,
                    border_radius=ft.BorderRadius.all(12),
                    padding=ft.Padding.all(12),
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(height=6),
                text_obj,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            tight=True,
        ),
        bgcolor=BG3(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(12),
        padding=ft.Padding.symmetric(horizontal=10, vertical=14),
        expand=True,
        on_click=on_click,
        ink=True,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )

    def on_hover(e):
        container.border = ft.Border.all(1, color if e.data else BORDER())
        icon_obj.color   = color
        text_obj.color   = TEXT() if e.data else TEXT2()
        container.update()
        icon_obj.update()
        text_obj.update()

    container.on_hover = on_hover
    return container


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — build_home_page
# ══════════════════════════════════════════════════════════════════════════════

def build_home_page(
    page        : ft.Page,
    navigate_fn : callable,
    on_detail   : callable,
) -> ft.Container:
    """
    Bangun halaman Home.

    Args:
        page        : ft.Page aktif
        navigate_fn : fn(page_name: str) — untuk navigasi ke halaman lain
        on_detail   : fn(recipe: dict)   — buka halaman detail resep

    Returns:
        ft.Container — siap dipakai sebagai salah satu halaman di content stack
    """

    # ── Mutable state ─────────────────────────────────────────────────────────
    _refs: dict = {
        "hero_wrap"    : None,   # ft.Container wrapper hero
        "stat_saved"   : None,   # ft.Text nilai saved count
        "stat_last"    : None,   # ft.Text nilai last opened
        "greeting_text": None,   # ft.Text greeting
        "search_field" : None,   # ft.TextField
    }

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
    _refs["greeting_text"] = greeting_text

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
    _refs["search_field"] = search_field

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
            # Kirim query langsung via navigate_fn — tanpa page.session
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
    _refs["hero_wrap"] = hero_wrap

    # ── Stat cards ────────────────────────────────────────────────────────────
    my_recipes   = _load_my_recipes()
    saved_count  = str(len(my_recipes))
    last_opened  = _get_last_opened()

    # Refs utk theme rebuild
    saved_val_text = ft.Text(
        saved_count,
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
    _refs["stat_saved"] = saved_val_text
    _refs["stat_last"]  = last_val_text

    def _make_stat_card(val_text: ft.Text, label: str, icon: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(icon, size=22),
                    ft.Container(height=2),
                    val_text,
                    ft.Text(
                        label, size=11, color=TEXT2(),
                        font_family="Font",
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
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

    stat_row = ft.Row(
        controls=[
            _make_stat_card(saved_val_text, "Resep Tersimpan", "📚"),
            _make_stat_card(last_val_text,  "Terakhir Dibuka", "🕐"),
        ],
        spacing=12,
    )

    # ── Quick actions ─────────────────────────────────────────────────────────
    quick_actions = ft.Row(
        controls=[
            _build_quick_btn(
                ft.Icons.SEARCH_OUTLINED,
                "Finder",
                ORANGE,
                ft.Colors.with_opacity(0.15, ORANGE),
                on_click=lambda e: navigate_fn("finder"),
            ),
            _build_quick_btn(
                ft.Icons.BOOK_OUTLINED,
                "My Recipes",
                "#2E9E5B",
                ft.Colors.with_opacity(0.15, "#2E9E5B"),
                on_click=lambda e: navigate_fn("my-recipes"),
            ),
            _build_quick_btn(
                ft.Icons.STAR_OUTLINE,
                "For You",
                "#1A6FBF",
                ft.Colors.with_opacity(0.15, "#1A6FBF"),
                on_click=lambda e: navigate_fn("for-you"),
            ),
        ],
        spacing=10,
    )

    # ── Assemble scroll content ───────────────────────────────────────────────
    scroll_col = ft.Column(
        controls=[
            # Greeting
            ft.Container(
                content=ft.Column(
                    controls=[greeting_text, sub_text],
                    spacing=4,
                    tight=True,
                ),
                padding=ft.Padding.only(bottom=18),
            ),
            # Search bar
            ft.Container(
                content=ft.Row(
                    controls=[search_field, search_btn_container],
                    spacing=10,
                ),
                padding=ft.Padding.only(bottom=4),
            ),
            ft.Text(
                "💡 Pisahkan bahan dengan koma, tekan Enter atau Cari",
                size=11.5,
                color=TEXT3(),
                font_family="Font",
                italic=True,
            ),
            ft.Container(height=20),

            # Resep Hari Ini
            _section_title("Resep Hari Ini 🔥"),
            ft.Container(height=8),
            hero_wrap,
            ft.Container(height=20),

            # Stat cards
            stat_row,
            ft.Container(height=20),

            # Quick actions
            _section_title("Menu Cepat"),
            ft.Container(height=8),
            quick_actions,
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

    # ── Entrance animation (saat halaman pertama kali visible) ────────────────
    async def _entrance():
        await asyncio.sleep(0.05)
        hero_wrap.opacity = 1.0
        hero_wrap.offset  = ft.Offset(0, 0)
        if hero_wrap.page:
            hero_wrap.update()

    page.run_task(_entrance)

    # ── Refresh data (dipanggil dari luar saat kembali ke home) ───────────────
    def refresh():
        """
        Panggil ini dari navigate_fn ketika user kembali ke Home
        agar stat cards & hero diperbarui.
        """
        new_recipes  = _load_all_recipes()
        new_hari_ini = _get_resep_hari_ini(new_recipes)
        new_my       = _load_my_recipes()
        new_last     = _get_last_opened()

        # Update greeting (jam bisa berubah)
        greeting_text.value = _greeting()

        # Update hero
        new_hero = (
            _build_hero(new_hari_ini, on_detail)
            if new_hari_ini
            else _build_hero_empty()
        )
        hero_wrap.content = new_hero

        # Update stat cards
        saved_val_text.value = str(len(new_my))
        lv = new_last
        last_val_text.value  = lv
        last_val_text.size   = 14 if len(lv) > 10 else 20

        try:
            greeting_text.update()
            hero_wrap.update()
            saved_val_text.update()
            last_val_text.update()
        except Exception:
            pass

    container.refresh = refresh

    # ── Theme rebuild ─────────────────────────────────────────────────────────
    def _rebuild_theme():
        container.bgcolor       = BG()
        greeting_text.color     = TEXT()
        sub_text.color          = TEXT2()
        search_field.bgcolor    = BG3()
        search_field.color      = TEXT()
        search_field.border_color = BORDER()
        saved_val_text.color    = ORANGE
        last_val_text.color     = ORANGE
        try:
            container.update()
            greeting_text.update()
            sub_text.update()
            search_field.update()
            saved_val_text.update()
            last_val_text.update()
        except Exception:
            pass

    theme_mgr.add_listener(_rebuild_theme)

    return container