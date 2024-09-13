import tkinter as tk
from io import BytesIO
from tkinter import ttk

import cairosvg
import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.collections import PatchCollection
from PIL import Image
from project_data import DoloresProject


class InspectionWindow(tk.Toplevel):
    def __init__(self, root: tk.Tk, project: DoloresProject) -> None:
        super().__init__(root)
        self.project = project
        self.objects_to_draw = {}
        self.object_scale = 0.25

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
        self.inspector.bind("<<TreeviewSelect>>", self.on_inspector_selection_change)
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
        self.insert_inspector_data(self.project)  # MUST BE RUN BEFORE PLOTTING!

        # RIGHT PANE  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        self.right_pane = ttk.Panedwindow(self.app_area, orient=tk.VERTICAL)
        self.right_pane.grid(row=0, column=1, sticky="NSWE")
        self.right_pane.columnconfigure(0, weight=1)
        self.right_pane.rowconfigure(0, weight=3)
        self.right_pane.rowconfigure(1, weight=1)
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
        self.gt_selector = ttk.Combobox(self.gt_toolbar_frame, state="readonly")
        self.gt_selector.bind("<<ComboboxSelected>>", self.on_image_selector_change)
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

        # INSP FIGURE # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        ax = self.insp_figure.add_axes((0, 0, 1, 1))
        ax.set_axis_off()
        loaded_image = plt.imread(self.project.image_path)
        og_height, og_width, _ = loaded_image.shape
        loaded_image = cv2.resize(
            loaded_image,
            dsize=(
                int(og_width * self.object_scale),
                int(og_height * self.object_scale),
            ),
        )
        self.plotted_insp_image = ax.imshow(loaded_image)

        self.drawn_objects = {}
        for obj_id, obj in self.objects_to_draw.items():
            obj.set(fill=False, visible=False)
            ax.add_patch(obj)
            self.drawn_objects[obj_id] = obj

        plt.close(self.insp_figure)

        # GT FIGURE # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        self.gt_figure_ax = self.gt_figure.add_axes((0, 0, 1, 1))
        self.gt_figure_ax.set_axis_off()
        plt.close(self.gt_figure)

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

    def _configure_selector(self) -> None:
        elements = []
        for ii, img_slice in self.project.id2slice.items():
            if img_slice.gt_file is not None:
                elements.append(ii)

        self.gt_selector["values"] = (*elements, "None")
        self.gt_selector.current(len(self.gt_selector["values"]) - 1)

    def _sort_data_by(self, column: str, reverse: bool) -> None: ...

    def insert_inspector_data(self, data: DoloresProject) -> None:
        self.objects_to_draw = {}
        for slice_id, slice_data in data.id2slice.items():
            scaled_data = slice_data.scale(self.object_scale)

            node_id = f"slice{slice_id}"
            self.inspector.insert(
                "",
                "end",
                node_id,
                text=f"Line {slice_id}",
                values=(
                    "Music Line",
                    slice_id,
                    scaled_data.bbox,
                ),
            )
            slice_bbox = scaled_data.bbox.get_patch()
            slice_bbox.set(
                color="red" if slice_id % 2 == 0 else "darkred",
                alpha=0.25,
                fill=True,
                hatch="//",
            )
            self.objects_to_draw[node_id] = slice_bbox

            for ii, ann in enumerate(scaled_data.anns):
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
                patch = ann.get_poly_patch()
                patch.set_color(ann.category.get_category_color())
                self.objects_to_draw[f"{node_id}.annotation{ii}"] = patch

    def on_image_selector_change(self, event: tk.Event) -> None:
        selected = self.gt_selector.get()
        if selected == "None":
            self.gt_figure_ax.cla()
            self.gt_figure_ax.set_axis_off()
            self.gt_figure.canvas.draw()
            return None

        img_slice = self.project.id2slice[int(selected)]
        if img_slice.gt_file is not None:
            self.gt_figure_ax.cla()
            with open(img_slice.gt_file, "r") as f_in:
                img_png = cairosvg.svg2png(f_in.read())
            loaded_img = Image.open(BytesIO(img_png))
            self.gt_figure_ax.imshow(loaded_img)
            self.gt_figure_ax.set_axis_off()
            self.gt_figure.canvas.draw()

    def on_inspector_selection_change(self, event: tk.Event) -> None:
        selection = self.inspector.selection()

        for obj in self.drawn_objects.values():
            obj.set_visible(False)

        for selected in selection:
            self.drawn_objects[selected].set_visible(True)

        self.insp_figure.canvas.draw()
