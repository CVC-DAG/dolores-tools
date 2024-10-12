import logging
import tkinter as tk
from argparse import ArgumentParser, Namespace
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import askdirectory
from typing import List, Optional

from project_data import DoloresProject

_LOGGER = logging.getLogger(__name__)


class DebugToolApplication:
    def __init__(self, path: Optional[Path]) -> None:
        self.root = tk.Tk()
        self.root.title("DoLoReS Administrator")
        self.root.minsize(800, 600)

        if path is not None:
            self.path = path
        else:
            self.path = Path(
                askdirectory(mustexist=True, title="Triar Carpeta Arrel de Firebase")
            )

        self.data = self._load_data(self.path)

        # Delay the import until here to avoid circular import
        from project_navigator_window import ProjectNavigatorWindow

        self._nav_window = ProjectNavigatorWindow(self.root, self.data, self.path, self)
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
        "--project_path",
        help="Path to the folder storing DoLoReS user folders",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    app = DebugToolApplication(args.project_path)
    app.main()
