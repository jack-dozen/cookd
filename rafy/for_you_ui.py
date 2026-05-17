"""
for_you_ui.py
════════════════════════════════════════════════════════════════
Halaman ResepForYou — rekomendasi resep berbasis aktivitas user.

Algoritma:
  • Resep Hari Ini  : scraped_at terbaru + match_score tertinggi
  • Resep Bulan Ini : skor = match_score×0.6 + frekuensi_kalkulasi×0.4 (top 5)

Cara pakai (di Gui.py):
    from rafy.for_you_ui import build_for_you_page

    content = build_for_you_page(
        page=page,
        on_detail=lambda r: navigate_to_detail(r),
        on_save=lambda r, saved: save_recipe(r, saved),
    )
════════════════════════════════════════════════════════════════
"""

import flet as ft
import os
import sys
from datetime import datetime, date
from collections import Counter

# ── Path resolver ──────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from rafy.theme import (
    theme_mgr, ORANGE, GREEN, AMBER, WHITE,
)
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
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


# ══════════════════════════════════════════════════════════════════════════════
# DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════

def _load_all_recipes() -> list[dict]:
    try:
        return _get_db().table("cookpad_recipes").all()
    except Exception as e:
        print(f"[for_you_ui] Gagal baca cookpad_recipes: {e}")
        return []


def _load_result_frequency() -> dict[str, int]:
    """Hitung berapa kali tiap recipe_id muncul di tabel results."""
    try:
        results = _get_db().table("results").all()
        freq    = Counter(
            r.get("recipe_id", "") for r in results if r.get("recipe_id")
        )
        return dict(freq)
    except Exception as e:
        print(f"[for_you_ui] Gagal baca results: {e}")
        return {}


def _parse_scraped_at(r: dict) -> date:
    try:
        return datetime.strptime(r.get("scraped_at", ""), "%Y-%m-%d %H:%M:%S").date()
    except Exception:
        return date.min


def _get_resep_hari_ini(recipes: list[dict]) -> dict | None:
    """
    1. Cari tanggal scraped_at paling baru.
    2. Dari grup tanggal itu, ambil match_score tertinggi.
    """
    if not recipes:
        return None
    latest_date  = max(_parse_scraped_at(r) for r in recipes)
    latest_group = [r for r in recipes if _parse_scraped_at(r) == latest_date]
    return max(latest_group, key=lambda r: r.get("match_score", 0))


def _get_resep_bulan_ini(
    recipes   : list[dict],
    freq      : dict[str, int],
    exclude_id: str = "",
) -> list[dict]:
    """
    Top 5 resep bulan ini.
    skor = match_score × 0.6 + (frekuensi / max_frekuensi) × 0.4
    Fallback ke semua resep jika bulan ini kosong.
    """
    now = datetime.now()

    def _in_month(r: dict) -> bool:
        try:
            d = datetime.strptime(r.get("scraped_at", ""), "%Y-%m-%d %H:%M:%S")
            return d.year == now.year and d.month == now.month
        except Exception:
            return False

    pool = [r for r in recipes if r.get("recipe_id") != exclude_id]
    monthly = [r for r in pool if _in_month(r)]
    if not monthly:
        monthly = pool   # fallback

    if not monthly:
        return []

    max_freq = max(freq.values()) if freq else 1

    def _score(r: dict) -> float:
        ms = r.get("match_score", 0)
        f  = freq.get(r.get("recipe_id", ""), 0)
        return ms * 0.6 + (f / max_freq) * 0.4

    ranked = sorted(monthly, key=_score, reverse=True)

    # Deduplicate by recipe_id, ambil top 5
    seen, result = set(), []
    for r in ranked:
        rid = r.get("recipe_id", "")
        if rid and rid not in seen:
            seen.add(rid)
            result.append(r)
        if len(result) >= 5:
            break
    return result


# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_score(score: float) -> str:
    return f"⭐ {score * 5:.1f}"


def _fmt_portion(s) -> str:
    return f"👥 {s}" if s and s != "-" else "👥 —"


def _fmt_time(s) -> str:
    return f"⏱ {s}" if s and s != "-" else "⏱ —"


def _thumbnail(url: str, width: int, height: int) -> ft.Container:
    return ft.Container(
        content=ft.Image(
            src=url or "",
            width=width,
            height=height,
            fit=ft.BoxFit.COVER,
            error_content=ft.Container(
                bgcolor=BG4(),
                content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3(), size=28),
                alignment=ft.Alignment(0, 0),
                width=width,
                height=height,
            ),
        ),
        width=width,
        height=height,
        border_radius=ft.BorderRadius.all(10),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        bgcolor=BG4(),
    )


def _ghost_badge(text: str) -> ft.Container:
    """Badge transparan putih — untuk hero card."""
    return ft.Container(
        content=ft.Text(text, color=WHITE, size=11, weight=ft.FontWeight.W_500),
        bgcolor=ft.Colors.with_opacity(0.22, WHITE),
        border_radius=ft.BorderRadius.all(20),
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.35, WHITE)),
    )


# ══════════════════════════════════════════════════════════════════════════════
# HERO CARD — Resep Hari Ini
# ══════════════════════════════════════════════════════════════════════════════

def _build_hero(recipe: dict, on_detail) -> ft.Container:
    name    = recipe.get("name", "Resep")
    img_url = recipe.get("image_url", "")

    return ft.Container(
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
            # Gradient gelap bawah → atas
            ft.Container(
                width=float("inf"),
                height=220,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(0, 1),
                    end=ft.Alignment(0, -0.2),
                    colors=["#DD000000", "#00000000"],
                ),
            ),
            # Teks + badge di bawah
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        name, color=WHITE, size=21,
                        weight=ft.FontWeight.W_800,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Container(height=6),
                    ft.Row([
                        _ghost_badge(_fmt_portion(recipe.get("portion", "-"))),
                        _ghost_badge(_fmt_time(recipe.get("cook_time", "-"))),
                        _ghost_badge(_fmt_score(recipe.get("match_score", 0))),
                    ], spacing=6),
                ], spacing=0, tight=True),
                padding=ft.Padding.all(16),
                alignment=ft.Alignment(-1, 1),
                height=220,
            ),
            # Tombol kanan bawah
            ft.Container(
                content=ft.ElevatedButton(
                    ft.Text("Lihat Resep →"),
                    bgcolor=ft.Colors.with_opacity(0.18, WHITE),
                    color=WHITE,
                    on_click=lambda e: on_detail(recipe),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=20),
                        side=ft.BorderSide(1, ft.Colors.with_opacity(0.5, WHITE)),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=6),
                    ),
                ),
                alignment=ft.Alignment(1, 1),
                padding=ft.Padding.all(14),
                height=220,
            ),
        ]),
        height=220,
        border_radius=ft.BorderRadius.all(14),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=lambda e: on_detail(recipe),
        ink=True,
        animate=ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT),
    )


# ══════════════════════════════════════════════════════════════════════════════
# RANKED ROW — Resep Bulan Ini
# ══════════════════════════════════════════════════════════════════════════════

def _build_ranked_row(rank: int, recipe: dict, on_detail, on_save) -> ft.Container:
    name    = recipe.get("name", "Resep")
    portion = recipe.get("portion", "-")
    ctime   = recipe.get("cook_time", "-")
    source  = recipe.get("source", "Cookpad")
    img_url = recipe.get("image_url", "")

    # Warna nomor ranking: 1=orange, 2=abu, 3=amber, sisanya=redup
    rank_colors = {1: ORANGE, 2: TEXT2(), 3: AMBER}
    rank_color  = rank_colors.get(rank, TEXT3())

    heart_ref = ft.Ref[ft.IconButton]()

    def _toggle(e):
        btn   = heart_ref.current
        saved = not getattr(btn, "_saved", False)
        btn._saved     = saved
        btn.icon       = ft.Icons.FAVORITE if saved else ft.Icons.FAVORITE_BORDER
        btn.icon_color = "#E74C3C" if saved else TEXT2()
        on_save(recipe, saved)
        e.page.update()

    return ft.Container(
        content=ft.Row([
            # Nomor
            ft.Container(
                content=ft.Text(
                    str(rank), color=rank_color, size=20,
                    weight=ft.FontWeight.W_800,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=28,
            ),
            # Thumbnail
            _thumbnail(img_url, 68, 68),
            # Info
            ft.Column([
                ft.Text(
                    name, color=TEXT(), size=14,
                    weight=ft.FontWeight.BOLD,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    f"👥 {portion}  ⏱ {ctime}  · {source}",
                    color=TEXT2(), size=11,
                ),
            ], spacing=4, expand=True),
            # Aksi
            ft.Row([
                ft.IconButton(
                    ref=heart_ref,
                    icon=ft.Icons.FAVORITE_BORDER,
                    icon_color=TEXT2(),
                    icon_size=18,
                    tooltip="Simpan ke My Recipes",
                    on_click=_toggle,
                ),
                ft.ElevatedButton(
                    content=ft.Text("Lihat"),
                    color=ORANGE,
                    bgcolor=ft.Colors.with_opacity(0, ORANGE),
                    on_click=lambda e: on_detail(recipe),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        side=ft.BorderSide(1.5, ORANGE),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    ),
                ),
            ], spacing=2, tight=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=BG3(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(10),
        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        on_click=lambda e: on_detail(recipe),
        ink=True,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
    )


# ══════════════════════════════════════════════════════════════════════════════
# EMPTY STATE
# ══════════════════════════════════════════════════════════════════════════════

def _build_empty(message: str = "Belum ada resep") -> ft.Container:
    return ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, color=TEXT3(), size=44),
            ft.Text(message, color=TEXT2(), size=14, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Cari resep dulu di Recipe Finder\nagar muncul di sini.",
                color=TEXT3(), size=12, text_align=ft.TextAlign.CENTER,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           spacing=8, tight=True),
        padding=ft.Padding.all(40),
        alignment=ft.Alignment(0, 0),
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — build_for_you_page
# ══════════════════════════════════════════════════════════════════════════════

def build_for_you_page(
    page      : ft.Page,
    on_detail : callable,
    on_save   : callable,
) -> ft.Column:
    """
    Bangun halaman ResepForYou.

    Args:
        page      : ft.Page aktif
        on_detail : fn(recipe: dict) → buka halaman detail
        on_save   : fn(recipe: dict, saved: bool) → simpan / hapus dari my_recipes
    """
    recipes   = _load_all_recipes()
    freq      = _load_result_frequency()
    hari_ini  = _get_resep_hari_ini(recipes)
    bulan_ini = _get_resep_bulan_ini(
        recipes, freq,
        exclude_id=hari_ini.get("recipe_id", "") if hari_ini else "",
    )

    controls: list[ft.Control] = []

    # ── Resep Hari Ini ────────────────────────────────────────────────────────
    controls.append(
        ft.Text("Resep Hari Ini 🔥", color=TEXT(), size=15,
                weight=ft.FontWeight.BOLD)
    )

    controls.append(
        _build_hero(hari_ini, on_detail)
        if hari_ini else _build_empty("Belum ada resep hari ini")
    )

    controls.append(ft.Container(height=20))

    # ── Resep Bulan Ini ───────────────────────────────────────────────────────
    controls.append(
        ft.Row([
            ft.Text("Resep Bulan Ini 📅", color=TEXT(), size=15,
                    weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Text(
                    "kecocokan + frekuensi",
                    color=TEXT3(), size=10,
                ),
                bgcolor=BG4(),
                border_radius=ft.BorderRadius.all(20),
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            ),
        ], spacing=8)
    )

    if bulan_ini:
        for i, recipe in enumerate(bulan_ini, start=1):
            controls.append(_build_ranked_row(i, recipe, on_detail, on_save))
    else:
        controls.append(_build_empty("Belum ada resep bulan ini"))

    column = ft.Column(
        controls=controls,
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    def _rebuild_controls():
        """Rebuild isi column dengan warna tema terbaru. Aman dipanggil berulang."""
        new_recipes   = _load_all_recipes()
        new_freq      = _load_result_frequency()
        new_hari_ini  = _get_resep_hari_ini(new_recipes)
        new_bulan_ini = _get_resep_bulan_ini(
            new_recipes, new_freq,
            exclude_id=new_hari_ini.get("recipe_id", "") if new_hari_ini else "",
        )
        new_controls = []
        new_controls.append(
            ft.Text("Resep Hari Ini 🔥", color=TEXT(), size=15,
                    weight=ft.FontWeight.BOLD)
        )
        new_controls.append(
            _build_hero(new_hari_ini, on_detail)
            if new_hari_ini else _build_empty("Belum ada resep hari ini")
        )
        new_controls.append(ft.Container(height=20))
        new_controls.append(
            ft.Row([
                ft.Text("Resep Bulan Ini 📅", color=TEXT(), size=15,
                        weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text("kecocokan + frekuensi", color=TEXT3(), size=10),
                    bgcolor=BG4(),
                    border_radius=ft.BorderRadius.all(20),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                ),
            ], spacing=8)
        )
        if new_bulan_ini:
            for i, recipe in enumerate(new_bulan_ini, start=1):
                new_controls.append(_build_ranked_row(i, recipe, on_detail, on_save))
        else:
            new_controls.append(_build_empty("Belum ada resep bulan ini"))
        column.controls = new_controls
        try: column.update()
        except Exception: pass

    # Simpan rebuild fn ke atribut column agar bisa dipanggil dari luar
    # dan agar listener bisa di-deregister kalau perlu
    column._rebuild = _rebuild_controls

    # Daftarkan listener SEKALI — cek apakah sudah terdaftar via id fn
    if not any(getattr(f, '_foryou_listener', False) for f in theme_mgr._listeners):
        _rebuild_controls._foryou_listener = True
        theme_mgr.add_listener(_rebuild_controls)

    return column
