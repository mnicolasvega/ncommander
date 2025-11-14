from docker.client import DockerClient
from task.TaskInterface import TaskInterface
from typing import Dict, Any, List
import docker
import json
import os

OUTPUT_DIR = "out"

class Builder:
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    PYTHON_IMAGE = "python:3.12-slim"
    VERSION = 0.1
    FORCE_REBUILD = True

    def create_task_dockerfile(self, task: TaskInterface, task_output_dir: str, dockerfile_template_path: str) -> None:
        if not os.path.exists(dockerfile_template_path):
            raise FileNotFoundError(f"Base Dockerfile template not found at {dockerfile_template_path}")
        with open(dockerfile_template_path, 'r') as f:
            template_content = f.read()
        apt_packages = task.dependencies().get('other', [])
        env_vars = task.dependencies().get('env', [])
        if apt_packages:
            apt_install_lines = []
            for pkg in apt_packages:
                apt_install_lines.append(f"    {pkg}")
            apt_install_str = " \\\n".join(apt_install_lines)
            apt_block = "\n".join([
                "# Install task-specific apt packages",
                "RUN apt-get update",
                "RUN apt-get install -y \\",
                apt_install_str,
                "RUN apt-get clean",
                "RUN rm -rf /var/lib/apt/lists/*"
            ])
        else:
            apt_block = ""
        env_block = "# Set environment variables" \
            if len(env_vars) > 0 \
            else ""
        for env in env_vars:
            env_block = env_block + f"\nENV {env}"
        replacements = {
            "task.apt_packages": apt_block,
            "task.env_vars": env_block,
            'task.name': task.name(),
        }
        docker_content = template_content
        for key, value in replacements.items():
            docker_content = docker_content.replace("{{" + key + "}}", value)
        dockerfile_path = f"{task_output_dir}/Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(docker_content)

    def does_task_dockerfile_exist(self, client: DockerClient, dir: str, task_name: str, image_tag: str) -> bool:
        image_exists = False
        has_dockerfile = os.path.exists(f"{dir}/docker/.generated/{task_name}/Dockerfile")
        if not self.FORCE_REBUILD and not has_dockerfile:
            try:
                client.images.get(image_tag)
                image_exists = True
                if self.print_docker_container_lifecycle:
                    self._print(f"Using cached Docker image '{image_tag}'")
            except docker.errors.ImageNotFound:
                image_exists = False
        return image_exists

    def get_memory(self, GBs: int) -> str:
        return f"{GBs}g"

    def get_cpus(self, count: int) -> int:
        return int(count * 1e9) # TODO: justify equivalence. Source?

    def get_network_mode(self, task: TaskInterface) -> str:
        uses_connection = task.requires_connection() or len(task.dependencies()) > 0
        return "default" if uses_connection else "none"

    def get_out_dir(self, in_container: bool = True) -> str:
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, "..", OUTPUT_DIR)
        return f"/app/{OUTPUT_DIR}" \
            if in_container else \
            full_path

    def get_container_cmd(self, task: TaskInterface, params: Dict[str, Any]) -> List[str]:
        output_dir = self.get_out_dir()
        dependencies = task.dependencies()
        pip_requirements = '\n'.join(dependencies.get('pip', []))
        cmd_pip_requirements = f"""cat > /tmp/requirements.txt << "EOF"
{pip_requirements}
EOF
python -m venv /tmp/venv
. /tmp/venv/bin/activate
pip install --no-cache-dir --root-user-action=ignore -r /tmp/requirements.txt"""
        cmd_run_python = f"""python TaskLauncher.py \
            --outdir {output_dir} \
            --task {task.__module__} \
            --data '{json.dumps(params)}'"""
        cmd_body = f"{cmd_pip_requirements} && {cmd_run_python}"
        if task.interval() is None:
            cmd_body = f"{cmd_body} && tail -f /dev/null"
        cmd = [
            "sh", "-c",
            cmd_body
        ]
        return cmd
