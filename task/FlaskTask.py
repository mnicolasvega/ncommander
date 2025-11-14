from task.BaseTask import BaseTask
from typing import Any, Dict
import os
import subprocess
import sys

class FlaskTask(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        in_container = carry.get('in_container', False)
        if not in_container:
            try:
                __import__('flask')
            except Exception as e:
                self._print("Flask is not installed in the current environment. Install it with 'pip install flask' or run in container mode.")
                return {"status": "missing_dependency", "dependency": "flask", "error": str(e)}
        dir_root = carry.get('outdir')
        host = carry.get('host', '127.0.0.1')
        port = int(carry.get('port', 5000))
        script_path = self._get_task_log_dir(dir_root, "flask_server.py")
        log_path = self._get_task_log_dir(dir_root, "flask_server.log")
        url = f"http://{'localhost' if host in ['127.0.0.1', '0.0.0.0'] else host}:{port}"

        pid_path = self._get_task_log_dir(dir_root, "flask_server.pid")
        existing_server = self._check_existing_server(pid_path, host, port, url)
        if existing_server:
            return existing_server

        self._generate_server_script(script_path, host, port)
        return self._start_server(script_path, pid_path, log_path, host, port, url)

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

    def interval(self) -> int | None:
        return None

    def name(self) -> str:
        return "flask_task"

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": ["flask"]
        }

    def requires_connection(self) -> bool:
        return False

    def max_time_expected(self) -> float | None:
        return 2.0

    def _start_server(self, script_path: str, pid_path: str, log_path: str, host: str, port: int, url: str) -> Dict[str, Any]:
        """Start Flask server process and return status dict."""
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

    def _generate_server_script(self, script_path: str, host: str, port: int) -> None:
        """Generate Flask server script from template with host and port substitution."""
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        template_path = os.path.join(os.path.dirname(__file__), 'flask_server_template.py')
        with open(template_path, 'r', encoding='utf-8') as f:
            server_code = f.read()
        server_code = server_code \
            .replace('{{host}}', host) \
            .replace('{{port}}', str(port))
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(server_code)

    def _check_existing_server(self, pid_path: str, host: str, port: int, url: str) -> Dict[str, Any] | None:
        """Check if Flask server is already running. Returns status dict if running, None otherwise."""
        if not os.path.exists(pid_path):
            return None
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
            return None
