import logging
import tkinter as tk
from argparse import ArgumentParser, Namespace
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import askdirectory
from typing import List, Optional

from project_data import DoloresProject
from firebase_data import FirebaseData
from project_navigator_window import ProjectNavigatorWindow
from onedrive_data import OneDriveData

_LOGGER = logging.getLogger(__name__)


class DebugToolApplication:
    def __init__(self, path: Optional[Path], onedrive_path: Optional[Path]) -> None:
        self.root = tk.Tk()
        self.root.title("DoLoReS Administrator")
        self.root.minsize(800, 600)

        if path is not None:
            self.path = path
        else:
            self.path = Path(
                askdirectory(mustexist=True, title="Triar Carpeta Arrel de Firebase")
            )
        
        if onedrive_path is not None:
            self.onedrive_path = onedrive_path
        else:
            self.onedrive_path = Path(
                askdirectory(mustexist=True, title="Triar Carpeta IMATGES_CLEAN de OneDrive")
            )

        self.firebase_data = FirebaseData(self.path)
        self.onedrive_data = OneDriveData(self.onedrive_path, self.firebase_data)        

        self._nav_window = ProjectNavigatorWindow(self.root, self.firebase_data, self.onedrive_data)
        self._nav_window.update_project_data(self.firebase_data.data)


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
    parser.add_argument(
        "--onedrive_path",
        help="Path to the OneDrive IMATGES_CLEAN folder",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    app = DebugToolApplication(args.project_path, args.onedrive_path)
    app.main()
