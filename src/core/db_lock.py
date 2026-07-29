"""
db_lock.py — shared locks untuk seluruh project
Import dari mana saja:
    from src.core.db_lock import DB_LOCK, DRIVER_INIT_LOCK
"""

import threading

# RLock: reentrant — thread yang sama boleh acquire berkali-kali tanpa deadlock.
# Dipakai oleh TokopediaScraper, AlfagiftScraper, AEONScraper, dan
# PriceComparisonService untuk menjaga konsistensi satu file TinyDB.
DB_LOCK: threading.RLock = threading.RLock()

# Lock untuk serialisasi inisialisasi undetected_chromedriver.
# uc.Chrome() tidak thread-safe saat copy chromedriver.exe di Windows
# (WinError 183: file already exists). Semua scraper yang pakai uc.Chrome()
# harus acquire lock ini sebelum memanggil init_driver().
DRIVER_INIT_LOCK: threading.Lock = threading.Lock()
