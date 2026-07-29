"""
home.py — CookD Home Page (formerly rafy/home.py)
"""

import asyncio
import os
import sys
from datetime import datetime

import flet as ft

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.theme import theme_mgr, ORANGE, WHITE
from tinydb import TinyDB

_DB_PATH = os.path.join(_ROOT, "data", "base.json")
_db_cache = None


def _get_db():
    global _db_cache
    if _db_cache is None:
        _db_cache = TinyDB(_DB_PATH)
    return _db_cache


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


def _load_all_recipes():
    try:
        return _get_db().table("cookpad_recipes").all()
    except Exception:
        return []


def _load_my_recipes():
    try:
        return _get_db().table("my_recipes").all()
    except Exception:
        return []


def _get_resep_hari_ini(recipes):
    if not recipes:
        return None
    from datetime import date

    def _parse(r):
        try:
            return datetime.strptime(r.get("scraped_at", ""), "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            return date.min

    latest_date = max(_parse(r) for r in recipes)
    latest_group = [r for r in recipes if _parse(r) == latest_date]
    return max(latest_group, key=lambda r: r.get("match_score", 0))


def _get_last_opened():
    try:
        results = _get_db().table("results").all()
        if not results:
            return ""
        latest = max(results, key=lambda r: r.get("opened_at", ""))
        return latest.get("name", "")
    except Exception:
        return ""


def _parse_minutes(cook_time_str):
    import re
    total = 0
    jam = re.search(r'(\d+)\s*jam', cook_time_str or "", re.IGNORECASE)
    menit = re.search(r'(\d+)\s*menit', cook_time_str or "", re.IGNORECASE)
    if jam:
        total += int(jam.group(1)) * 60
    if menit:
        total += int(menit.group(1))
    return total if total > 0 else 60


def _get_rekomendasi(recipes, hour, n=3):
    if not recipes:
        return []

    def _score(r):
        menit = _parse_minutes(r.get("cook_time", ""))
        match = r.get("match_score", 0)
        if hour < 11:
            t = 1.0 if menit <= 30 else (0.5 if menit <= 60 else 0.2)
        elif hour < 15:
            t = 1.0
        elif hour < 19:
            t = 1.0 if menit <= 20 else (0.5 if menit <= 40 else 0.15)
        else:
            t = 1.0 if menit <= 30 else (0.4 if menit <= 60 else 0.1)
        return match * t

    return sorted(recipes, key=_score, reverse=True)[:n]


def _rek_label_for_hour(hour):
    if hour < 11:
        return "Sarapan Ringan"
    elif hour < 15:
        return "Makan Siang"
    elif hour < 19:
        return "Cemilan Sore"
    return "Masakan Cepat Malam"


def _greeting():
    hour = datetime.now().hour
    if hour < 11:
        return "Selamat pagi"
    elif hour < 15:
        return "Selamat siang"
    elif hour < 19:
        return "Selamat sore"
    return "Selamat malam"


def _ghost_badge(text):
    return ft.Container(
        content=ft.Text(text, color=WHITE, size=11, weight=ft.FontWeight.W_500),
        bgcolor=ft.Colors.with_opacity(0.22, WHITE),
        border_radius=ft.BorderRadius.all(20),
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.35, WHITE)),
    )


def _build_hero(recipe, on_detail):
    name = recipe.get("name", "Resep")
    img_url = recipe.get("image_url", "")
    portion = recipe.get("portion", "")
    ctime = recipe.get("cook_time", "")

    return ft.Container(
        content=ft.Stack([
            ft.Image(src=img_url or "", width=float("inf"), height=220, fit=ft.BoxFit.COVER,
                     error_content=ft.Container(bgcolor=BG4(), content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3(), size=48), width=float("inf"), height=220, alignment=ft.Alignment(0, 0))),
            ft.Container(width=float("inf"), height=220, gradient=ft.LinearGradient(begin=ft.Alignment(0, 1), end=ft.Alignment(0, -0.3), colors=["#E0000000", "#60000000", "#00000000"])),
            ft.Container(content=ft.Column([ft.Text(name, color=WHITE, size=22, weight=ft.FontWeight.W_800, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS), ft.Row([_ghost_badge(f"{portion}"), _ghost_badge(f"{ctime}")], spacing=6)], spacing=6, tight=True), padding=ft.Padding.only(left=18, right=18, bottom=16), alignment=ft.Alignment(-1, 1), height=220),
            ft.Container(content=ft.Container(content=ft.Text("Lihat Resep", color=WHITE, size=12.5, weight=ft.FontWeight.W_600), bgcolor=ft.Colors.with_opacity(0.18, WHITE), border_radius=ft.BorderRadius.all(20), padding=ft.Padding.symmetric(horizontal=14, vertical=7), border=ft.Border.all(1, ft.Colors.with_opacity(0.4, WHITE)), on_click=lambda e: on_detail(recipe), ink=True), alignment=ft.Alignment(1, 1), padding=ft.Padding.only(right=16, bottom=16), height=220),
        ]),
        border_radius=ft.BorderRadius.all(14), clip_behavior=ft.ClipBehavior.HARD_EDGE, height=220, on_click=lambda e: on_detail(recipe), ink=True,
    )


def _build_hero_empty():
    return ft.Container(height=220, bgcolor=BG3(), border=ft.Border.all(1, BORDER()), border_radius=ft.BorderRadius.all(14), alignment=ft.Alignment(0, 0),
                        content=ft.Column([ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, color=TEXT3(), size=44), ft.Container(height=8), ft.Text("Belum ada resep", color=TEXT2(), size=14, weight=ft.FontWeight.BOLD), ft.Text("Cari resep di Finder", color=TEXT3(), size=12)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, tight=True))


def _build_rekomendasi_card(recipe, on_detail):
    return ft.Container(
        expand=True,
        content=ft.Column([
            ft.Container(height=150, border_radius=ft.BorderRadius.all(10), clip_behavior=ft.ClipBehavior.HARD_EDGE,
                         content=ft.Image(src=recipe.get("image_url", ""), fit=ft.BoxFit.COVER, width=float("inf"), height=150,
                                          error_content=ft.Container(bgcolor=BG4(), content=ft.Icon(ft.Icons.RESTAURANT, color=TEXT3(), size=32), alignment=ft.Alignment(0, 0)))),
            ft.Container(height=8),
            ft.Text(recipe.get("name", ""), size=13, weight=ft.FontWeight.W_600, color=TEXT(), max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Row([ft.Icon(ft.Icons.TIMER_OUTLINED, size=11, color=TEXT3()), ft.Text(recipe.get("cook_time", ""), size=12, color=TEXT3())], spacing=3),
        ], spacing=0, tight=True),
        bgcolor=BG3(), border=ft.Border.all(1, BORDER()), border_radius=ft.BorderRadius.all(14), padding=ft.Padding.all(12),
        on_click=lambda e: on_detail(recipe), ink=True,
    )


def build_home_page(page, navigate_fn, on_detail):
    greeting_text = ft.Text(_greeting(), size=24, weight=ft.FontWeight.W_800, color=TEXT())
    sub_text = ft.Text("Mau masak apa hari ini?", size=13, color=TEXT2())
    search_field = ft.TextField(hint_text="cth: bawang putih, tomat, telur...", hint_style=ft.TextStyle(color=TEXT3()), bgcolor=BG3(), color=TEXT(), focused_border_color=ORANGE, border_color=BORDER(), border_radius=ft.BorderRadius.all(28), content_padding=ft.Padding.symmetric(horizontal=24, vertical=14), expand=True)

    search_btn = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.SEARCH, color=WHITE, size=16), ft.Text("Cari", color=WHITE, weight=ft.FontWeight.BOLD)], spacing=6, tight=True), style=ft.ButtonStyle(bgcolor=ORANGE, shape=ft.RoundedRectangleBorder(radius=28), padding=ft.Padding.symmetric(horizontal=26, vertical=14)), on_click=lambda e: navigate_fn("finder", query=search_field.value.strip()))
    search_field.on_submit = lambda e: navigate_fn("finder", query=search_field.value.strip())

    recipes = _load_all_recipes()
    hari_ini = _get_resep_hari_ini(recipes)
    hero_inner = _build_hero(hari_ini, on_detail) if hari_ini else _build_hero_empty()
    hero_wrap = ft.Container(content=hero_inner, animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT), opacity=0.0)

    my_recipes = _load_my_recipes()
    last_opened = _get_last_opened()
    saved_val_text = ft.Text(str(len(my_recipes)), size=20, weight=ft.FontWeight.W_800, color=ORANGE)
    last_val_text = ft.Text(last_opened if last_opened else "-", size=14, weight=ft.FontWeight.W_800, color=ORANGE)

    def _make_stat_card(vt, label, icon):
        return ft.Container(content=ft.Column([icon, ft.Container(height=2), vt, ft.Text(label, size=11, color=TEXT2())], spacing=2, tight=True), bgcolor=BG3(), border=ft.Border.all(1, BORDER()), border_radius=ft.BorderRadius.all(12), padding=ft.Padding.symmetric(horizontal=16, vertical=14), expand=True)

    saved_card = _make_stat_card(saved_val_text, "Resep Tersimpan", ft.Icon(ft.Icons.BOOK_OUTLINED, color=ORANGE, size=22))
    last_card = _make_stat_card(last_val_text, "Terakhir Dibuka", ft.Icon(ft.Icons.ACCESS_TIME, color=ORANGE, size=22))
    stat_row = ft.Row([saved_card, last_card], spacing=12)

    _hour = datetime.now().hour
    _rek_data = _get_rekomendasi(recipes, _hour)
    title_rekomendasi = ft.Text(_rek_label_for_hour(_hour), size=15, weight=ft.FontWeight.BOLD, color=TEXT())
    rekomendasi_row = ft.Row([_build_rekomendasi_card(r, on_detail) for r in _rek_data] if _rek_data else [ft.Text("Belum ada data", color=TEXT3(), size=12)], spacing=12, expand=True)
    title_hari_ini = ft.Text("Resep Hari Ini", size=15, weight=ft.FontWeight.BOLD, color=TEXT())

    scroll_col = ft.Column([ft.Container(content=ft.Column([greeting_text, sub_text], spacing=4), padding=ft.Padding.only(bottom=18)), ft.Row([search_field, search_btn], spacing=10), ft.Container(height=20), title_hari_ini, ft.Container(height=8), hero_wrap, ft.Container(height=20), stat_row, ft.Container(height=20), title_rekomendasi, ft.Container(height=8), rekomendasi_row], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    container = ft.Container(expand=True, bgcolor=BG(), visible=False, content=ft.Container(content=scroll_col, padding=ft.Padding.symmetric(horizontal=24, vertical=20), expand=True))

    async def _entrance():
        await asyncio.sleep(0.05)
        hero_wrap.opacity = 1.0
        if hero_wrap.page:
            hero_wrap.update()

    page.run_task(_entrance)

    def refresh():
        new_recipes = _load_all_recipes()
        new_hari_ini = _get_resep_hari_ini(new_recipes)
        new_my = _load_my_recipes()
        new_last = _get_last_opened()
        greeting_text.value = _greeting()
        hero_wrap.content = _build_hero(new_hari_ini, on_detail) if new_hari_ini else _build_hero_empty()
        saved_val_text.value = str(len(new_my))
        last_val_text.value = new_last if new_last else "-"
        new_hour = datetime.now().hour
        new_rek = _get_rekomendasi(new_recipes, new_hour)
        title_rekomendasi.value = _rek_label_for_hour(new_hour)
        rekomendasi_row.controls = [_build_rekomendasi_card(r, on_detail) for r in new_rek] if new_rek else [ft.Text("Belum ada data", color=TEXT3(), size=12)]
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

    def _rebuild_theme():
        container.bgcolor = BG()
        greeting_text.color = TEXT()
        sub_text.color = TEXT2()
        search_field.bgcolor = BG3()
        search_field.color = TEXT()
        search_field.border_color = BORDER()
        saved_val_text.color = ORANGE
        last_val_text.color = ORANGE
        saved_card.bgcolor = BG3()
        saved_card.border = ft.Border.all(1, BORDER())
        last_card.bgcolor = BG3()
        last_card.border = ft.Border.all(1, BORDER())
        try:
            container.update()
        except Exception:
            pass

    theme_mgr.add_listener(_rebuild_theme)
    return container
