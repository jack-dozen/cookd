from tinydb import TinyDB
import json
import os


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'base.json')


def import_my_recipes(file_path: str):
    """
    Import my_recipes.json ke tabel my_recipes di TinyDB.

    Args:
        file_path: Path ke file my_recipes.json
    """
    if not os.path.exists(file_path):
        print(f"File tidak ditemukan: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Format file tidak valid, harus berupa list of dict.")
        return

    db = TinyDB(DB_PATH)
    my_recipes = db.table('my_recipes')

    my_recipes.insert_multiple(data)
    print(f"Berhasil import {len(data)} resep ke tabel my_recipes.")


# ── untuk testing ──
# if __name__ == '__main__':
#     import_my_recipes(r'C:\Users\nama\Downloads\my_recipes.json')
