from pathlib import Path
from ..utils.helpers import shorten

ITEMS_DIR_NAME = "items"
LOGS_DIR_NAME = "logs"
PROJECT_DATA_DIR_NAME = ".spinetoolbox"
SPECIFICATIONS_DIR_NAME = "specifications"


class ProjectDir:
    """"""
    def __init__(self, project_dir_path):
        """
        Args:
            project_dir_path (Path or str): path to project directory
        """
        self._path = Path(project_dir_path)
        self._path.mkdir(exist_ok=True)
        project_data_dir = self._path / PROJECT_DATA_DIR_NAME
        project_data_dir.mkdir(exist_ok=True)
        items_dir = project_data_dir / ITEMS_DIR_NAME
        items_dir.mkdir(exist_ok=True)
        specifications_dir = project_data_dir / SPECIFICATIONS_DIR_NAME
        specifications_dir.mkdir(exist_ok=True)

    @property
    def path(self) -> Path:
        """Path to project dir."""
        return self._path

    @property
    def items_dir(self) -> Path:
        """Path to project items directory."""
        return self._path / PROJECT_DATA_DIR_NAME / ITEMS_DIR_NAME

    def add_project_item(self, name):
        """Creates item's data directory structure on disk.

        Does not do anything if data directory exists already.

        Args:
            name (str): name of item
        """
        data_dir = Path(self.items_dir) / shorten(name)
        data_dir.mkdir(exist_ok=True)
        logs_dir = data_dir / LOGS_DIR_NAME
        logs_dir.mkdir(exist_ok=True)

