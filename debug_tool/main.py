import logging
import tkinter as tk
from argparse import ArgumentParser, Namespace
from pathlib import Path
from tkinter import ttk
from typing import List

from project_data import DoloresProject
from project_navigator_window import ProjectNavigatorWindow

_LOGGER = logging.getLogger(__name__)


class DebugToolApplication:
    def __init__(self, path: Path) -> None:
        self.root = tk.Tk()
        self.root.title("DoLoReS Administrator")
        self.root.minsize(800, 600)

        self.data = self._load_data(path)

        self._nav_window = ProjectNavigatorWindow(self.root, self.data)
        self._nav_window.update_project_data(self.data)

    def _load_data(self, path: Path) -> List[DoloresProject]:
        output = []
        for user_folder in [x for x in path.glob("*") if x.is_dir()]:
            for project in [x for x in user_folder.glob("*") if x.is_dir()]:
                try:
                    output.append(DoloresProject(project))
                except ValueError as e:
                    _LOGGER.warning(f"Could not load {str(project)}: {e}")
                except FileNotFoundError as e:
                    _LOGGER.warning(f"Could not load {str(project)}: {e}")
        return output

    def main(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "project_path",
        help="Path to the folder storing DoLoReS user folders",
        type=Path,
    )
    args = parser.parse_args()

    app = DebugToolApplication(args.project_path)
    app.main()