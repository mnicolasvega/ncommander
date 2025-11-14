from .BaseTask import BaseTask
from typing import Any, Dict, List, Tuple
import os

"""
Counts files in the specified directories.
"""
class DirObserver(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        paths = carry.get('paths', ['/'])
        results = []
        for dir_path in paths:
            try:
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    count_files, count_dirs, file_names, dir_names = self._count_files_and_dirs(dir_path)
                    self._print(f"dir '{dir_path}' has {count_files} files and {count_dirs} directories.")
                    results.append({
                        "dir_path": dir_path,
                        "count_files": count_files,
                        "count_dirs": count_dirs,
                        "file_names": file_names,
                        "dir_names": dir_names
                    })
                else:
                    self._print(f"dir '{dir_path}' does not exist, or is not a directory.")
            except Exception as e:
                self._print(f"error while counting files in '{dir_path}': {e}")
        return {"paths": results}

    def text_output(self, data: Dict[str, Any]) -> str:
        paths = data.get('paths', [])
        if not paths:
            return "No directories observed"
        lines = []
        for path_data in paths:
            dir_path = path_data.get('dir_path', '/')
            count_files = path_data.get('count_files', 0)
            count_dirs = path_data.get('count_dirs', 0)
            lines.append(f"dir '{dir_path}' has {count_files} files and {count_dirs} directories.")
        return ' | '.join(lines)

    def html_output(self, data: Dict[str, Any]) -> str:
        paths = data.get('paths', [])
        if not paths:
            return "No directories observed"
        path_htmls = []
        for path_data in paths:
            dir_path = path_data.get('dir_path', '/')
            count_files = path_data.get('count_files', 0)
            count_dirs = path_data.get('count_dirs', 0)
            file_names = path_data.get('file_names', [])
            dir_names = path_data.get('dir_names', [])
            files_html = '\n'.join([f'<li>📄 {name}</li>' for name in file_names]) if file_names else ''
            dirs_html = '\n'.join([f'<li>📁 {name}</li>' for name in dir_names]) if dir_names else ''
            path_html = self._render_html_from_template('template/DirObserver.html', {
                'dir_path': dir_path,
                'count_files': str(count_files),
                'count_dirs': str(count_dirs),
                'files_list': files_html,
                'dirs_list': dirs_html
            })
            path_htmls.append(path_html)
        return '<br/>\n'.join(path_htmls)

    def interval(self) -> int:
        return 3

    def name(self) -> str:
        return "dir_observer"

    def _count_files_and_dirs(self, dir_path: str) -> Tuple[int, int, List[str], List[str]]:
        files = [f for f in os.listdir(dir_path) if os.path.isfile(f"{dir_path}/{f}")]
        dirs = [f for f in os.listdir(dir_path) if os.path.isdir(f"{dir_path}/{f}")]
        count_files = len(files)
        count_dirs = len(dirs)
        return count_files, count_dirs, files, dirs