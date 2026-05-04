"""
formatter.py — CookD
Helper untuk format nilai ke string tampilan yang konsisten.
"""

from datetime import datetime


# ─────────────────────────────────────────────────────────────────────
# HARGA
# ─────────────────────────────────────────────────────────────────────
def format_price(price: int | float) -> str:
    """49900 → 'Rp 49.900'"""
    try:
        return f"Rp {int(price):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp -"

def parse_price(price_str: str) -> int:
    """'Rp 49.900' atau 'Rp\xa049.900' → 49900"""
    try:
        cleaned = (
            str(price_str)
            .replace("Rp", "")
            .replace("\xa0", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        return int(float(cleaned))
    except (ValueError, AttributeError):
        return 0


# ─────────────────────────────────────────────────────────────────────
# DURASI / WAKTU MASAK
# ─────────────────────────────────────────────────────────────────────
def format_duration(minutes: int | str | None) -> str:
    """
    60   → '1 jam'
    90   → '1 jam 30 menit'
    30   → '30 menit'
    None → '-'
    """
    if minutes is None:
        return "-"
    try:
        m = int(minutes)
    except (ValueError, TypeError):
        return str(minutes)  # sudah string seperti "30 menit"

    if m <= 0:
        return "-"
    hours, mins = divmod(m, 60)
    if hours and mins:
        return f"{hours} jam {mins} menit"
    elif hours:
        return f"{hours} jam"
    else:
        return f"{m} menit"


# ─────────────────────────────────────────────────────────────────────
# PERSENTASE KECOCOKAN
# ─────────────────────────────────────────────────────────────────────
def format_score(score: float) -> str:
    """0.875 → '88%'"""
    try:
        return f"{round(score * 100)}%"
    except (TypeError, ValueError):
        return "0%"

def format_score_label(score: float) -> str:
    """0.875 → '88% cocok'"""
    return f"{format_score(score)} cocok"


# ─────────────────────────────────────────────────────────────────────
# TANGGAL / WAKTU
# ─────────────────────────────────────────────────────────────────────
def now_str() -> str:
    """Return timestamp sekarang: '2025-01-15 14:30:00'"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_str() -> str:
    """Return tanggal hari ini: '2025-01-15'"""
    return datetime.now().strftime("%Y-%m-%d")

def format_scraped_at(iso_str: str) -> str:
    """
    '2025-01-15T14:30:00.123456' → '15 Jan 2025, 14:30'
    Fallback ke string asli kalau parsing gagal.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%-d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return str(iso_str)


# ─────────────────────────────────────────────────────────────────────
# TEKS UMUM
# ─────────────────────────────────────────────────────────────────────
def truncate(text: str, max_len: int = 60) -> str:
    """Potong teks panjang dengan ellipsis."""
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len - 1] + "…"

def clean_ingredient(text: str) -> str:
    """Bersihkan teks bahan dari newline dan spasi berlebih."""
    return " ".join(text.replace("\n", " ").split()).strip()

def capitalize_words(text: str) -> str:
    """'nasi goreng spesial' → 'Nasi Goreng Spesial'"""
    return text.title() if text else ""

def plural(count: int, singular: str, plural_form: str = "") -> str:
    """
    plural(1, 'resep')     → '1 resep'
    plural(3, 'resep')     → '3 resep'
    plural(3, 'bahan', 'bahan') → '3 bahan'  (Indonesian biasanya sama)
    """
    word = plural_form if plural_form and count != 1 else singular
    return f"{count} {word}"