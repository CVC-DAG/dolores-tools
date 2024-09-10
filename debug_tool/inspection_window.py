import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from project_data import DoloresProject


class InspectionWindow(tk.Toplevel):
    def __init__(self, root: tk.Tk, project: DoloresProject) -> None:
        super().__init__(root)
        self.project = project

        self.title("DoLoReS Inspector")
        self.minsize(800, 600)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=32)
        self.rowconfigure(1, weight=1)

        self.toolstrip = ttk.Frame(self, height=32)
        self.app_area = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.toolstrip.grid(row=0, column=0, sticky="NWE")
        self.app_area.grid(row=1, column=0, sticky="NSWE")

        self.app_area.columnconfigure(0, weight=1)
        self.app_area.columnconfigure(1, weight=4)
        self.app_area.rowconfigure(0, weight=1)

        # LEFT PANE # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        s_left = ttk.Style()
        s_left.configure("Frame1.TFrame", background="red")

        self.left_pane = ttk.Frame(self.app_area)
        self.left_pane.grid(row=0, column=0, sticky="NSWE")
        self.app_area.add(self.left_pane)

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

        self.right_pane = ttk.Panedwindow(self.app_area, orient=tk.VERTICAL)
        self.right_pane.grid(row=0, column=1, sticky="NSWE")
        self.right_pane.columnconfigure(0, weight=1)
        self.app_area.add(self.right_pane)

        self.topright_frame = ttk.Frame(self.right_pane)
        self.botright_frame = ttk.Frame(self.right_pane)
        self.topright_frame.grid(column=0, row=0, sticky="NSWE")
        self.botright_frame.grid(column=0, row=1, sticky="NSWE")

        self.right_pane.add(self.topright_frame)
        self.right_pane.add(self.botright_frame)

        self.insp_toolbar_frame = ttk.Frame(self.topright_frame)
        self.gt_toolbar_frame = ttk.Frame(self.botright_frame)

        self.insp_figure = plt.figure()
        self.insp_canvas = FigureCanvasTkAgg(
            self.insp_figure, master=self.topright_frame
        )
        self.insp_toolbar = NavigationToolbar2Tk(
            self.insp_canvas, self.insp_toolbar_frame
        )

        self.gt_figure = plt.figure()
        self.gt_canvas = FigureCanvasTkAgg(self.gt_figure, master=self.botright_frame)
        self.gt_toolbar = NavigationToolbar2Tk(self.gt_canvas, self.gt_toolbar_frame)

        self.gt_selector_label = ttk.Label(
            self.gt_toolbar_frame,
            text="Transcript Image: ",
        )
        self.gt_selector = ttk.Combobox(self.gt_toolbar_frame)
        self._configure_selector()

        self.insp_canvas.get_tk_widget().grid(row=0, column=0, sticky="NSWE")
        self.insp_toolbar_frame.grid(row=1, column=0, sticky="WE")
        self.gt_canvas.get_tk_widget().grid(row=0, column=0, sticky="NSWE")
        self.gt_toolbar_frame.grid(row=1, column=0, sticky="WE")

        self.topright_frame.columnconfigure(0, weight=1)
        self.botright_frame.columnconfigure(0, weight=1)
        self.topright_frame.rowconfigure(0, weight=1)
        self.botright_frame.rowconfigure(0, weight=1)

        self.insp_toolbar.grid(row=0, column=0, sticky="W")

        self.gt_toolbar.grid(row=0, column=0, sticky="W")
        self.gt_selector_label.grid(row=0, column=1, sticky="W")
        self.gt_selector.grid(row=0, column=2, sticky="W")

        self.gt_toolbar_frame.columnconfigure(0, weight=1)
        self.insp_toolbar_frame.columnconfigure(0, weight=1)
        self.gt_toolbar_frame.rowconfigure(0, weight=1)
        self.insp_toolbar_frame.rowconfigure(0, weight=1)

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

    def _configure_selector(self) -> None: ...

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
