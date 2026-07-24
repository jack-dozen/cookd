# Refactoring Cookd-App: Migrasi Sisa File ke `src/`

## Latar Belakang

Codebase saat ini **setengah jadi** — beberapa file sudah dipindah ke `src/` (dengan import yang benar), tapi masih ada 4 file besar yang masih berada di folder pribadi (`fadhil/`, `rafy/`, `zaky/`) dengan import yang masih menggunakan path lama (`from rafy.theme import ...`). Akibatnya, import di `src/ui/views/main_window.py` dan `src/ui/components/save_btn.py` **akan error** saat runtime.

## Masalah yang Ditemukan

### File yang masih harus dimigrasikan dari folder pribadi ke `src/`:

| File Sumber (lama) | Target di `src/` | Import di src yang sudah merujuknya |
|---|---|---|
| `fadhil/my_recipes.py` | `src/ui/views/my_recipes.py` | `main_window.py`, `save_btn.py` |
| `rafy/for_you_ui.py` | `src/ui/views/for_you.py` | `main_window.py` |
| `zaky/price_panel.py` | `src/ui/views/price_panel.py` | `detail.py` |
| `zaky/info.py` | `src/ui/views/info.py` | `main_window.py` |

### Import lama yang perlu diupdate di file-file tersebut:

| File | Import Lama | Import Baru |
|---|---|---|
| `my_recipes.py` | `from rafy.theme import ...` | `from src.core.theme import ...` |
| `my_recipes.py` | `from rafy.snackbar import ...` | `from src.ui.components.snackbar import ...` |
| `my_recipes.py` | `DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')` | Path yang benar relatif ke root |
| `for_you_ui.py` | `from rafy.theme import ...` | `from src.core.theme import ...` |
| `price_panel.py` | `from rafy.theme import ...` | `from src.core.theme import ...` |
| `price_panel.py` | `from rafy.ingredient_price_list import ...` | `from src.ui.components.ingredient_price_list import ...` |
| `price_panel.py` | `from rafy.snackbar import ...` | `from src.ui.components.snackbar import ...` |
| `info.py` | `from rafy.theme import ...` | `from src.core.theme import ...` |

### File lain:
- `main.py` saat ini: `ft.run(gui_main, assets_dir="hadi")` — perlu diubah ke `assets_dir="assets"` karena font & gambar sudah di `assets/`
- `src/ui/components/sidebar_extras.py` docstring masih menyebut `rafy/sidebar.py` — perlu diupdate

## Proposed Changes

### 1. Migrasi Files

#### [NEW] [my_recipes.py](file:///c:/Users/zkyal/College%20(Local)/Proyek%201%20PPLD/cookd-app/src/ui/views/my_recipes.py)
Salin dari `fadhil/my_recipes.py`, update import:
- `from rafy.snackbar import show_snack` → `from src.ui.components.snackbar import show_snack`
- `from rafy.theme import theme_mgr` → `from src.core.theme import theme_mgr`
- `DB_PATH` path disesuaikan: `os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'base.json')`

#### [NEW] [for_you.py](file:///c:/Users/zkyal/College%20(Local)/Proyek%201%20PPLD/cookd-app/src/ui/views/for_you.py)
Salin dari `rafy/for_you_ui.py`, update import:
- `from rafy.theme import ...` → `from src.core.theme import ...`

#### [NEW] [price_panel.py](file:///c:/Users/zkyal/College%20(Local)/Proyek%201%20PPLD/cookd-app/src/ui/views/price_panel.py)
Salin dari `zaky/price_panel.py`, update import:
- `from rafy.theme import ...` → `from src.core.theme import ...`
- `from rafy.ingredient_price_list import ...` → `from src.ui.components.ingredient_price_list import ...`
- `from rafy.snackbar import ...` → `from src.ui.components.snackbar import ...`
- Hapus sys.path hacks

#### [NEW] [info.py](file:///c:/Users/zkyal/College%20(Local)/Proyek%201%20PPLD/cookd-app/src/ui/views/info.py)
Salin dari `zaky/info.py`, update import:
- `from rafy.theme import ...` → `from src.core.theme import ...`

### 2. Update File yang Ada

#### [MODIFY] [main.py](file:///c:/Users/zkyal/College%20(Local)/Proyek%201%20PPLD/cookd-app/main.py)
- Ganti `assets_dir="hadi"` → `assets_dir="assets"`

#### [MODIFY] [sidebar_extras.py](file:///c:/Users/zkyal/College%20(Local)/Proyek%201%20PPLD/cookd-app/src/ui/components/sidebar_extras.py)
- Update docstring yang masih menyebut `rafy/`

## Verification Plan

### Manual Verification
- Jalankan `python main.py` dan pastikan aplikasi terbuka tanpa error
- Cek semua halaman: Home, Finder, My Recipes, For You, Info
- Cek font sudah muncul (karena `assets_dir` diubah)

> [!NOTE]
> Folder `fadhil/`, `rafy/`, `zaky/` **tidak dihapus** untuk sementara — sebagai backup. Setelah verifikasi berjalan lancar, folder tersebut bisa dihapus manual.
