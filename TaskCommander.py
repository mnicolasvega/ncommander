from container.Builder import Builder as DockerBuilder
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
        self.last_execution = {}
        self.running_containers = {}
        
    def run(self, tasks: List[dict]) -> None:
        """Main execution loop for running tasks."""
        self._initialize()
        count = 0
        tasks_output = {}
        try:
            while True:
                count += 1
                if self._cfg['print_cycles']:
                    self._print(f"executing cycle #{count}")
                self.output_parser.build_html(tasks, tasks_output)
                finished_tasks_output = self._handle_finished_tasks()
                for task_dict in tasks:
                    task = task_dict['task']
                    params = task_dict['parameters']
                    task_name = task.name()
                    if self._should_run_task(task):
                        execution_data = self._run_task(task, params)
                        if task_name not in finished_tasks_output:
                            finished_tasks_output[task_name] = execution_data
                        else:
                            finished_tasks_output[task_name].update(execution_data)
                        if 'container' in execution_data:
                            self.running_containers[task_name] = execution_data['container']
                        self.last_execution[task_name] = time.time()
                    self.output_parser.build_html(tasks, tasks_output)
                tasks_output.update(finished_tasks_output)
                time.sleep(1)
        except KeyboardInterrupt:
            self._print("interrupted by user")
        except Exception as e:
            self._print(f"unhandled exception: {e}")

    def _run_task(self, task: TaskInterface, params: Dict[str, Any]) -> Dict[str, Any]:
        params['outdir'] = self.container_builder.get_out_dir(not self._cfg['run_containerless'])
        task_result = self._run_in_container(task, params) \
            if not self._cfg['run_containerless'] else \
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
        os.makedirs(f"{commander_dir}/out", exist_ok=True)
        client = docker.from_env()
        task_name = task.name()
        image_tag = f"task-commander:{task_name}"
        image_exists = self.container_builder.does_task_dockerfile_exist(client, commander_dir, task_name, image_tag)
        if not image_exists:
            dockerfile_template_path = f"{commander_dir}/docker/Dockerfile"
            path_task_dockerfile = f"{commander_dir}/docker/.generated/{task_name}"
            os.makedirs(path_task_dockerfile, exist_ok=True)
            self.container_builder.create_task_dockerfile(task, path_task_dockerfile, dockerfile_template_path)
            if self._cfg['print_docker_container_lifecycle']:
                self._print(f"Building Docker image '{image_tag}' from {path_task_dockerfile}")
            try:
                image, build_logs = client.images.build(
                    path = path_task_dockerfile,
                    tag = image_tag,
                    rm = True,  # Remove intermediate containers
                    forcerm = True  # Always remove intermediate containers
                )
                if self._cfg['print_docker_container_lifecycle']:
                    self._print(f"Successfully built image {image.short_id}")
            except Exception as e:
                self._print(f"Failed to build Docker image: {e}")
                raise
        container = client.containers.run(
            image = image_tag,
            command = self.container_builder.get_container_cmd(task, params),
            detach = DONT_BLOCK_CONSOLE,
            remove = KILL_CONTAINER_AFTER_FINISH,
            working_dir = "/app",
            volumes = {
                commander_dir: {
                    "bind": "/app",
                    "mode": "rw"
                }
            },
            environment = {"PARAMS": json.dumps(params)},
            mem_limit = self.container_builder.get_memory(1),
            nano_cpus = self.container_builder.get_cpus(1),
            network_mode = self.container_builder.get_network_mode(task)
        )
        return container

    def _should_run_task(self, task: TaskInterface) -> bool:
        task_name = task.name()
        if task_name not in self.last_execution:
            return True
        time_elapsed = time.time() - self.last_execution[task_name]
        return time_elapsed >= task.interval()

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

    def _signal_handler(self, signal: int, frame: Optional[FrameType]) -> None:
        self._print(f"interrupt signal detected. Closing...")
        sys.exit(0)
