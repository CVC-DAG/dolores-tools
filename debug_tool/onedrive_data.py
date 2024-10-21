import logging
from pathlib import Path
from typing import List, Optional
from subprocess import run
import os

from project_data import DoloresProject

_LOGGER = logging.getLogger(__name__)


class OneDriveData:
    def __init__(self, path: Optional[Path]) -> None:
        self.path = path
        self.projects = self._load_data(self.path)

    def _load_data(self, path: Path) -> List[DoloresProject]:
        output = {}
        for week in os.listdir(path):
            output[week] = []
            for file in os.listdir(os.path.join(path, week)):
                if file[-4:] == '.jpg':
                    output[week].append(file)

        return output
    
    
    def refresh_data(self) -> None:    
        command = ["gcloud", "storage", "cp", "-r", "gs://musicalignapp.appspot.com/uploads", str(self.path)[:-7]]
        run(command)

        self.data = self._load_data(self.path)
            
        