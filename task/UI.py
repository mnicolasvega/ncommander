import os
from task.FlaskTask import FlaskTask
from typing import Any, Dict

class UI(FlaskTask):
    """Extends FlaskTask to dynamically generate and serve HTML from task outputs."""

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        """Start Flask server that dynamically generates HTML from task outputs."""
        in_container = carry.get('in_container', False)
        self._print(f"UI.run start - in_container={in_container}, carry_keys={list(carry.keys())}")
        dependency_error = self._check_flask_dependency(in_container)
        if dependency_error:
            self._print(f"Dependency check failed for Flask: {dependency_error}")
            return dependency_error
        dir_root = carry.get('outdir')
        self._print(f"Resolved dir_root={dir_root}")
        default_host = '0.0.0.0' if in_container else self.LOCALHOST
        host = carry.get('host', default_host)
        port = int(carry.get('port', self.DEFAULT_PORT))
        self._print(f"Resolved host/port: {host}:{port}")
        script_path = self._get_task_log_dir(dir_root, "flask_server.py")
        log_path = self._get_task_log_dir(dir_root, "flask_server.log")
        pid_path = self._get_task_log_dir(dir_root, "flask_server.pid")
        self._print(f"Paths - script={script_path}, log={log_path}, pid={pid_path}")
        url = f"http://{host}:{port}"
        error_existing_server = self._check_existing_server(pid_path, host, port, url)
        if error_existing_server:
            self._print(f"Existing server detected: {error_existing_server}")
            return error_existing_server
        self._print("Generating UI server script from template")
        self._generate_ui_server_script(script_path, host, port, dir_root)
        self._print(f"Starting UI Flask server at {url}")
        return self._start_server(script_path, pid_path, log_path, host, port, url)

    def name(self) -> str:
        return "ncommander_ui"

    def _generate_ui_server_script(self, script_path: str, host: str, port: int, dir_root: str) -> None:
        """Generate Flask server script from template with path, host and port substitution."""
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        task_template_dir = os.path.join(os.path.dirname(dir_root), "task", "template")
        tasks_config_path = os.path.join(os.path.dirname(dir_root), "cfg", "ui_config.json")
        var_dir = os.path.join(os.path.dirname(dir_root), "var")
        template_path = os.path.join(os.path.dirname(__file__), 'ui_server_template.py')
        self._print(f"Generating server script using template {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            server_code = f.read()
        server_code = server_code \
            .replace('{{task_template_dir}}', task_template_dir) \
            .replace('{{tasks_config_path}}', tasks_config_path) \
            .replace('{{var_dir}}', var_dir) \
            .replace('{{host}}', host) \
            .replace('{{port}}', str(port))
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(server_code)
        self._print(f"Server script written to {script_path}")
