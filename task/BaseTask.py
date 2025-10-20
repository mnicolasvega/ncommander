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

    def requires_connection(self) -> bool:
        return False

    def max_time_expected(self) -> float | None:
        return None

    def dependencies(self) -> Dict[str, Any]:
        return {}

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
        return f"{dir_root}/task/{task_name}/{file_name}"
