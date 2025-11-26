import json
import os
from typing import List


class QueueService:
    """Service for managing persistent queue operations."""
    
    @staticmethod
    def get_queue_file_path(task_name: str, outdir: str) -> str:
        """
        Get the path to the queue.txt file for a given task.
        
        Args:
            task_name: Name of the task using the queue
            outdir: Output directory from carry (e.g., "/app/tmp")
        
        Returns:
            Path to the queue file
        """
        commander_dir = os.path.dirname(outdir)
        queue_dir = os.path.join(commander_dir, "var", task_name)
        os.makedirs(queue_dir, exist_ok=True)
        return os.path.join(queue_dir, "queue.txt")
    
    @staticmethod
    def read_queue(queue_file: str) -> List[str]:
        """
        Read the queue from queue.txt. Returns empty list if file doesn't exist.
        The last line contains the current queue as a JSON array.
        
        Args:
            queue_file: Path to the queue file
        
        Returns:
            List of items in the queue
        """
        if not os.path.exists(queue_file):
            return []
        try:
            with open(queue_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                # The last line contains the current queue as a JSON array
                lines = content.split('\n')
                if lines:
                    return json.loads(lines[-1])
                return []
        except Exception:
            return []
    
    @staticmethod
    def write_queue(queue_file: str, queue: List[str]) -> None:
        """
        Write the queue to queue.txt as a JSON array on a new line.
        
        Args:
            queue_file: Path to the queue file
            queue: List of items to write to the queue
        """
        try:
            with open(queue_file, 'a') as f:
                f.write(json.dumps(queue) + '\n')
        except Exception:
            pass
    
    @staticmethod
    def pop_first(queue_file: str) -> tuple[List[str], str | None]:
        """
        Remove and return the first item from the queue, updating the file.
        
        Args:
            queue_file: Path to the queue file
        
        Returns:
            Tuple of (updated queue, popped item or None if queue was empty)
        """
        queue = QueueService.read_queue(queue_file)
        if not queue:
            return ([], None)
        
        first_item = queue[0]
        remaining_queue = queue[1:]
        QueueService.write_queue(queue_file, remaining_queue)
        return (remaining_queue, first_item)
    
    @staticmethod
    def initialize_queue(queue_file: str, items: List[str]) -> None:
        """
        Initialize the queue with items if it doesn't already exist.
        
        Args:
            queue_file: Path to the queue file
            items: List of items to initialize the queue with
        """
        QueueService.write_queue(queue_file, items)
    
    @staticmethod
    def get_queue_size(queue_file: str) -> int:
        """
        Get the current size of the queue.
        
        Args:
            queue_file: Path to the queue file
        
        Returns:
            Number of items in the queue
        """
        return len(QueueService.read_queue(queue_file))
