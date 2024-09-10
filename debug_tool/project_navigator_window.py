import logging
import shutil
import tkinter as tk
from subprocess import run
from tkinter import Message, ttk
from typing import List, Optional

from inspection_window import InspectionWindow
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.pyplot import text
from project_data import DoloresProject

_LOGGER = logging.getLogger(__name__)


class ProjectNavigatorWindow:
    def __init__(self, root: tk.Tk, data: List[DoloresProject]) -> None:
        self.root = root
        self.data = data

        self.frame = ttk.Frame(self.root)
        self.toolstrip = ttk.Frame(self.root, height=32)
        self._configure_toolstrip()

        self.treeview = ttk.Treeview(
            self.frame, columns=("author", "date", "version", "correct")
        )
        self.scrollbar = ttk.Scrollbar(
            root, orient="vertical", command=self.treeview.yview
        )
        self.treeview.configure(yscrollcommand=self.scrollbar.set)
        self._configure_treeview()
        self._configure_fonts()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.toolstrip.grid(column=0, row=0, sticky="NEW")
        self.frame.grid(column=0, row=1, sticky="NSEW")

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        self.treeview.grid(column=0, row=0, sticky="NSEW")
        self.scrollbar.grid(column=1, row=1, sticky="NSEW")

        self.inspections = {}

    def _configure_treeview(self) -> None:
        # Display column names and guarantee they have enough width
        self.treeview.heading("#0", text="Project Name")
        self.treeview.column("#0", minwidth=200, width=250)
        self.treeview.heading(
            "author", text="Author", command=lambda: self._sort_data_by("author", False)
        )
        self.treeview.column("author", minwidth=100, width=100)
        self.treeview.heading(
            "date", text="Date", command=lambda: self._sort_data_by("date", False)
        )
        self.treeview.heading(
            "version",
            text="App Version",
            command=lambda: self._sort_data_by("version", False),
        )
        self.treeview.column("version", minwidth=120, width=120)
        self.treeview.heading(
            "correct",
            text="Correct",
            command=lambda: self._sort_data_by("correct", False),
        )
        self.treeview.column("correct", minwidth=120, width=120)

    def _configure_fonts(self) -> None:
        style = ttk.Style()
        style.configure("Treeview", font=("Helvetica", 12))
        style.configure("Treeview.Heading", font=("Arial", 14, "bold"))

    def _configure_toolstrip(self) -> None:
        bn_inspect = ttk.Button(
            self.toolstrip,
            text="Inspect",
            command=self.command_inspect,
        )
        bn_inspect.grid(column=0, row=1, sticky="NW")

        bn_open_ed = ttk.Button(
            self.toolstrip,
            text="Open in editor",
            command=self.command_open_in_editor,
        )
        bn_open_ed.grid(column=1, row=1, sticky="NW")

        bn_show_plot = ttk.Button(
            self.toolstrip,
            text="Show Plot",
            command=self.command_show_plot,
        )
        bn_show_plot.grid(column=2, row=1, sticky="NW")

        self.toolstrip.columnconfigure(3, weight=1)

        bn_delete = ttk.Button(
            self.toolstrip,
            text="Delete",
            command=self.command_delete_projects,
        )
        bn_delete.grid(column=4, row=1, sticky="NE")

    def update_project_data(self, data: List[DoloresProject]) -> None:
        for ii, project in enumerate(data):
            self.treeview.insert(
                "",
                "end",
                ii,
                text=project.metadata.name,
                values=(
                    project.metadata.contributor,
                    project.metadata.date,  # .strftime("%d/%m/%Y, %H:%M:%S"),
                    project.metadata.version,
                    "yes" if project.fully_loaded else "no",
                ),
            )

    def command_inspect(self) -> None:
        index = self.treeview.selection()

        if len(index) > 1:
            tk.messagebox.showinfo(
                title="Error", message="Select only one project to proceed"
            )
            return None

        if len(index) == 0:
            tk.messagebox.showinfo(
                title="Error", message="Select at least one project to proceed"
            )
            return None
        if len(index) == 1:
            selected = index[0]
            project = self.data[int(selected)]

            if project in self.inspections:
                tk.messagebox.showinfo(
                    title="Error", message="This project is already open"
                )
                return None

            if not project.fully_loaded:
                tk.messagebox.showinfo(
                    title="Error", message="This project cannot be loaded."
                )
                return None

            window = InspectionWindow(self.root, project)
            self.inspections[project] = window
            window.window.protocol(
                "WM_DELETE_WINDOW", lambda: self.close_inspection(project, window)
            )

    def command_open_in_editor(self) -> None:
        index = self.treeview.selection()
        for ii in map(int, index):
            run(["open", str(self.data[ii].project_file)])

    def command_show_plot(self) -> None:
        index = self.treeview.selection()
        for ii in map(int, index):
            project = self.data[ii]
            if project.fully_loaded:
                project.plot(project.id2slice, project.image_path, 0.2)

    def command_delete_projects(self) -> None:
        index = self.treeview.selection()

        if len(index) == 0:
            return

        answer = tk.messagebox.askyesno(
            "Confirm",
            "Are you sure you want to delete the project? This action cannot be undone",
        )

        if answer:
            elements_to_remove = []
            for ii in index:
                shutil.rmtree(self.data[int(ii)].project_path)
                self.treeview.delete(ii)
                elements_to_remove.append(self.data[int(ii)])

            for torm in elements_to_remove:
                self.data.remove(torm)

    def close_inspection(
        self, project: DoloresProject, window: InspectionWindow
    ) -> None:
        window.window.destroy()
        if project in self.inspections:
            del self.inspections[project]

    def _sort_data_by(self, column: str, reverse: bool) -> None:
        data_list = [
            (self.treeview.set(item, column), item)
            for item in self.treeview.get_children("")
        ]
        data_list.sort(key=lambda t: t[0], reverse=reverse)

        # Rearrange the items in the treeview
        for index, (val, item) in enumerate(data_list):
            self.treeview.move(item, "", index)

        # Toggle the sorting direction for the next time
        self.treeview.heading(
            column, command=lambda: self._sort_data_by(column, not reverse)
        )
