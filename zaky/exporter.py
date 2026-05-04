from tinydb import TinyDB
import json
import os


TABLES = [
    'my_recipes',
    'tokped_ingredients',
    'alfagift_ingredients',
    'recipes',
    'aeon_ingredients'
]

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')


def export_table(table_name: str) -> str:
    """
    Export satu tabel dari TinyDB ke file JSON di folder Downloads user.

    Args:
        table_name: Nama tabel yang mau diekspor

    Returns:
        Path file yang disimpan
    """
    db = TinyDB(DB_PATH)
    table = db.table(table_name)
    data = table.all()  # ambil semua record sebagai list

    # Format JSON kebawah (list of dict)
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    output_path = os.path.join(downloads_path, f'{table_name}.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"[{table_name}] Exported ke: {output_path}")
    return output_path


def export_selected(table_names: list[str]):
    """
    Export beberapa tabel sekaligus.

    Args:
        table_names: List nama tabel yang mau diekspor
    """
    for name in table_names:
        if name not in TABLES:
            print(f"[{name}] Tabel tidak dikenali, skip.")
            continue
        export_table(name)

    print("\nExport selesai!")


# ── untuk testing ──
if __name__ == '__main__':
     export_selected(['tokped_ingredients'])
