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
    
    @staticmethod
    def merge_and_filter_queue(queue_file: str, new_items: List[str], filter_func=None) -> List[str]:
        """
        Merge existing queue with new items, giving priority to existing queue items.
        Optionally filter out items that should be skipped.
        """
        existing_queue = QueueService.read_queue(queue_file)
        existing_set = set(existing_queue)
        merged = list(existing_queue)
        for item in new_items:
            if item not in existing_set:
                merged.append(item)
                existing_set.add(item)
        if filter_func:
            merged = [item for item in merged if filter_func(item)]
        QueueService.write_queue(queue_file, merged)
        return merged
    
    @staticmethod
    def build_queue(
        queue_file: str,
        collect_func,
        filter_func=None,
        print_func=None
    ) -> tuple[List[str], dict]:
        """
        Complete queue building workflow: collect items, merge with existing queue, and filter.
        
        Args:
            queue_file: Path to the queue file
            collect_func: Function that returns tuple of (collected_items: List[str], skips: List[dict])
            filter_func: Optional function that takes an item and returns True if it should be kept
            print_func: Optional function for logging messages
        
        Returns:
            Tuple of (final_queue: List[str], collection_info: dict with 'files' and 'skips')
        """
        # Collect items using provided function
        collected_items, skips = collect_func()
        
        if print_func:
            print_func(f"collection: items={len(collected_items)}, skips={len(skips)}")
        
        if not collected_items:
            return ([], {"collected": 0, "skips": len(skips), "skip_details": skips})
        
        # Merge existing queue with new items and filter
        final_queue = QueueService.merge_and_filter_queue(queue_file, collected_items, filter_func)
        
        if print_func:
            print_func(f"Queue merged and filtered: {len(final_queue)} items remaining")
        
        return (final_queue, {
            "collected": len(collected_items),
            "skips": len(skips),
            "skip_details": skips,
            "final_queue_size": len(final_queue)
        })
