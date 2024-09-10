import tkinter as tk
from tkinter import ttk

from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.pyplot import style
from project_data import DoloresProject


class InspectionWindow:
    def __init__(self, root: tk.Tk, project: DoloresProject) -> None:
        self.project = project

        self.root = root
        self.window = tk.Toplevel(self.root)

        s_main = ttk.Style()
        s_main.configure("Frame0.TFrame", background="orange")

        s_toolstrip = ttk.Style()
        s_toolstrip.configure("Frame3.TFrame", background="yellow")

        self.window.title("DoLoReS Inspector")
        self.window.minsize(800, 600)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, minsize=32)
        self.window.rowconfigure(1, weight=1)

        self.toolstrip = ttk.Frame(self.window, height=32, style="Frame3.TFrame")
        self.app_area = ttk.Frame(self.window, style="Frame0.TFrame")
        self.toolstrip.grid(row=0, column=0, sticky="NWE")
        self.app_area.grid(row=1, column=0, sticky="NSWE")

        self.app_area.columnconfigure(0, weight=1)
        self.app_area.columnconfigure(1, weight=3)
        self.app_area.rowconfigure(0, weight=1)

        # LEFT PANE # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        s_left = ttk.Style()
        s_left.configure("Frame1.TFrame", background="red")

        self.left_pane = ttk.Frame(self.app_area, style="Frame1.TFrame")
        self.left_pane.grid(row=0, column=0, sticky="NSWE")

        self.left_pane.columnconfigure(0, weight=1)
        self.left_pane.rowconfigure(0, weight=1)
        self.left_pane.rowconfigure(1)

        self.inspector = ttk.Treeview(self.left_pane, columns=("class", "id", "bbox"))
        self.inspector.grid(row=0, column=0, sticky="NSWE")

        self.insp_y_scrollbar = ttk.Scrollbar(
            self.left_pane, orient="vertical", command=self.inspector.yview
        )
        self.inspector.configure(yscrollcommand=self.insp_y_scrollbar.set)
        self.insp_y_scrollbar.grid(column=1, row=0, sticky="NSE")

        self.insp_x_scrollbar = ttk.Scrollbar(
            self.left_pane, orient="horizontal", command=self.inspector.xview
        )
        self.inspector.configure(xscrollcommand=self.insp_x_scrollbar.set)
        self.insp_x_scrollbar.grid(column=0, row=1, sticky="SWE")

        self._configure_inspector()
        self.insert_inspector_data(self.project)

        # RIGHT PANE  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        s_right = ttk.Style()
        s_right.configure("Frame2.TFrame", background="blue")

        self.right_pane = ttk.Frame(self.app_area, style="Frame2.TFrame")
        self.right_pane.grid(row=0, column=1, sticky="NSWE")
        self.right_pane.columnconfigure(0, weight=1)
        self.right_pane.rowconfigure(0, weight=1)
        self.right_pane.rowconfigure(1, weight=1)

    def _configure_inspector(self) -> None:
        # Display column names and guarantee they have enough width
        self.inspector.heading("#0", text="Element")

        self.inspector.heading(
            "class", text="Class", command=lambda: self._sort_data_by("class", False)
        )
        self.inspector.heading(
            "id", text="ID", command=lambda: self._sort_data_by("id", False)
        )
        self.inspector.heading(
            "bbox",
            text="Bounding Box",
            command=lambda: self._sort_data_by("bbox", False),
        )

    def _sort_data_by(self, column: str, reverse: bool) -> None: ...

    def insert_inspector_data(self, data: DoloresProject) -> None:
        for slice_id, slice_data in data.id2slice.items():
            node_id = f"slice{slice_id}"
            self.inspector.insert(
                "",
                "end",
                node_id,
                text=f"Line {slice_id}",
                values=(
                    "Music Line",
                    slice_id,
                    slice_data.bbox,
                ),
            )

            for ii, ann in enumerate(slice_data.anns):
                self.inspector.insert(
                    node_id,
                    "end",
                    f"{node_id}.annotation{ii}",
                    text=f"",
                    values=(
                        ann.category.value,
                        ann.ident,
                        ann.bbox,
                    ),
                )