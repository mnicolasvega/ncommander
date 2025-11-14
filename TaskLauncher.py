from task.TaskInterface import TaskInterface
from typing import Any, Dict, Tuple
import argparse
import importlib
import json
import os
import time

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class TaskLauncher:
    def __init__(self, task: TaskInterface) -> None:
        self._task = task
        self._logs = {}
        self._time_elapsed_ms = 0

    def run(self, params: Dict[str, Any]) -> None:
        try:
            output_path = params['outdir']
            self._create_dirs(output_path)
            self._log(f"executing - params: {params}")
            time_start = time.perf_counter()
            output = self._task.run(params)
            text_output = self._task.text_output(output)
            html_output = self._task.html_output(output)
            time_now = time.perf_counter()
            self._time_elapsed_ms = (time_now - time_start) * 1000.0
            output['time_elapsed_ms'] = self._time_elapsed_ms
            output['time_finish_ms'] = time.time() * 1000.0
            if (self._task.max_time_expected() is not None) and (self._time_elapsed_ms > self._task.max_time_expected()):
                self._log(f"task took too long: {self._time_elapsed_ms} secs.")
            self._write_container_logs(output_path, output)
            self._write_task_output(output_path, text_output)
            self._write_task_html_output(output_path, html_output)
        except PermissionError as e:
            self._log(f"permission error: {e}")
        except Exception as e:
            self._log(f"unhandled exception: {e}")

    def elapsed_time(self) -> float:
        return self._time_elapsed_ms

    def logs(self) -> Dict[float, str]:
        return self._logs

    def _log(self, message: str) -> None:
        timestamp = time.time()
        self._logs[timestamp] = message

    def _create_dirs(self, output_path: str) -> None:
        os.makedirs(output_path, exist_ok=True)
        task_dir = f"{output_path}/tasks/{self._task.name()}"
        os.makedirs(task_dir, exist_ok=True)
        os.makedirs(f"{task_dir}/container", exist_ok=True)

    def _write_container_logs(self, output_path: str, result: Dict[str, Any]) -> None:
        json_str = json.dumps(result, ensure_ascii=False)
        with open(f"{output_path}/output.log", "a", encoding="utf-8") as f:
            f.write("%s: %s\n" % (self._task.name(), json_str))

    def _write_task_output(self, output_path: str, text_output: str) -> None:
        with open(f"{output_path}/output.txt", "a", encoding="utf-8") as f:
            f.write("%s: %s\n" % (self._task.name(), text_output))

    def _write_task_html_output(self, output_path: str, html_output: str) -> None:
        with open(f"{output_path}/tasks/{self._task.name()}/out.html", "w", encoding="utf-8") as f:
            f.write(html_output)

def _get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", required=True, help="Output dir inside container")
    p.add_argument("--task", required=True, help="Module path of the task to run")
    p.add_argument("--data", required=True, help="JSON config")
    args = p.parse_args()
    return args

def _load_params() -> Tuple[TaskInterface, Dict[str, Any]]:
    args = _get_args()
    module = importlib.import_module(args.task)
    class_name = args.task.split('.')[-1]
    task_class = getattr(module, class_name)
    task = task_class()
    params = json.loads(args.data)
    params.update({'args': args})
    return task, params

if __name__ == "__main__":
    task, params = _load_params()
    launcher = TaskLauncher(task)
    launcher.run(params)
