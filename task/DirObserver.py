from .BaseTask import BaseTask
from typing import Any, Dict, Tuple
import os

"""
Counts files in the specified directory.
"""
class DirObserver(BaseTask):
    def __init__(self, dir: str = "/") -> None:
        super().__init__()
        self._dir = dir

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if os.path.exists(self._dir) and os.path.isdir(self._dir):
                count_files, count_dirs = self._count_files_and_dirs()
                self._print(f"dir '{self._dir}' has {count_files} files and {count_dirs} directories.")
                return {
                    "count_files": count_files,
                    "count_dirs": count_dirs
                }
            else:
                self._print(f"dir '{self._dir}' does not exist, or is not a directory.")
                return {}
        except Exception as e:
            self._print(f"error while counting files in '{self._dir}': {e}")
            return {}

    def text_output(self, data: Dict[str, Any]) -> str:
        count_files = data['count_files'] if 'count_files' in data else 0
        count_dirs = data['count_dirs'] if 'count_dirs' in data else 0
        return f"dir '{self._dir}' has {count_files} files and {count_dirs} directories."

    def html_output(self, data: Dict[str, Any]) -> str:
        count_files = data['count_files'] if 'count_files' in data else 0
        count_dirs = data['count_dirs'] if 'count_dirs' in data else 0
        html = self._render_html_from_template('template/DirObserver.html', {
            'dir_path': self._dir,
            'count_files': str(count_files),
            'count_dirs': str(count_dirs),
        })
        return html

    def interval(self) -> int:
        return 3

    def name(self) -> str:
        return "dir_observer"

    def _count_files_and_dirs(self) -> Tuple[int, int]:
        files = [f for f in os.listdir(self._dir) if os.path.isfile(f"{self._dir}/{f}")]
        dirs = [f for f in os.listdir(self._dir) if os.path.isdir(f"{self._dir}/{f}")]
        count_files = len(files)
        count_dirs = len(dirs)
        return count_files, count_dirs