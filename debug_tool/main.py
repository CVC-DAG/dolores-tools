import tkinter as tk
from tkinter import ttk

from main_window import MainWindow


class DebugToolApplication:
    def __init__(self) -> None:
        self._window = MainWindow()

    def main(self) -> None:
        ...


if __name__ == "__main__":
    app = DebugToolApplication()
    app.main()
