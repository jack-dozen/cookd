import flet as ft
from src.ui.views.main_window import main as gui_main

if __name__ == "__main__":
    print("Launching GUI from folder...")
    ft.run(gui_main, assets_dir="assets")
