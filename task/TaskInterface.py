from abc import ABC, abstractmethod
from typing import Dict, Any, List

class TaskInterface(ABC):
    @abstractmethod
    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the task with the given parameters and return the result carry.
        """
        pass

    @abstractmethod
    def interval(self) -> int | None:
        """
        Return the interval in seconds between runs.
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """
        Return the name of the task.
        """
        pass

    @abstractmethod
    def text_output(self, data: Dict[str, Any]) -> str:
        """
        Return a human-readable string representation of the task output.
        """
        pass

    @abstractmethod
    def html_output(self, data: Dict[str, Any]) -> str:
        """
        Return a human-readable HTML representation of the task output.
        """
        pass

    @abstractmethod
    def logs(self) -> Dict[str, str]:
        """
        Return task logs in <timestamp, message> format.
        """
        pass

    @abstractmethod
    def dependencies(self) -> Dict[str, Any]:
        """
        Return a list of python pip dependencies required by the task.
        """
        pass

    @abstractmethod
    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Return volume mappings for container mode: {host_path: {"bind": container_path, "mode": "ro|rw"}}.
        """
        pass

    @abstractmethod
    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        """
        Return port mappings for container mode: {container_port: host_port}.
        """
        pass

    @abstractmethod
    def cpus(self) -> float:
        """
        Return the number of CPU cores required by the task.
        """
        pass

    @abstractmethod
    def memory_gb(self) -> float:
        """
        Return the amount of memory in GB required by the task.
        """
        pass

    @abstractmethod
    def requires_connection(self) -> bool:
        """
        Return true if the task requires an active internet connection.
        """
        pass

    @abstractmethod
    def max_time_expected(self) -> float | None:
        """
        Return the maximum time in seconds expected for the task to complete.
        """
        pass
