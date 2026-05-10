# rafy/for_you_ui.py
import flet as ft
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rafy.theme import theme_mgr, ORANGE, WHITE

def BG()     -> str: return theme_mgr.get("BG")
def BG2()    -> str: return theme_mgr.get("BG2")
def BG3()    -> str: return theme_mgr.get("BG3")
def BG4()    -> str: return theme_mgr.get("BG4")
def TEXT()   -> str: return theme_mgr.get("TEXT")
def TEXT2()  -> str: return theme_mgr.get("TEXT2")
def TEXT3()  -> str: return theme_mgr.get("TEXT3")
def BORDER() -> str: return theme_mgr.get("BORDER")


# ─────────────────────────────────────────────────────────────────────────────
# DUMMY DATA — 12 resep, rotasi tiap hari
# ─────────────────────────────────────────────────────────────────────────────
RECIPES = [
    {
        "name":        "Rendang Daging Sapi",
        "author":      "Uni Farah",
        "portion":     "11 porsi",
        "cook_time":   "67 menit",
        "image_url":   "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "1 kg daging sapi",
            "400 ml santan kental",
            "5 siung bawang putih",
            "8 siung bawang merah",
            "3 batang serai",
            "3 lembar daun jeruk",
            "2 cm lengkuas",
            "2 cm jahe",
            "10 buah cabai merah",
            "Garam secukupnya",
        ],
        "steps": [
            "Haluskan bumbu: bawang putih, bawang merah, cabai, jahe, dan lengkuas.",
            "Tumis bumbu halus bersama serai dan daun jeruk hingga harum.",
            "Masukkan daging sapi, aduk rata hingga daging berubah warna.",
            "Tuang santan kental, masak dengan api sedang sambil terus diaduk.",
            "Kecilkan api, masak hingga santan mengering dan daging berwarna cokelat gelap.",
            "Koreksi rasa, angkat dan sajikan.",
        ],
    },
    {
        "name":        "Nasi Goreng Kampung Spesial",
        "author":      "Bunda Sari",
        "portion":     "2 porsi",
        "cook_time":   "20 menit",
        "image_url":   "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "2 piring nasi putih dingin",
            "2 butir telur",
            "3 siung bawang putih",
            "5 siung bawang merah",
            "2 sdm kecap manis",
            "1 sdt garam",
            "1 sdt merica",
            "2 sdm minyak goreng",
            "Cabai rawit secukupnya",
            "Daun bawang secukupnya",
        ],
        "steps": [
            "Iris tipis bawang merah, bawang putih, dan cabai rawit.",
            "Panaskan minyak, tumis bawang hingga harum dan kekuningan.",
            "Masukkan telur, orak-arik hingga setengah matang.",
            "Masukkan nasi, aduk rata dengan bumbu.",
            "Tambahkan kecap manis, garam, dan merica. Aduk hingga merata.",
            "Tambahkan daun bawang, aduk sebentar lalu angkat dan sajikan.",
        ],
    },
    {
        "name":        "Soto Ayam Lamongan",
        "author":      "Mbak Dewi",
        "portion":     "6 porsi",
        "cook_time":   "50 menit",
        "image_url":   "https://images.unsplash.com/photo-1555126634-323283e090fa?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "1 ekor ayam kampung",
            "2 liter air",
            "5 siung bawang putih",
            "8 siung bawang merah",
            "2 cm kunyit",
            "2 cm jahe",
            "2 batang serai",
            "3 lembar daun salam",
            "Garam dan merica secukupnya",
            "Daun bawang dan seledri",
        ],
        "steps": [
            "Rebus ayam dalam air hingga matang, angkat dan suwir-suwir.",
            "Haluskan bawang putih, bawang merah, kunyit, dan jahe.",
            "Tumis bumbu halus bersama serai dan daun salam hingga harum.",
            "Masukkan bumbu ke dalam kaldu ayam, didihkan.",
            "Koreksi rasa dengan garam dan merica.",
            "Sajikan dengan suwiran ayam, taburan daun bawang, dan seledri.",
        ],
    },
    {
        "name":        "Gado-gado Jakarta",
        "author":      "Mpok Tini",
        "portion":     "4 porsi",
        "cook_time":   "30 menit",
        "image_url":   "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "200 g kacang tanah goreng",
            "3 siung bawang putih",
            "5 buah cabai merah",
            "2 sdm gula merah",
            "1 sdm kecap manis",
            "Garam secukupnya",
            "Air secukupnya",
            "Sayuran rebus (kangkung, tauge, kol)",
            "Tahu dan tempe goreng",
            "Lontong secukupnya",
        ],
        "steps": [
            "Haluskan kacang tanah, bawang putih, dan cabai.",
            "Masak bumbu kacang dengan air, gula merah, kecap, dan garam.",
            "Aduk hingga saus mengental dan matang.",
            "Susun sayuran rebus, tahu, tempe, dan lontong di piring.",
            "Siram dengan saus kacang, sajikan segera.",
        ],
    },
    {
        "name":        "Semur Daging Kentang",
        "author":      "Ibu Ratna",
        "portion":     "4 porsi",
        "cook_time":   "45 menit",
        "image_url":   "https://images.unsplash.com/photo-1574484284002-952d92456975?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "500 g daging sapi",
            "3 buah kentang",
            "5 siung bawang putih",
            "6 siung bawang merah",
            "4 sdm kecap manis",
            "1 sdt pala bubuk",
            "1 sdt merica",
            "Garam secukupnya",
            "Minyak goreng",
            "Air secukupnya",
        ],
        "steps": [
            "Potong daging dan kentang sesuai selera.",
            "Tumis bawang merah dan putih hingga harum.",
            "Masukkan daging, masak hingga berubah warna.",
            "Tambahkan kecap manis, pala, merica, dan garam.",
            "Tuang air, masak hingga daging empuk.",
            "Masukkan kentang, masak hingga matang dan kuah mengental.",
        ],
    },
    {
        "name":        "Ayam Bakar Taliwang",
        "author":      "Kak Rohani",
        "portion":     "4 porsi",
        "cook_time":   "60 menit",
        "image_url":   "https://images.unsplash.com/photo-1562802378-063ec186a863?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "1 ekor ayam muda",
            "10 buah cabai merah keriting",
            "5 buah cabai rawit",
            "6 siung bawang putih",
            "8 siung bawang merah",
            "1 sdt terasi bakar",
            "2 sdm minyak kelapa",
            "Garam dan gula secukupnya",
            "Air jeruk limau",
        ],
        "steps": [
            "Belah ayam menjadi dua bagian, geprek sedikit.",
            "Haluskan semua bumbu cabai, bawang, dan terasi.",
            "Lumuri ayam dengan bumbu, diamkan 30 menit.",
            "Bakar ayam di atas bara api sambil dibolak-balik.",
            "Olesi dengan sisa bumbu setiap kali membalik.",
            "Bakar hingga matang dan sedikit gosong di bagian pinggir.",
        ],
    },
    {
        "name":        "Opor Ayam Kuning",
        "author":      "Bunda Lia",
        "portion":     "6 porsi",
        "cook_time":   "55 menit",
        "image_url":   "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "1 ekor ayam potong",
            "500 ml santan",
            "5 siung bawang putih",
            "8 siung bawang merah",
            "3 cm kunyit",
            "2 cm jahe",
            "2 batang serai",
            "3 lembar daun jeruk",
            "Garam dan gula secukupnya",
        ],
        "steps": [
            "Haluskan bawang putih, bawang merah, kunyit, dan jahe.",
            "Tumis bumbu halus bersama serai dan daun jeruk.",
            "Masukkan ayam, aduk rata dengan bumbu.",
            "Tuang santan encer, masak hingga mendidih.",
            "Tambahkan santan kental, masak dengan api kecil.",
            "Koreksi rasa, sajikan dengan taburan bawang goreng.",
        ],
    },
    {
        "name":        "Bakso Kuah Gurih",
        "author":      "Pak Bambang",
        "portion":     "5 porsi",
        "cook_time":   "90 menit",
        "image_url":   "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "500 g daging sapi giling",
            "100 g tepung tapioka",
            "2 siung bawang putih",
            "1 sdt garam",
            "1 sdt merica",
            "1 butir telur putih",
            "1 liter kaldu sapi",
            "Daun bawang dan seledri",
            "Bihun atau mie secukupnya",
        ],
        "steps": [
            "Campurkan daging giling, tepung tapioka, telur, bawang, garam, dan merica.",
            "Uleni hingga adonan kalis dan bisa dibentuk.",
            "Rebus air hingga mendidih, bentuk adonan menjadi bulatan.",
            "Masukkan bakso ke dalam air mendidih, rebus hingga mengapung.",
            "Didihkan kaldu sapi, beri bumbu garam dan merica.",
            "Sajikan bakso dalam mangkuk dengan kuah, mie, dan taburan daun bawang.",
        ],
    },
    {
        "name":        "Capcay Kuah Seafood",
        "author":      "Chef Andi",
        "portion":     "4 porsi",
        "cook_time":   "25 menit",
        "image_url":   "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "200 g udang kupas",
            "100 g cumi-cumi",
            "Wortel, kol, sawi, jagung muda",
            "5 siung bawang putih",
            "1 sdm saus tiram",
            "1 sdm kecap asin",
            "1 sdt merica",
            "Garam secukupnya",
            "Maizena untuk pengental",
        ],
        "steps": [
            "Tumis bawang putih hingga harum.",
            "Masukkan udang dan cumi, masak hingga berubah warna.",
            "Tambahkan sayuran keras seperti wortel dan jagung muda.",
            "Masukkan sayuran lainnya, aduk rata.",
            "Bumbui dengan saus tiram, kecap asin, garam, dan merica.",
            "Kentalkan dengan larutan maizena, sajikan panas.",
        ],
    },
    {
        "name":        "Gulai Kambing Padang",
        "author":      "Uda Herman",
        "portion":     "8 porsi",
        "cook_time":   "75 menit",
        "image_url":   "https://images.unsplash.com/photo-1631515243349-e0cb75fb8d3a?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "1 kg daging kambing",
            "600 ml santan kental",
            "10 buah cabai merah",
            "8 siung bawang putih",
            "10 siung bawang merah",
            "3 cm kunyit",
            "2 cm jahe",
            "3 batang serai",
            "Daun kunyit dan daun jeruk",
            "Garam secukupnya",
        ],
        "steps": [
            "Cuci bersih daging kambing, potong sesuai selera.",
            "Haluskan semua bumbu cabai, bawang, kunyit, dan jahe.",
            "Tumis bumbu halus bersama serai, daun kunyit, dan daun jeruk.",
            "Masukkan daging kambing, aduk hingga tercampur rata.",
            "Tuang santan, masak dengan api sedang sambil diaduk.",
            "Kecilkan api, masak hingga daging empuk dan kuah mengental.",
        ],
    },
    {
        "name":        "Tumis Kangkung Belacan",
        "author":      "Kak Mira",
        "portion":     "3 porsi",
        "cook_time":   "15 menit",
        "image_url":   "https://images.unsplash.com/photo-1625938144755-652e08e359b7?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "1 ikat kangkung",
            "1 sdt terasi",
            "5 buah cabai merah",
            "3 siung bawang putih",
            "5 siung bawang merah",
            "Garam dan gula secukupnya",
            "Minyak goreng",
        ],
        "steps": [
            "Petik kangkung, cuci bersih.",
            "Haluskan bawang merah, bawang putih, cabai, dan terasi.",
            "Panaskan minyak, tumis bumbu hingga harum.",
            "Masukkan kangkung, aduk cepat dengan api besar.",
            "Bumbui dengan garam dan gula.",
            "Angkat segera agar kangkung tidak layu terlalu lama.",
        ],
    },
    {
        "name":        "Ikan Bakar Bumbu Rujak",
        "author":      "Bapak Surya",
        "portion":     "4 porsi",
        "cook_time":   "40 menit",
        "image_url":   "https://images.unsplash.com/photo-1535399831218-d5bd36d1a6b3?w=900&q=80",
        "source":      "Cookpad",
        "ingredients": [
            "2 ekor ikan kakap",
            "8 buah cabai merah",
            "5 buah cabai rawit",
            "6 siung bawang putih",
            "4 siung bawang merah",
            "2 buah tomat",
            "1 sdm gula merah",
            "Garam secukupnya",
            "Air jeruk nipis",
        ],
        "steps": [
            "Bersihkan ikan, beri irisan dan lumuri air jeruk nipis.",
            "Haluskan bumbu cabai, bawang, tomat, dan gula merah.",
            "Lumuri ikan dengan bumbu rujak, diamkan 20 menit.",
            "Bakar ikan di atas bara api sambil dibolak-balik.",
            "Olesi bumbu setiap membalik ikan.",
            "Bakar hingga matang dan bumbu sedikit kering.",
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# ROTASI HARIAN
# ─────────────────────────────────────────────────────────────────────────────
def get_daily_recipes() -> tuple[dict, list[dict]]:
    """
    Rotasi berdasarkan hari ke-berapa dalam setahun.
    Return: (resep_hari_ini, [5 resep mingguan])
    """
    day = datetime.now().timetuple().tm_yday  # 1–365
    n   = len(RECIPES)

    # Resep hari ini — berputar tiap hari
    today_idx   = day % n
    today       = RECIPES[today_idx]

    # 5 resep mingguan — ambil 5 berikutnya, tidak ada duplikat dengan today
    weekly = []
    for i in range(1, n):
        idx = (today_idx + i) % n
        weekly.append(RECIPES[idx])
        if len(weekly) == 5:
            break

    return today, weekly


# ─────────────────────────────────────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
def build_for_you_page(on_recipe_click) -> ft.Container:
    """
    Bangun seluruh halaman For You.
    on_recipe_click(recipe: dict) — callback ke show_detail() di Gui.py
    """
    today, weekly = get_daily_recipes()

    # ── Hero card — Resep Hari Ini ──
    hero = ft.Container(
        height=260,
        content=ft.Stack(
            controls=[
                ft.Image(
                    src=today["image_url"],
                    width=float("inf"),
                    height=260,
                    fit=ft.ImageFit.COVER,
                ),
                ft.Container(
                    width=float("inf"),
                    height=260,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(0, 1),
                        end=ft.Alignment(0, -1),
                        colors=["#EE000000", "#22000000"],
                    ),
                ),
                ft.Container(
                    bottom=0, left=0, right=0,
                    padding=ft.padding.symmetric(horizontal=24, vertical=16),
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                today["name"],
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=WHITE,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text(f"👥 {today['portion']}", size=12, color=WHITE),
                                        bgcolor="#44000000",
                                        border_radius=ft.BorderRadius.all(20),
                                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                    ),
                                    ft.Container(
                                        content=ft.Text(f"⏱ {today['cook_time']}", size=12, color=WHITE),
                                        bgcolor="#44000000",
                                        border_radius=ft.BorderRadius.all(20),
                                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                    ),
                                    ft.Container(
                                        content=ft.Text(today["source"], size=12, color=WHITE),
                                        bgcolor="#44000000",
                                        border_radius=ft.BorderRadius.all(20),
                                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                    ),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=8,
                    ),
                ),
                # Tombol Lihat Resep
                ft.Container(
                    top=16, right=16,
                    content=ft.ElevatedButton(
                        "Lihat Resep →",
                        bgcolor=ORANGE,
                        color=WHITE,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=20),
                        ),
                        on_click=lambda e: on_recipe_click(today),
                    ),
                ),
            ],
        ),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border_radius=ft.BorderRadius.all(12),
        on_click=lambda e: on_recipe_click(today),
        ink=True,
    )

    # ── List item — Resep Mingguan ──
    def build_weekly_item(rank: int, recipe: dict) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    # Rank number
                    ft.Container(
                        content=ft.Text(
                            str(rank),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ORANGE if rank == 1 else TEXT2(),
                        ),
                        width=28,
                        alignment=ft.alignment.center,
                    ),
                    # Thumbnail
                    ft.Container(
                        width=64,
                        height=64,
                        content=ft.Image(
                            src=recipe["image_url"],
                            width=64,
                            height=64,
                            fit=ft.ImageFit.COVER,
                        ),
                        border_radius=ft.BorderRadius.all(8),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    # Info
                    ft.Column(
                        controls=[
                            ft.Text(
                                recipe["name"],
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT(),
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"👥 {recipe['portion']} · ⏱ {recipe['cook_time']} · {recipe['source']}",
                                size=12,
                                color=TEXT2(),
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    # Tombol lihat
                    ft.TextButton(
                        "Lihat",
                        style=ft.ButtonStyle(color=ORANGE),
                        on_click=lambda e, r=recipe: on_recipe_click(r),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER())),
            bgcolor=BG3(),
            on_click=lambda e, r=recipe: on_recipe_click(r),
            ink=True,
            on_hover=lambda e: (
                setattr(e.control, "bgcolor", BG4() if e.data else BG3()),
                e.control.update()
            ),
        )

    weekly_list = ft.Column(
        controls=[
            build_weekly_item(i + 1, r)
            for i, r in enumerate(weekly)
        ],
        spacing=0,
    )

    return ft.Container(
        expand=True,
        bgcolor=BG(),
        content=ft.Column(
            controls=[
                # ── Resep Hari Ini ──
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Resep Hari Ini 🔥", size=16, weight=ft.FontWeight.BOLD, color=TEXT()),
                            hero,
                        ],
                        spacing=12,
                    ),
                    padding=ft.padding.symmetric(horizontal=24, vertical=20),
                ),
                # ── Resep Mingguan ──
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Trending Minggu Ini 📅", size=16, weight=ft.FontWeight.BOLD, color=TEXT()),
                            ft.Container(
                                content=weekly_list,
                                border_radius=ft.BorderRadius.all(10),
                                border=ft.Border.all(1, BORDER()),
                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=ft.padding.only(left=24, right=24, bottom=24),
                ),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
    )