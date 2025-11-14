from typing import Dict, Any, List
from web.Builder import Builder
import json
import os

class OutputParser:
    def build_html(self, tasks: List[dict], tasks_output: Dict[str, dict]) -> None:
        tasks = sorted(tasks, key=lambda x: x['order'])
        output_path = self.__get_path("output.html")
        builder = Builder()
        task_names = [task_dict['task'].name() for task_dict in tasks]
        tasks_execution_data = {}
        tasks_execution_data.update(self._load_previous_task_executions(task_names, tasks_output))
        tasks_execution_data.update(self._load_task_executions(tasks_output))
        for task_data in tasks:
            task_name = task_data['task'].name()
            if task_name in tasks_execution_data:
                builder.add(task_name, tasks_execution_data[task_name])
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

    def get_json(self, task_name: str) -> Dict[str, Any]:
        """
        Read output {task_name}.json and return its content as a dictionary.
        This file contains the complete task output including timing data.
        """
        try:
            json_path = self.__get_path(f"output/{task_name}.json")
            if not os.path.exists(json_path):
                return {}
            with open(json_path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_task_executions(self, tasks_output: Dict[str, dict]) -> Dict[str, dict]:
        tasks = {}
        for task_name, output in tasks_output.items():
            data = output.get('data')
            if not data:
                data = self.get_json(task_name)
            html = output.get('html')
            if not html:
                html = self.get_html(task_name)
            tasks[task_name] = {
                'html': html,
                'data': data,
                'is_previous': False
            }
        return tasks

    def _load_previous_task_executions(self, task_names: List[str], tasks_output: Dict[str, dict]) -> Dict[str, dict]:
        previous_tasks = {}
        for task_name in task_names:
            if task_name not in tasks_output:
                html = self.get_html(task_name)
                data = self.get_json(task_name)
                if html or data:
                    previous_tasks[task_name] = {
                        'html': html,
                        'data': data,
                        'is_previous': True
                    }
        return previous_tasks

    def __get_path(self, file_name: str) -> str:
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        return f"{commander_dir}/tmp/{file_name}"
