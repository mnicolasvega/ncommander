from typing import Dict, Any
from web.Builder import Builder
import json
import os

class OutputParser:
    def build_html(self, tasks_output: Dict[str, dict]) -> None:
        output_path = self.__get_path("output.html")
        builder = Builder()
        for task_name, output in tasks_output.items():
            data = output.get('data', {})
            html = output.get('html', "")
            builder.add(task_name, html, data)
        html = builder.build()
        builder.save(output_path, html)

    def get_text(self, task_name: str, output_file: str = "output.txt") -> Dict[str, Any]:
        """
        Read output "output.txt" and return a Task's text_output as a dictionary.
        """
        try:
            output_path = self.__get_path(output_file)
            if not os.path.exists(output_path):
                return {}
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            prefix = f"{task_name}:"
            for raw in reversed(lines):
                line = raw.strip()
                if line.startswith(prefix):
                    _, _, content = line.partition(":")
                    content = content.strip()
                    try:
                        return json.loads(content)
                    except Exception:
                        return content
        except Exception:
            return {}
        return {}

    def get_html(self, task_name: str) -> str:
        """
        Read output {task_name}.html and return its HTML content as a string.
        This file is produced by the result of a TaskInterface method html_output.
        """
        try:
            html_path = self.__get_path(f"output/{task_name}.html")
            if not os.path.exists(html_path):
                return ""
            with open(html_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def __get_path(self, file_name: str) -> str:
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        return f"{commander_dir}/out/{file_name}"
