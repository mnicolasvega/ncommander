from .BaseTask import BaseTask
from typing import Any, Dict, List, Tuple
import os

"""
Counts files in the specified directories.
"""
class DirObserver(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        input_paths = carry.get('paths', [])
        paths = []
        for original_path in input_paths:
            dir_path = self._get_volume(original_path, carry)
            try:
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    count_files, count_dirs, file_names, dir_names, total_size = self._count_files_and_dirs(dir_path)
                    self._print(f"dir '{original_path}' has {count_files} files and {count_dirs} directories.")
                    paths.append({
                        "dir_path": original_path,
                        "count_files": count_files,
                        "count_dirs": count_dirs,
                        "file_names": file_names,
                        "dir_names": dir_names,
                        "total_size": total_size
                    })
                else:
                    self._print(f"dir '{original_path}' does not exist, or is not a directory.")
            except Exception as e:
                self._print(f"error while counting files in '{original_path}': {e}")
        return {"paths": paths}

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
            file_names = sorted(path_data.get('file_names', []))
            dir_names = sorted(path_data.get('dir_names', []))
            total_size_bytes = path_data.get('total_size', 0)
            items = []
            items.extend([f'<li>📁 {name}</li>' for name in dir_names])
            items.extend([f'<li>📄 {name}</li>' for name in file_names])
            items_html = '\n'.join(items) if items else ''
            total_count = count_files + count_dirs
            path_html = self._render_html_from_template('template/DirObserver.html', {
                'dir_path': dir_path,
                'total_count': str(total_count),
                'total_size': self._format_size(total_size_bytes),
                'items_list': items_html
            })
            path_htmls.append(path_html)
        return '<br/>\n'.join(path_htmls)

    def interval(self) -> int:
        return 3

    def name(self) -> str:
        return "dir_observer"

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        paths = params.get('paths', [])
        volumes = {}
        for path in paths:
            if not path.startswith('/app/'):
                safe_path = path.replace('/', '_').strip('_')
                container_path = f"/mnt/observer/{safe_path}"
                volumes[path] = {
                    "bind": container_path,
                    "mode": "ro"
                }
        return volumes

    def _count_files_and_dirs(self, dir_path: str) -> Tuple[int, int, List[str], List[str], int]:
        files = [f for f in os.listdir(dir_path) if os.path.isfile(f"{dir_path}/{f}")]
        dirs = [f for f in os.listdir(dir_path) if os.path.isdir(f"{dir_path}/{f}")]
        count_files = len(files)
        count_dirs = len(dirs)
        total_size = 0
        for f in files:
            try:
                total_size += os.path.getsize(f"{dir_path}/{f}")
            except OSError:
                pass
        return count_files, count_dirs, files, dirs, total_size

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable format."""
        if size_bytes == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
