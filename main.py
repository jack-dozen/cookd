import flet as ft
from hadi.Gui import main as gui_main

if __name__ == "__main__":
    print("Launching GUI from folder...")
    ft.run(gui_main, assets_dir="hadi")