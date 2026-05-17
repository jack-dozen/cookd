import asyncio
import threading
import flet as ft
import flet_lottie as ftl
from hadi import CookpadScraper
from rafy.theme import theme_mgr, ORANGE, ORANGE_GLOW, GREEN, AMBER, WHITE


def BG():     return theme_mgr.get("BG")
def BG2():    return theme_mgr.get("BG2")
def BG3():    return theme_mgr.get("BG3")
def BG4():    return theme_mgr.get("BG4")
def TEXT():   return theme_mgr.get("TEXT")
def TEXT2():  return theme_mgr.get("TEXT2")
def TEXT3():  return theme_mgr.get("TEXT3")
def BORDER(): return theme_mgr.get("BORDER")


COOKING_STAGES = [
    ("Preparing Ingredients...",    "Fetching page"),
    ("Cracking the Recipe Open...", "Parsing HTML"),
    ("Mixing the Instructions...",  "Extracting steps"),
    ("Gathering Ingredients...",    "Building card"),
    ("Sliding into the Oven...",    "Loading"),
    ("Serving Your Recipe!....",    "Almost done"),
]

_FLOAT_EMOJIS = [
    ("🧄", 0.0,  10, 2.6),
    ("🍅", 0.0,   8, 2.1),
    ("🥚", 0.0,  12, 3.0),
    ("🧅", 0.0,   9, 2.4),
    ("🌶️", 0.0, 11, 2.8),
]

PAGE_SIZE = 10


def build_finder_page(page: ft.Page, show_detail_fn) -> ft.Container:
    """
    Bangun halaman Finder.

    Setelah memanggil fungsi ini, simpan hasilnya di page.session agar
    Home bisa langsung menjalankan pencarian:

        finder_page = build_finder_page(page, show_detail_fn)
        page.session.set("finder_ref", finder_page)

    Dengan begitu, search bar di Home akan otomatis mengisi & menjalankan
    pencarian di Finder tanpa user harus menekan tombol lagi.
    """

    # ── State ─────────────────────────────────────────────────────────────────
    _search_mode  = {"value": "scrape"}
    _stop_event   = {"value": None}
    _is_scraping  = {"value": False}
    _last_query   = {"value": ""}

    # FIX: session counter — each new search gets a unique ID.
    # Every callback checks its captured session_id against this before
    # touching the UI. Old threads from stopped sessions are silently dropped.
    _session_id   = {"value": 0}

    _all_results: list[dict] = []
    _results_lock = threading.Lock()

    _page_scraped_count: list[int] = []
    _current_page = {"value": 0}

    # ── Loader ────────────────────────────────────────────────────────────────
    loader_label = ft.Text(COOKING_STAGES[0][0], color=ORANGE, size=14, italic=True)
    loader_sub   = ft.Text(COOKING_STAGES[0][1], color=TEXT2(), size=11)
    loader_ring  = ftl.Lottie(
        src="https://lottie.host/7748923e-58e6-4db0-bff7-7454e10aa489/L8lGN5kMvc.json",
        width=100, height=100, repeat=True, visible=True,
        scale=ft.Scale(scale=1.2),
    )
    loader_dots = [
        ft.Container(
            width=8, height=8,
            border_radius=ft.BorderRadius.all(4),
            bgcolor=BG3(),
            border=ft.Border.all(1, BORDER()),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            scale=ft.Scale(scale=1.0),
        )
        for _ in range(6)
    ]
    loader_ring_bg = ft.Container(
        content=loader_ring, width=60, height=60,
        bgcolor=BG3(), border_radius=ft.BorderRadius.all(22),
        alignment=ft.Alignment.CENTER,
    )
    sticky_loader = ft.Container(
        visible=False,
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
        padding=ft.Padding.symmetric(horizontal=24, vertical=15),
        content=ft.Row(
            controls=[
                loader_ring_bg,
                ft.Column(controls=[loader_label, loader_sub], spacing=2, expand=True),
                ft.Column(
                    controls=[ft.Row(controls=loader_dots, spacing=6, tight=True)],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=30,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def _set_loading_stage(stage: int):
        if stage < 0:
            sticky_loader.visible = False
            page.update()
            return
        sticky_loader.visible = True
        s = COOKING_STAGES[min(stage, len(COOKING_STAGES) - 1)]
        loader_label.value  = s[0]
        loader_sub.value    = s[1]
        loader_ring.visible = stage < 7
        loader_ring.play    = stage < 7
        for i, dot in enumerate(loader_dots):
            if i < stage:
                dot.bgcolor = ORANGE
                dot.border  = ft.Border.all(1, ORANGE)
                dot.scale   = ft.Scale(scale=1.0)
            elif i == stage:
                dot.bgcolor = ft.Colors.TRANSPARENT
                dot.border  = ft.Border.all(2, ORANGE)
                dot.scale   = ft.Scale(scale=1.35)
            else:
                dot.bgcolor = BG3()
                dot.border  = ft.Border.all(1, BORDER())
                dot.scale   = ft.Scale(scale=1.0)
        page.update()

    def _refresh_loader_for_current_page():
        cur   = _current_page["value"]
        count = _page_scraped_count[cur] if cur < len(_page_scraped_count) else 0

        if not _is_scraping["value"]:
            _set_loading_stage(-1)
            return

        page_is_full = count >= PAGE_SIZE
        is_last_active_page = cur >= len(_page_scraped_count) - 1

        if page_is_full and not is_last_active_page:
            _set_loading_stage(-1)
        elif page_is_full:
            _set_loading_stage(-1)
        else:
            stage = min(count, 5)
            _set_loading_stage(stage)

    # ── Floating emoji ────────────────────────────────────────────────────────
    _float_tasks_active = {"value": False}
    _emoji_containers: list[ft.Container] = []

    async def _float_all_emojis_loop():
        toggles = [i % 2 == 0 for i in range(len(_emoji_containers))]
        while _float_tasks_active["value"]:
            for i, c in enumerate(_emoji_containers):
                _, _, amp, _ = _FLOAT_EMOJIS[i]
                c.offset = ft.Offset(0, (amp if toggles[i] else -amp) / 100)
                toggles[i] = not toggles[i]
            page.update()
            await asyncio.sleep(1.3)

    def _start_float_animations():
        _float_tasks_active["value"] = True
        page.run_task(_float_all_emojis_loop)

    def _stop_float_animations():
        _float_tasks_active["value"] = False
        for c in _emoji_containers:
            c.offset = ft.Offset(0, 0)

    for emoji, _, amp, period in _FLOAT_EMOJIS:
        _emoji_containers.append(
            ft.Container(
                content=ft.Text(emoji, size=28),
                animate_offset=ft.Animation(int(period * 500), ft.AnimationCurve.EASE_IN_OUT),
                offset=ft.Offset(0, 0),
            )
        )

    enter_hint = ft.Container(
        content=ft.Text(
            "atau tekan Enter ↵", size=12, color=TEXT3(),
            font_family="Font", text_align=ft.TextAlign.CENTER, italic=True,
        ),
        animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
        opacity=0.5,
    )

    async def _pulse_enter_hint():
        while True:
            enter_hint.opacity = 1.0
            if enter_hint.page: enter_hint.update()
            await asyncio.sleep(1.2)
            enter_hint.opacity = 0.3
            if enter_hint.page: enter_hint.update()
            await asyncio.sleep(1.2)

    empty_title = ft.Text(
        "Masukkan bahan yang kamu punya", size=18,
        weight=ft.FontWeight.BOLD, color=TEXT(),
        font_family="Font", text_align=ft.TextAlign.CENTER,
    )
    empty_sub = ft.Text(
        "CookD akan carikan resep terbaik\nsesuai bahan di dapurmu 🥘",
        size=14, color=TEXT2(), font_family="Font", text_align=ft.TextAlign.CENTER,
    )
    empty_state = ft.Container(
        visible=True, expand=True,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, 0), radius=1.2,
            colors=["#18206a20", "#00000000"],
        ),
        content=ft.Column(
            controls=[
                ft.Text("🍳", size=72),
                ft.Container(height=16),
                empty_title,
                ft.Container(height=8),
                empty_sub,
                ft.Container(height=24),
                ft.Row(controls=_emoji_containers, alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                ft.Container(height=16),
                enter_hint,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        ),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1.0,
    )

    results_column = ft.Column(
        controls=[], spacing=10,
        scroll=ft.ScrollMode.AUTO, expand=True, visible=False,
    )

    # ── Pagination bar ────────────────────────────────────────────────────────
    _prev_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color=ORANGE, tooltip="Halaman sebelumnya",
        visible=False,
        mouse_cursor=ft.MouseCursor.CLICK,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            bgcolor={"hovered": BG3(), "": ft.Colors.TRANSPARENT},
            mouse_cursor=ft.MouseCursor.CLICK,
        ),
        on_click=lambda e: page.run_task(_go_page, _current_page["value"] - 1),
    )

    _page_label = ft.Text(
        "1/1", size=13, color=TEXT(), font_family="Font", weight=ft.FontWeight.BOLD,
    )

    _next_icon_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        icon_color=ORANGE, tooltip="Halaman berikutnya",
        visible=False,
        mouse_cursor=ft.MouseCursor.CLICK,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            bgcolor={"hovered": BG3(), "": ft.Colors.TRANSPARENT},
            mouse_cursor=ft.MouseCursor.CLICK,
        ),
        on_click=lambda e: page.run_task(_go_page, _current_page["value"] + 1),
    )

    _next_spinner = ft.Container(
        content=ft.ProgressRing(width=16, height=16, stroke_width=2, color=ORANGE),
        width=40, height=40,
        alignment=ft.Alignment.CENTER,
        visible=False,
        tooltip="Memuat halaman berikutnya...",
    )

    pagination_bar = ft.Container(
        visible=False,
        padding=ft.Padding.symmetric(horizontal=0, vertical=8),
        content=ft.Row(
            controls=[_prev_btn, _page_label, _next_icon_btn, _next_spinner],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def _total_pages() -> int:
        with _results_lock:
            total = len(_all_results)
        if total == 0:
            return 1
        return -(-total // PAGE_SIZE)

    def _update_pagination():
        cur   = _current_page["value"]
        total = _total_pages()

        _page_label.value = f"{cur + 1}/{total}"
        _prev_btn.visible = cur > 0

        next_start = (cur + 1) * PAGE_SIZE
        with _results_lock:
            total_results = len(_all_results)

        has_next_data  = total_results > next_start
        still_scraping = _is_scraping["value"]

        _next_icon_btn.visible = has_next_data
        _next_spinner.visible  = not has_next_data and still_scraping

        pagination_bar.visible = (total > 1) or _next_spinner.visible
        pagination_bar.update()

    async def _go_page(page_index: int):
        with _results_lock:
            total_results = len(_all_results)

        if page_index < 0:
            return
        if page_index * PAGE_SIZE >= total_results:
            return

        _current_page["value"] = page_index
        await _render_current_page()

    async def _render_current_page():
        cur   = _current_page["value"]
        start = cur * PAGE_SIZE
        end   = start + PAGE_SIZE

        with _results_lock:
            page_recipes = sorted(
                _all_results, key=lambda x: x["match_score"], reverse=True
            )[start:end]

        # Build all cards first (no awaits yet)
        _tracked_cards.clear()
        new_cards = [_build_card(r) for r in page_recipes]

        # Replace column contents and push ONE update — visible immediately
        results_column.controls.clear()
        results_column.controls.extend(new_cards)
        _update_pagination()
        _refresh_loader_for_current_page()
        results_column.update()
        page.update()

        # Fire all card animations in parallel with a tiny stagger
        async def _animate_all():
            await asyncio.gather(*[
                _animate_card_in(card, i * 0.03)
                for i, card in enumerate(new_cards)
            ])
            _update_pagination()
            _refresh_loader_for_current_page()
            page.update()

        page.run_task(_animate_all)

    # ── Card helpers ──────────────────────────────────────────────────────────
    _tracked_cards: list[ft.Container] = []

    def _card_gradient():
        return ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=[BG3(), BG2(), BG3()], stops=[0.0, 0.5, 1.0],
        )

    def _card_hover_gradient():
        return ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=["#28ff8c40", "#18ff6a20", BG2()], stops=[0.0, 0.4, 1.0],
        )

    def _not_found_card() -> ft.Container:
        sad_emoji = ft.Container(
            content=ft.Text("😔", size=52),
            animate_offset=ft.Animation(400, ft.AnimationCurve.BOUNCE_OUT),
            offset=ft.Offset(0, 0),
        )

        async def _shake_emoji():
            for dx in [0.05, -0.05, 0.04, -0.04, 0.02, -0.02, 0.0]:
                sad_emoji.offset = ft.Offset(dx, 0)
                if sad_emoji.page: sad_emoji.update()
                await asyncio.sleep(0.06)

        card = ft.Container(
            content=ft.Column(
                controls=[
                    sad_emoji,
                    ft.Container(height=4),
                    ft.Text("Resep tidak ditemukan", size=16, weight=ft.FontWeight.BOLD, color=TEXT(), font_family="Font"),
                    ft.Text("Coba bahan lain atau tambah lebih banyak bahan", size=13, color=TEXT2(), font_family="Font", text_align=ft.TextAlign.CENTER),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Text("Coba lagi →", color=ORANGE, size=13, weight=ft.FontWeight.BOLD, font_family="Font"),
                        bgcolor=BG3(),
                        border=ft.Border.all(1, ORANGE),
                        border_radius=ft.BorderRadius.all(20),
                        padding=ft.Padding.symmetric(horizontal=18, vertical=8),
                        on_click=lambda e: (setattr(search_field, "value", ""), search_field.focus(), search_field.update()),
                        ink=True, ink_color="#30ff6a20",
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1),
                colors=["#30ef444430", BG2(), BG3()], stops=[0.0, 0.5, 1.0],
            ),
            border_radius=ft.BorderRadius.all(16),
            border=ft.Border.all(1, "#60ef4444"),
            padding=ft.Padding.symmetric(horizontal=24, vertical=32),
            alignment=ft.Alignment(0, 0),
            animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_IN),
            animate_offset=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            opacity=0.0, offset=ft.Offset(0, 0.15),
        )

        async def _animate_in():
            await asyncio.sleep(0.01)
            card.opacity = 1.0
            card.offset  = ft.Offset(0, 0)
            card.update()
            await asyncio.sleep(0.1)
            await _shake_emoji()

        page.run_task(_animate_in)
        _tracked_cards.append(card)
        return card

    def _build_card(r: dict) -> ft.Container:
        score     = r.get("match_score", 0)
        score_pct = f"Match {round(score * 100)}%"
        bg_score, fg_score = (
            ("#1B3D28", GREEN)     if score >= 0.8 else
            ("#3D2E0A", AMBER)     if score >= 0.5 else
            ("#3D1A1A", "#ef4444")
        )

        thumb = ft.Container(
            width=96, height=96,
            border_radius=ft.BorderRadius.all(12),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            content=ft.Image(src=r.get("image_url", ""), width=96, height=96, fit="cover"),
        )

        _hover_state = {"active": False}

        async def on_card_click(e, _card=None):
            c = _card
            c.opacity = 0.7
            c.update()
            await asyncio.sleep(0.08)
            c.opacity  = 1.0
            c.gradient = _card_gradient()
            c.border   = ft.Border.all(1, BORDER())
            c.shadow   = None
            c.update()
            show_detail_fn(r)

        def on_hover(e, _card=None, _thumb=None, _state=None):
            if _card not in _tracked_cards:
                return

            is_hovering = bool(e.data)

            if _state["active"] == is_hovering:
                return
            _state["active"] = is_hovering

            if is_hovering:
                _card.gradient = _card_hover_gradient()
                _card.border   = ft.Border.all(1.5, ORANGE)
                _card.shadow   = ft.BoxShadow(
                    spread_radius=0, blur_radius=14,
                    color="#50ff6a20", offset=ft.Offset(0, 2),
                )
                _thumb.border_radius = ft.BorderRadius.all(14)
            else:
                _card.gradient = _card_gradient()
                _card.border   = ft.Border.all(1, BORDER())
                _card.shadow   = None
                _thumb.border_radius = ft.BorderRadius.all(12)

            _card.update()
            _thumb.update()

        # FIX (blank card): set gradient and border RIGHT HERE at construction
        # time so the card is never in a "no style" state between being appended
        # to results_column and _animate_card_in firing. The opacity/offset
        # start values make it invisible until the animation plays, but the
        # background is always correct — no white flash.
        inner_card = ft.Container(
            data=score,
            animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_IN),
            animate_offset=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            opacity=0.0, offset=ft.Offset(0, 0.12),
            gradient=_card_gradient(),          # ← set at build time, not only in _animate_card_in
            border=ft.Border.all(1, BORDER()),  # ← same
            content=ft.Row(
                controls=[
                    thumb,
                    ft.Column(
                        controls=[
                            ft.Text(r["name"], color=TEXT(), weight=ft.FontWeight.BOLD, size=16, font_family="Font"),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=TEXT2(), size=13),
                                    ft.Text(r.get("portion", ""),    color=TEXT2(), size=12),
                                    ft.Text("·",                     color=TEXT3(), size=12),
                                    ft.Icon(ft.Icons.TIMER_OUTLINED, color=TEXT2(), size=13),
                                    ft.Text(r.get("cook_time", ""),  color=TEXT2(), size=12),
                                ],
                                spacing=4,
                            ),
                            ft.Container(
                                content=ft.Text(r.get("source", "Cookpad"), color=TEXT3(), size=10),
                                bgcolor=BG4(),
                                border_radius=ft.BorderRadius.all(6),
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ],
                        spacing=7, expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Text(score_pct, color=fg_score, size=11, weight=ft.FontWeight.BOLD),
                                bgcolor=bg_score,
                                border_radius=ft.BorderRadius.all(20),
                                border=ft.Border.all(1, fg_score),
                                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            ),
                            ft.ElevatedButton(
                                "Lihat →",
                                style=ft.ButtonStyle(
                                    bgcolor=ORANGE, color=WHITE,
                                    mouse_cursor=ft.MouseCursor.CLICK,
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                                    overlay_color={"hovered": "#d94410", "": ORANGE},
                                ),
                                on_click=lambda e, rec=r: show_detail_fn(rec),
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            border_radius=ft.BorderRadius.all(16),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
        )

        inner_card.on_hover  = lambda e, c=inner_card, t=thumb, s=_hover_state: on_hover(e, _card=c, _thumb=t, _state=s)
        inner_card.on_click  = lambda e, c=inner_card: page.run_task(on_card_click, e, c)

        outer_wrapper = ft.Container(
            content=inner_card,
            clip_behavior=ft.ClipBehavior.NONE,
            padding=ft.Padding.symmetric(horizontal=2, vertical=2),
            bgcolor=ft.Colors.TRANSPARENT,
        )

        outer_wrapper.data = score

        _tracked_cards.append(inner_card)
        return outer_wrapper

    async def _animate_card_in(wrapper: ft.Container, delay: float = 0.0):
        """Animate the inner card inside its outer wrapper."""
        if delay > 0:
            await asyncio.sleep(delay)
        inner = wrapper.content
        # Gradient/border already set at build time; only update opacity/offset here.
        inner.opacity = 1.0
        inner.offset  = ft.Offset(0, 0)
        inner.update()

    # ── Mode toggle ───────────────────────────────────────────────────────────
    def _make_mode_btn(label: str, mode: str) -> ft.Container:
        is_active = _search_mode["value"] == mode
        return ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e, m=mode: _select_mode(m),
            content=ft.Container(
                data=mode,
                content=ft.Text(
                    label, size=12,
                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                    color=WHITE if is_active else TEXT2(),
                    font_family="Font", no_wrap=True,
                ),
                bgcolor=ORANGE if is_active else "transparent",
                border_radius=ft.BorderRadius.all(10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=7),
                ink=True,
            ),
        )

    _local_btn  = _make_mode_btn("📁 Lokal",  "local")
    _scrape_btn = _make_mode_btn("🌐 Scrape", "scrape")

    mode_toggle = ft.Container(
        content=ft.Row(controls=[_local_btn, _scrape_btn], spacing=4, tight=True),
        bgcolor=BG3(),
        border=ft.Border.all(1, BORDER()),
        border_radius=ft.BorderRadius.all(12),
        padding=ft.Padding.all(4),
        animate_opacity=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
    )

    def _select_mode(mode: str):
        if _is_scraping["value"]:
            return
        _search_mode["value"] = mode
        for btn, m in [(_local_btn, "local"), (_scrape_btn, "scrape")]:
            is_active = mode == m
            btn.content.bgcolor        = ORANGE if is_active else "transparent"
            btn.content.content.weight = ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL
            btn.content.content.color  = WHITE if is_active else TEXT2()
            btn.content.update()

    def _lock_mode_toggle(locked: bool):
        mode_toggle.opacity = 0.4 if locked else 1.0
        mode_toggle.update()

    # ── Stop / Refresh button ─────────────────────────────────────────────────
    _stop_refresh_btn = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE_OUTLINED,
        icon_color="#ef4444",
        tooltip="Stop",
        visible=False,
        mouse_cursor=ft.MouseCursor.CLICK,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor={"hovered": "#22ef4444", "": ft.Colors.TRANSPARENT},
            mouse_cursor=ft.MouseCursor.CLICK,
        ),
    )

    def _set_btn_stop():
        _stop_refresh_btn.icon       = ft.Icons.STOP_CIRCLE_OUTLINED
        _stop_refresh_btn.icon_color = "#ef4444"
        _stop_refresh_btn.tooltip    = "Stop"
        _stop_refresh_btn.visible    = True
        _stop_refresh_btn.style.bgcolor = {"hovered": "#22ef4444", "": ft.Colors.TRANSPARENT}
        _stop_refresh_btn.update()

    def _set_btn_refresh():
        _stop_refresh_btn.icon       = ft.Icons.REFRESH
        _stop_refresh_btn.icon_color = ORANGE
        _stop_refresh_btn.tooltip    = "Ulangi pencarian"
        _stop_refresh_btn.visible    = True
        _stop_refresh_btn.style.bgcolor = {"hovered": "#22ff6a20", "": ft.Colors.TRANSPARENT}
        _stop_refresh_btn.update()

    async def _on_stop_refresh_click(e):
        if _is_scraping["value"]:
            # ── STOP ──────────────────────────────────────────────────────────
            ev = _stop_event["value"]
            if ev:
                ev.set()
                print("[CookD] ⛔ Pencarian dihentikan oleh pengguna.")

            # FIX: bump session ID immediately so any in-flight on_recipe_found
            # callbacks that haven't fired yet will see a mismatched session and
            # bail out — even if stop_ev.is_set() check loses the race.
            _session_id["value"] += 1

            _is_scraping["value"] = False

            _set_btn_refresh()
            _set_loading_stage(-1)
            _lock_mode_toggle(False)

            _stop_event["value"] = threading.Event()
            _stop_event["value"].set()

            for c in list(_tracked_cards):
                try:
                    c.gradient = _card_gradient()
                    c.border   = ft.Border.all(1, BORDER())
                    c.scale    = ft.Scale(scale=1.0)
                    c.update()
                except Exception:
                    pass

            _update_pagination()
            page.update()
        else:
            # ── REFRESH ──
            last = _last_query["value"]
            if last:
                search_field.value = last
                search_field.update()
                await _run_search_logic()

    _stop_refresh_btn.on_click = _on_stop_refresh_click

    # ── Search field & button ─────────────────────────────────────────────────
    search_field = ft.TextField(
        hint_text="cth: bawang putih, tomat, telur...",
        hint_style=ft.TextStyle(color=TEXT3()),
        bgcolor=BG3(), color=TEXT(),
        focused_border_color=ORANGE, border_color=BORDER(),
        border_radius=ft.BorderRadius.all(28),
        content_padding=ft.Padding.symmetric(horizontal=24, vertical=14),
        expand=True,
        on_submit=lambda e: page.run_task(_run_search_logic),
    )

    search_btn = ft.ElevatedButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SEARCH, color=WHITE, size=16),
                ft.Text("Cari", color=WHITE, weight=ft.FontWeight.BOLD),
            ],
            spacing=6, tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor=ORANGE,
            shape=ft.RoundedRectangleBorder(radius=28),
            mouse_cursor=ft.MouseCursor.CLICK,
            padding=ft.Padding.symmetric(horizontal=26, vertical=14),
            overlay_color={"hovered": "#d94410", "pressed": "#c03b0d", "": ORANGE},
        ),
    )

    search_btn_container = ft.Container(
        content=search_btn,
        scale=ft.Scale(scale=1.0),
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
    )

    async def _on_search_btn_click(e):
        search_btn_container.scale = ft.Scale(scale=0.93)
        search_btn_container.update()
        await asyncio.sleep(0.08)
        search_btn_container.scale = ft.Scale(scale=1.0)
        search_btn_container.update()
        await _run_search_logic()

    search_btn.on_click = _on_search_btn_click

    # ── Core search logic ─────────────────────────────────────────────────────
    async def _run_search_logic():
        nonlocal _all_results, _page_scraped_count

        ingredients = search_field.value.strip()
        if not ingredients:
            return

        # If already scraping, stop previous run first.
        if _is_scraping["value"]:
            ev = _stop_event["value"]
            if ev:
                ev.set()
            _is_scraping["value"] = False

        # FIX: bump session counter BEFORE resetting shared state so that any
        # callbacks queued by the old thread see a mismatched session_id and
        # abort without touching _all_results or _page_scraped_count.
        _session_id["value"] += 1
        my_session = _session_id["value"]

        # Reset state
        _all_results        = []
        _page_scraped_count = [0]
        _current_page["value"] = 0
        _last_query["value"]   = ingredients
        _tracked_cards.clear()
        results_column.controls.clear()
        _stop_float_animations()

        empty_state.visible    = False
        results_column.visible = True
        pagination_bar.visible = False
        empty_state.update()
        results_column.update()
        pagination_bar.update()

        _is_scraping["value"] = True
        _lock_mode_toggle(True)
        _set_btn_stop()
        _set_loading_stage(0)
        page.update()

        stop_ev = threading.Event()
        _stop_event["value"] = stop_ev

        user_ingredients = [k.strip() for k in ingredients.split(",") if k.strip()]
        loop      = asyncio.get_event_loop()
        found_any = {"value": False}

        def on_recipe_found(recipe):
            async def update_ui():
                # FIX: primary guard — stale session means a stop was pressed
                # (or a new search started) since this callback was dispatched.
                # Drop the result entirely; touching the UI here would corrupt
                # the new session's state or produce blank/white cards.
                if _session_id["value"] != my_session:
                    return

                # Secondary guard — belt-and-suspenders with stop_ev.
                if stop_ev.is_set() or not _is_scraping["value"]:
                    return

                found_any["value"] = True

                with _results_lock:
                    _all_results.append(recipe)
                    total = len(_all_results)

                recipe_page_idx = (total - 1) // PAGE_SIZE

                # FIX (_page_scraped_count race): guard list extension under the
                # same session check so a stop+restart can't cause an append to
                # the newly-reset list that then throws off card counts.
                while len(_page_scraped_count) <= recipe_page_idx:
                    _page_scraped_count.append(0)
                _page_scraped_count[recipe_page_idx] += 1

                cur = _current_page["value"]

                if recipe_page_idx == cur:
                    wrapper = _build_card(recipe)
                    insert_at = len(results_column.controls)
                    for i, ctrl in enumerate(results_column.controls):
                        if recipe["match_score"] > (ctrl.data or 0):
                            insert_at = i
                            break
                    results_column.controls.insert(insert_at, wrapper)
                    results_column.update()
                    page.update()
                    await _animate_card_in(wrapper, 0.0)

                _refresh_loader_for_current_page()
                _update_pagination()
                page.update()

            asyncio.run_coroutine_threadsafe(update_ui(), loop)

        def run():
            CookpadScraper.main(
                user_ingredients,
                on_recipe_found=on_recipe_found,
                mode=_search_mode["value"],
                stop_event=stop_ev,
            )
            stop_ev.set()

            async def _on_run_done():
                # FIX: same session guard in the completion handler — if the
                # user stopped and restarted between the thread finishing and
                # this coroutine running, do nothing.
                if _session_id["value"] != my_session:
                    return
                if not _is_scraping["value"]:
                    return
                _is_scraping["value"] = False
                _set_loading_stage(-1)
                _set_btn_refresh()
                _lock_mode_toggle(False)
                if not found_any["value"]:
                    not_found = _not_found_card()
                    results_column.controls.append(not_found)
                _update_pagination()
                page.update()

            asyncio.run_coroutine_threadsafe(_on_run_done(), loop)

        threading.Thread(target=run, daemon=True).start()

    # ── Theme rebuild ─────────────────────────────────────────────────────────
    def rebuild():
        container.bgcolor         = BG()
        search_field.bgcolor      = BG3()
        search_field.color        = TEXT()
        search_field.border_color = BORDER()
        search_field.update()
        mode_toggle.bgcolor = BG3()
        mode_toggle.border  = ft.Border.all(1, BORDER())
        mode_toggle.update()
        loader_ring_bg.bgcolor = BG3()
        loader_ring_bg.update()
        loader_sub.color = TEXT2()
        loader_sub.update()
        empty_title.color = TEXT()
        empty_sub.color   = TEXT2()
        empty_title.update()
        empty_sub.update()
        for card in _tracked_cards:
            if not isinstance(card, ft.Container):
                continue
            card.gradient = _card_gradient()
            card.border   = ft.Border.all(1, BORDER())
            card.shadow   = None
            card.update()
            row = getattr(card, "content", None)
            if not isinstance(row, ft.Row):
                continue
            for child in row.controls:
                if isinstance(child, ft.Column):
                    for item in child.controls:
                        if isinstance(item, ft.Text):
                            item.color = TEXT() if item.weight == ft.FontWeight.BOLD else TEXT2()
                            item.update()
                        elif isinstance(item, ft.Container):
                            _is_score_badge = (
                                isinstance(getattr(item, "content", None), ft.Text)
                                and item.border_radius is not None
                                and getattr(item, "padding", None) is not None
                                and getattr(item.content, "weight", None) == ft.FontWeight.BOLD
                                and item.bgcolor not in (None, ft.Colors.TRANSPARENT, BG4())
                            )
                            if not _is_score_badge:
                                item.bgcolor = BG4()
                                item.update()
                                if isinstance(getattr(item, "content", None), ft.Text):
                                    item.content.color = TEXT3()
                                    item.content.update()
                        elif isinstance(item, ft.Row):
                            for sub in item.controls:
                                if isinstance(sub, ft.Text):
                                    sub.color = TEXT2()
                                    sub.update()
                                elif isinstance(sub, ft.Icon):
                                    sub.color = TEXT2()
                                    sub.update()
        page.update()

    theme_mgr.add_listener(rebuild)

    # ── Container ─────────────────────────────────────────────────────────────
    container = ft.Container(
        expand=True,
        bgcolor=BG(),
        visible=False,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[search_field, search_btn_container, _stop_refresh_btn],
                                spacing=10,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text("Mode:", size=12, color=TEXT2(), font_family="Font"),
                                    mode_toggle,
                                ],
                                spacing=10,
                                alignment=ft.MainAxisAlignment.START,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=ft.Padding.symmetric(horizontal=24, vertical=18),
                ),
                sticky_loader,
                ft.Container(
                    expand=True,
                    bgcolor=ft.Colors.TRANSPARENT,
                    clip_behavior=ft.ClipBehavior.NONE,
                    padding=ft.Padding.only(left=20, right=20, bottom=8),
                    margin=ft.Margin.only(top=4),
                    content=ft.Stack(
                        controls=[
                            empty_state,
                            ft.Column(
                                controls=[results_column, pagination_bar],
                                spacing=0,
                                expand=True,
                            ),
                        ],
                        expand=True,
                        clip_behavior=ft.ClipBehavior.NONE,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        ),
    )

    container.results_column = results_column
    _start_float_animations()
    page.run_task(_pulse_enter_hint)

    # ── Prefill from Home search bar ──────────────────────────────────────────
    def prefill_and_search(query: str):
        """
        Dipanggil dari navigate_fn saat user search dari Home.
        Isi search_field lalu langsung jalankan pencarian.
        """
        if not query:
            return
        search_field.value = query
        search_field.update()
        page.run_task(_run_search_logic)

    container.prefill_and_search = prefill_and_search

    # Cek jika ada prefill yang dikirim dari Home sebelum page ini aktif
    def on_visible_change(e):
        if not container.visible:
            return
        prefill = page.session.get("home_prefill")
        if prefill:
            page.session.remove("home_prefill")
            prefill_and_search(prefill)

    container.on_visible_change = on_visible_change

    return container