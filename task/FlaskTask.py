from task.BaseTask import BaseTask
from typing import Any, Dict
import os
import subprocess
import sys

class FlaskTask(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            __import__('flask')
        except Exception as e:
            self._print("Flask is not installed in the current environment. Install it with 'pip install flask' or run in container mode.")
            return {"status": "missing_dependency", "dependency": "flask", "error": str(e)}
        dir_root = carry['outdir']
        host = carry.get('host', '127.0.0.1')
        port = int(carry.get('port', 5000))
        script_path = self._get_task_log_dir(dir_root, "flask_server.py")
        pid_path = self._get_task_log_dir(dir_root, "flask_server.pid")
        log_path = self._get_task_log_dir(dir_root, "flask_server.log")
        url = f"http://{'localhost' if host in ['127.0.0.1', '0.0.0.0'] else host}:{port}"

        if os.path.exists(pid_path):
            try:
                with open(pid_path, 'r', encoding='utf-8') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                self._print(f"Flask already running pid {pid} at {url}")
                return {"status": "running", "pid": pid, "port": port, "host": host, "url": url}
            except Exception:
                try:
                    os.remove(pid_path)
                except Exception:
                    pass

        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        server_code = (
            "from flask import Flask\n"
            "app = Flask(__name__)\n"
            "@app.get('/')\n"
            "def index():\n"
            "    return 'hello world'\n"
            "if __name__ == '__main__':\n"
            f"    app.run(host='{host}', port={port})\n"
        )
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(server_code)

        with open(log_path, 'a', encoding='utf-8') as log_file:
            try:
                proc = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=log_file,
                    stderr=log_file,
                    start_new_session=True,
                    close_fds=True,
                )
                with open(pid_path, 'w', encoding='utf-8') as f:
                    f.write(str(proc.pid))
                self._print(f"Flask started pid {proc.pid} at {url}")
                return {"status": "started", "pid": proc.pid, "port": port, "host": host, "url": url, "log": log_path}
            except Exception as e:
                self._print(f"Failed to start Flask: {e}")
                return {"status": "error", "error": str(e)}

    def html_output(self, data: Dict[str, Any]) -> str:
        url = data.get('url', '')
        status = data.get('status', '')
        pid = data.get('pid', '')
        return f"<html><body><p>Flask server {status}. PID: {pid}. <a href='{url}' target='_blank'>{url}</a></p></body></html>"

    def text_output(self, data: Dict[str, Any]) -> str:
        status = data.get('status', '')
        url = data.get('url', '')
        if status == 'missing_dependency':
            return "Flask missing. Please install with 'pip install flask' or run in container mode."
        if status == 'error':
            return f"Error starting Flask: {data.get('error', '')}"
        if url:
            return f"{status} at {url}"
        return status or "no status"

    def interval(self) -> int:
        return 10

    def name(self) -> str:
        return "flask_task"

    def dependencies(self) -> Dict[str, Any]:
        return {"pip": ["flask"]}

    def requires_connection(self) -> bool:
        return False

    def max_time_expected(self) -> float | None:
        return 2.0
