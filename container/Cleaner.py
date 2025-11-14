from docker.models.containers import Container
from typing import Dict, List
import docker


class Cleaner:
    def cleanup_orphaned_containers(self) -> List[str]:
        """Cleanup any orphaned task-commander containers from previous runs.
        
        Returns:
            List of container IDs that were successfully cleaned up.
            
        Raises:
            Exception: If Docker operations fail.
        """
        client = docker.from_env()
        all_containers = client.containers.list(all=True)
        orphaned = []
        for c in all_containers:
            try:
                if c.image.tags and any(tag.startswith('task-commander:') for tag in c.image.tags):
                    orphaned.append(c)
            except Exception:
                pass
        cleaned_ids = []
        for container in orphaned:
            try:
                container.stop(timeout=5)
                container.remove()
                cleaned_ids.append(container.short_id)
            except Exception:
                pass
        return cleaned_ids

    def cleanup_containers(self, running_containers: Dict[str, Container]) -> List[str]:
        """Stop and remove all running containers.
        
        Returns:
            List of container IDs that were successfully cleaned up.
            
        Raises:
            Exception: If Docker operations fail.
        """
        if not running_containers:
            return []
        cleaned_ids = []
        for task_name, container in list(running_containers.items()):
            try:
                container.stop(timeout=5)
                container.remove()
                cleaned_ids.append(container.short_id)
            except Exception:
                pass
        running_containers.clear()
        return cleaned_ids
