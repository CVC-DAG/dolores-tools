import logging
from pathlib import Path
from typing import List, Optional
from subprocess import run
import os

from project_data import DoloresProject

_LOGGER = logging.getLogger(__name__)


class FirebaseData:
    def __init__(self, path: Optional[Path]) -> None:
        self.path = path
        self.data = self._load_data(self.path)
        self.list_of_files = self.get_list_of_files()

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
    
    
    def refresh_data(self) -> None:    
        command = ["gcloud", "storage", "cp", "-r", "gs://musicalignapp.appspot.com/uploads", str(self.path)[:-7]]
        run(command, shell=True)

        self.data = self._load_data(self.path)
        self.list_of_files = self.get_list_of_files()

    def get_list_of_files(self) -> List[str]:
        lst = []

        if os.name == 'posix':  # 'posix' means a Unix-like OS (Linux, macOS)
            split_char = '*'
        elif os.name == 'nt':   # 'nt' means Windows
            split_char = '$2'
        
        for project in self.data:
            name, *_ = project.project_name.split(split_char, maxsplit=1)
            lst.append(name)
        return lst
            
        