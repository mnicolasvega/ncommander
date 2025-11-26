from .TaskInterface import TaskInterface
from typing import Any, Dict, List
import json
import os
import time

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class BaseTask(TaskInterface):
    def __init__(self) -> None:
        self._logs = {}

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def dependencies(self) -> Dict[str, Any]:
        return {}

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        return {}

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def cpus(self) -> float:
        return 1.0

    def memory_gb(self) -> float:
        return 1.0

    def requires_connection(self) -> bool:
        return False

    def max_time_expected(self) -> float | None:
        return None

    def revive(self) -> bool:
        return False

    def text_output(self, data: Dict[str, Any]) -> str:
        return json.dumps(data)

    def html_output(self, data: Dict[str, Any]) -> str:
        return json.dumps(data)

    def logs(self) -> Dict[str, str]:
        return self._logs

    def _render_html_from_template(self, template_name: str, replacements: Dict[str, Any]) -> str:
        try:
            base_dir = os.path.dirname(__file__)
            template_path = f"{base_dir}/{template_name}"
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            for key, value in replacements.items():
                html = html.replace(f"{{{{%s}}}}" % (key), value)
            return html.strip()
        except Exception as e:
            return f"error formatting: {e}"

    def _print(self, message: str) -> None:
        timestamp = time.time()
        formatted_day_time = time.strftime(TIME_FORMAT, time.localtime(timestamp))
        formatted_message = f"[{formatted_day_time}] [{self.name()}] {message}"
        print(formatted_message)
        self._logs[timestamp] = formatted_message

    def _log(self, message: str) -> None:
        timestamp = time.time()
        self._logs[timestamp] = message

    def _get_task_log_dir(self, dir_root: str, file_name: str) -> str:
        task_name = self.name()
        return f"{dir_root}/tasks/{task_name}/container/{file_name}"

    def _get_volume(self, dir_path: str, params: Dict[str, Any]) -> str:
        """
        Convert host path to container path based on volume mappings.
        If the path is already a container path (starts with /app/), return it as-is.
        Otherwise, look up the path in the volume mappings to get the bind path.
        """
        if dir_path.startswith('/app/'):
            return dir_path
        volume_mappings = self.volumes(params)
        if dir_path in volume_mappings:
            return volume_mappings[dir_path]['bind']
        return dir_path

    def _get_task_data(self, task_name: str) -> Dict[str, Any]:
        """
        Read a JSON task file from the output directory and return its content.
        Raises an exception if the file is not found or cannot be parsed.
        """
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        output_dir = os.path.join(commander_dir, 'tmp', 'output')
        file_path = os.path.join(output_dir, f"{task_name}.json")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_var_relative_path(self, absolute_path: str) -> str:
        """
        Convert absolute path to relative path from var directory.
        E.g., /home/user/ncommander/var/task/file.jpg -> task/file.jpg
        """
        parts = absolute_path.split(os.sep)
        try:
            var_index = parts.index('var')
            return os.sep.join(parts[var_index + 1:])
        except (ValueError, IndexError):
            return absolute_path
