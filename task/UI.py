from task.FlaskTask import FlaskTask
from task.OutputParser import OutputParser
from typing import Any, Dict
import os

class UI(FlaskTask):
    """Extends FlaskTask to serve the generated output.html from web.Builder."""

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        """Start Flask server serving the output.html."""
        in_container = carry.get('in_container', False)
        dependency_error = self._check_flask_dependency(in_container)
        if dependency_error:
            return dependency_error
        dir_root = carry.get('outdir')
        default_host = '0.0.0.0' if in_container else self.LOCALHOST
        host = carry.get('host', default_host)
        port = int(carry.get('port', self.DEFAULT_PORT))
        script_path = self._get_task_log_dir(dir_root, "flask_server.py")
        log_path = self._get_task_log_dir(dir_root, "flask_server.log")
        pid_path = self._get_task_log_dir(dir_root, "flask_server.pid")
        url = f"http://{host}:{port}"
        error_existing_server = self._check_existing_server(pid_path, host, port, url)
        if error_existing_server:
            return error_existing_server
        self._generate_ui_server_script(script_path, host, port, dir_root)
        return self._start_server(script_path, pid_path, log_path, host, port, url)

    def name(self) -> str:
        return "ncommander_ui"

    def _generate_ui_server_script(self, script_path: str, host: str, port: int, dir_root: str) -> None:
        """Generate Flask server script from template with path, host and port substitution."""
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        output_html_path = os.path.join(os.path.dirname(dir_root), "tmp", "output.html")
        task_template_dir = os.path.join(os.path.dirname(dir_root), "task", "template")
        template_path = os.path.join(os.path.dirname(__file__), 'ui_server_template.py')
        with open(template_path, 'r', encoding='utf-8') as f:
            server_code = f.read()
        server_code = server_code \
            .replace('{{output_html_path}}', output_html_path) \
            .replace('{{task_template_dir}}', task_template_dir) \
            .replace('{{host}}', host) \
            .replace('{{port}}', str(port))
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(server_code)
