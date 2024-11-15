import tkinter as tk
from io import BytesIO
from tkinter import ttk

# import cairosvg   # TEMPORALMENT FORA MENTRE NO TROBI UNA ALTERNATIVA MULTIPLATAFORMA
import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib._api import select_matching_signature
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.collections import PatchCollection
from PIL import Image
from project_data import DoloresProject


class ComparisonWindow(tk.Toplevel):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Check Projects")
        self.window.geometry("800x600")
        
        # Create a Treeview with two columns
        self.tree = ttk.Treeview(self.window, columns=("Projects", "Folder"), show="headings")
        self.tree.heading("Projects", text="Projects", command=lambda: self._sort_data_by("Projects", False))
        self.tree.heading("Folder", text="Folder", command=lambda: self._sort_data_by("Folder", False))

        # Define column widths
        self.tree.column("Projects", width=200)
        self.tree.column("Folder", width=100)

        self.tree.tag_configure('green', foreground='green')
        self.tree.tag_configure('red', foreground='red')

        # Add a scrollbar
        self.scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")

    def insert_comparison_data(self, bool_dict:  dict[str, bool], onedrive_files: dict[str, list[str]]) -> None:
        
        # Insert data into the Treeview
        for key, value in onedrive_files.items():
            for file in value:
                if bool_dict[file]:
                    self.tree.insert("", "end", values=(file, key), tags=('green',))
                else:
                    self.tree.insert("", "end", values=(file, key), tags=('red',))

        # Pack the Treeview widget
        self.tree.pack(expand=True, fill="both")

    def _sort_data_by(self, column: str, reverse: bool) -> None:
        data_list = [
            (self.tree.set(item, column), item)
            for item in self.tree.get_children("")
        ]
        data_list.sort(key=lambda t: t[0], reverse=reverse)

        # Rearrange the items in the treeview
        for index, (val, item) in enumerate(data_list):
            self.tree.move(item, "", index)

        # Toggle the sorting direction for the next time
        self.tree.heading(
            column, command=lambda: self._sort_data_by(column, not reverse)
        )
