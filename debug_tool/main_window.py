import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(8, 6), dpi=150)
        self.frame = ttk.Frame(self)
        self.treeview = ttk.Treeview(self.frame, columns=("Annotation", "Type"))
        self.figure_frame = ttk.Frame(self.frame)
        self.canvas = FigureCanvasTkAgg(self.figure, self.figure_frame)

        self.figure.grid(column=0, row=0)
