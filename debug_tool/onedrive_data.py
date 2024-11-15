from pathlib import Path
from typing import List, Optional
import os

from project_data import DoloresProject
from firebase_data import FirebaseData


class OneDriveData:
    def __init__(self, path: Optional[Path], firebase_data : FirebaseData) -> None:
        self.path = path
        self.projects = self._load_data(self.path)
        self.firebase_data = firebase_data

    def _load_data(self, path: Path) -> dict[str, list[str]]:
        output = {}

        for week in path.glob("*"):
            if week.is_dir():
                output[week.name] = []
                for file in week.glob("*"):
                    if file.name[-4:] == '.jpg':
                        output[week.name].append(file.name[:-4])

        return output

    def compare_with_firebase(self) -> dict:
        dict_done = {}
        for list in self.projects.values():
            for file in list:
                if file in self.firebase_data.list_of_files:
                    dict_done[file] = True
                else:
                    dict_done[file] = False

        return dict_done
            
        