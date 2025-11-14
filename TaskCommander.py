from container.Builder import Builder as DockerBuilder
from container.Cleaner import Cleaner
from docker.errors import DockerException
from docker.models.containers import Container
from task.OutputParser import OutputParser
from task.TaskInterface import TaskInterface
from TaskLauncher import TaskLauncher
from types import FrameType
from typing import Dict, Any, List, Optional, Tuple
import docker
import json
import os
import signal
import sys
import time

class TaskCommander:
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    PYTHON_IMAGE = "python:3.12-slim"
    VERSION = 0.1
    
    def __init__(
        self, 
        print_cycles: bool = False,
        print_docker_container_logs: bool = False,
        print_docker_container_lifecycle: bool = False,
        run_containerless: bool = True,
        force_rebuild: bool = True
    ):
        self._cfg = {
            'print_cycles': print_cycles,
            'print_docker_container_logs': print_docker_container_logs,
            'print_docker_container_lifecycle': print_docker_container_lifecycle,
            'run_containerless': run_containerless,
            'force_container_rebuild': force_rebuild
        }
        self.container_builder = DockerBuilder()
        self.output_parser = OutputParser()
        self.cleaner = Cleaner()
        self.last_execution = {}
        self.running_containers = {}

    def run(self, tasks: List[dict]) -> None:
        """Main execution loop for running tasks."""
        self._initialize()
        self._save_tasks_config(tasks)
        self._cleanup_orphaned()
        count = 0
        tasks_output = {}
        try:
            while True:
                count += 1
                if self._cfg['print_cycles']:
                    self._print(f"executing cycle #{count}")
                finished_tasks_output = self._handle_finished_tasks()
                for task_dict in tasks:
                    task_result = self._execute_task(task_dict)
                    if task_result:
                        task_name, execution_data = task_result
                        if task_name not in finished_tasks_output:
                            finished_tasks_output[task_name] = execution_data
                        else:
                            finished_tasks_output[task_name].update(execution_data)
                tasks_output.update(finished_tasks_output)
                time.sleep(1)
        except KeyboardInterrupt:
            self._print("interrupted by user")
        except Exception as e:
            self._print(f"unhandled exception: {e}")
        finally:
            self._cleanup_running()

    def _execute_task(self, task_dict: dict) -> Tuple[str, Dict[str, Any]] | None:
        """Execute a task if needed and return (task_name, execution_data) or None."""
        task = task_dict['task']
        params = task_dict['parameters']
        task_name = task.name()
        if self._should_run_task(task):
            execution_data = self._run_task(task, params)
            if 'container' in execution_data:
                self.running_containers[task_name] = execution_data['container']
            self.last_execution[task_name] = time.time()
            return task_name, execution_data
        return None

    def _run_task(self, task: TaskInterface, params: Dict[str, Any]) -> Dict[str, Any]:
        in_container = not self._cfg['run_containerless']
        params['outdir'] = self.container_builder.get_out_dir(in_container)
        params['in_container'] = in_container
        task_result = self._run_in_container(task, params) \
            if in_container else \
            self._run_containerless(task, params)
        return task_result

    def _run_containerless(self, task: TaskInterface, params: Dict[str, Any]) -> Dict[str, Any]:
        launcher = TaskLauncher(task)
        launcher.run(params)
        task_name = task.name()
        output_txt = self.output_parser.get_text(task_name, "output.txt")
        output_dict = self.output_parser.get_text(task_name, "output.log")
        output_html = self.output_parser.get_html(task_name)
        task_output = {
            'text': output_txt,
            'html': output_html,
            'data': output_dict
        }
        return task_output
    
    def _run_in_container(self, task: TaskInterface, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            container = self._run_container(task, params)
            execution_data = {
                'container': container,
                'task_name': task.name()
            }
            if self._cfg['print_docker_container_lifecycle']:
                self._print(f"'{task.name()}' started in container {container.short_id}")
        except DockerException as e:
            self._print(f"'{task.name()}' task docker error: {e.__str__()}")
            execution_data = {'exception': e}
        except Exception as e:
            self._print(f"'{task.name()}' task unhandled error: {e.__str__()}")
            execution_data = {'exception': e}
        return execution_data

    def _run_container(self, task: TaskInterface, params: Dict[str, Any]) -> Container:
        DONT_BLOCK_CONSOLE = True
        KILL_CONTAINER_AFTER_FINISH = False
        commander_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(f"{commander_dir}/tmp/tasks", exist_ok=True)
        client = docker.from_env()
        task_name = task.name()
        image_tag = f"task-commander:{task_name}"
        image_exists = self.container_builder.does_task_dockerfile_exist(client, commander_dir, task_name, image_tag)
        if not image_exists:
            dockerfile_template_path = f"{commander_dir}/container/Dockerfile"
            path_task_dir = f"{commander_dir}/tmp/tasks/{task_name}"
            os.makedirs(path_task_dir, exist_ok=True)
            os.makedirs(f"{path_task_dir}/container", exist_ok=True)
            self.container_builder.create_task_dockerfile(task, path_task_dir, dockerfile_template_path)
            if self._cfg['print_docker_container_lifecycle']:
                self._print(f"Building Docker image '{image_tag}' from {path_task_dir}")
            try:
                image, build_logs = client.images.build(
                    path = path_task_dir,
                    tag = image_tag,
                    rm = True,  # Remove intermediate containers
                    forcerm = True  # Always remove intermediate containers
                )
                if self._cfg['print_docker_container_lifecycle']:
                    self._print(f"Successfully built image {image.short_id}")
            except Exception as e:
                self._print(f"Failed to build Docker image: {e}")
                raise
        task_ports = task.ports(params)
        container = client.containers.run(
            image = image_tag,
            command = self.container_builder.get_container_cmd(task, params),
            detach = DONT_BLOCK_CONSOLE,
            remove = KILL_CONTAINER_AFTER_FINISH,
            working_dir = f"/app/tmp/tasks/{task_name}/container",
            volumes = self.container_builder.get_volumes(commander_dir, task, params),
            ports = task_ports,
            environment = {"PARAMS": json.dumps(params)},
            mem_limit = self.container_builder.get_memory(1),
            nano_cpus = self.container_builder.get_cpus(1),
            network_mode = self.container_builder.get_network_mode(task)
        )
        return container

    def _should_run_task(self, task: TaskInterface) -> bool:
        task_name = task.name()
        interval = task.interval()
        has_to_be_kept_alive = interval is None
        if has_to_be_kept_alive:
            if not self._cfg['run_containerless']:
                return task_name not in self.running_containers
            else:
                return task_name not in self.last_execution
        if task_name not in self.last_execution:
            return True
        time_elapsed = time.time() - self.last_execution[task_name]
        return time_elapsed >= interval

    def _handle_finished_tasks(self) -> Dict[str, dict]:
        containers_output = {}
        completed_containers = self._get_finished_containers()
        for task_name, container in completed_containers.items():
            try:
                logs = container.logs() \
                    .decode(errors="replace") \
                    .strip()
                exit_code = container.attrs['State']['ExitCode']
                output_txt = self.output_parser.get_text(task_name, "output.txt")
                output_dict = self.output_parser.get_text(task_name, "output.log")
                output_html = self.output_parser.get_html(task_name)
                containers_output[task_name] = {
                    'text': output_txt,
                    'html': output_html,
                    'data': output_dict
                }
                self._print(f"[{task_name}] output: {output_txt}")
                if self._cfg['print_docker_container_logs']:
                    self._print(f"[{task_name}] logs: \"{logs}\"")
                if self._cfg['print_docker_container_lifecycle']:
                    self._print(f"[docker] Container finished: {container.short_id} ({task_name}), exit code: {exit_code}")
                self._finish_container(task_name, container)
            except Exception as e:
                self._print(f"[docker] Error checking container {container.short_id}: {e}")
                self._finish_container(task_name, container)
        return containers_output

    def _get_finished_containers(self) -> Dict[str, Container]:
        completed_containers = {}
        for task_name, container in self.running_containers.items():
            try:
                container.reload()
                if container.status == 'exited':
                    completed_containers[task_name] = container
            except Exception as e:
                self._print(f"[docker] Warning: Could not reload container {container.short_id}: {e}")
                completed_containers[task_name] = container
        return completed_containers

    def _finish_container(self, task_name: str, container: Container) -> None:
        try:
            container.remove()
        except Exception as e:
            self._print(f"[docker] Warning: Could not remove container {container.short_id}: {e}")
        finally:
            if task_name in self.running_containers:
                del self.running_containers[task_name]

    def _print(self, message: str) -> None:
        timestamp = time.time()
        formatted_day_time = time.strftime(self.TIME_FORMAT, time.localtime(timestamp))
        formatted_message = f"[{formatted_day_time}] [commander] {message}"
        print(formatted_message)

    def _initialize(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._print(f">> commander v{self.VERSION}")

    def _save_tasks_config(self, tasks: List[dict]) -> None:
        """Save tasks configuration to a JSON file for UI server."""
        commander_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = f"{commander_dir}/tmp/output.json"
        tasks_config = [{
            'name': task_dict['task'].name(),
            'order': task_dict['order']
        } for task_dict in tasks]
        tasks_config = sorted(tasks_config, key=lambda x: x['order'])
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(tasks_config, f, indent=2)

    def _signal_handler(self, signal: int, frame: Optional[FrameType]) -> None:
        self._print(f"interrupt signal detected. Closing...")
        self._cleanup_running()
        sys.exit(0)

    def _cleanup_orphaned(self) -> None:
        """Cleanup orphaned containers from previous runs."""
        try:
            cleaned_ids = self.cleaner.cleanup_orphaned_containers()
            if cleaned_ids:
                cleaned_ids_str = ", ".join(cleaned_ids)
                self._print(f"Found {len(cleaned_ids)} orphaned container(s) from previous run:\n  {cleaned_ids_str}")
        except Exception as e:
            self._print(f"[docker] Warning: Could not check for orphaned containers: {e}")

    def _cleanup_running(self) -> None:
        """Cleanup currently running containers."""
        try:
            cleaned_ids = self.cleaner.cleanup_containers(self.running_containers)
            if cleaned_ids:
                self._print(f"Cleaning up {len(cleaned_ids)} running container(s)...")
                self._print("Cleanup complete")
        except Exception as e:
            self._print(f"[docker] Warning: Could not cleanup containers: {e}")
