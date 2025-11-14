from task.BaseTask import BaseTask
from typing import Any, Dict
import html
import json
import os

class TaskData(BaseTask):
    """Task that reads and displays JSON task output files from the output/ directory."""

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        """Read all .json files from output/ directory and return their content."""
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        output_dir = os.path.join(commander_dir, 'tmp', 'output')
        task_data_list = []
        if not os.path.exists(output_dir):
            return {"tasks": task_data_list}
        try:
            json_files = self._get_json_files(output_dir)
            for json_file in json_files:
                task_name = os.path.splitext(json_file)[0]
                try:
                    content = self._get_task_data(task_name)
                    task_data_list.append({
                        'file_name': json_file,
                        'task_name': task_name,
                        'content': content
                    })
                except Exception as e:
                    task_data_list.append({
                        'file_name': json_file,
                        'task_name': task_name,
                        'error': str(e)
                    })
        except Exception as e:
            return {"tasks": [], "error": str(e)}
        return {"tasks": task_data_list}

    def text_output(self, data: Dict[str, Any]) -> str:
        """Generate text output showing task data summary."""
        tasks = data.get('tasks', [])
        if not tasks:
            return "No task data found"
        lines = []
        for task_data in tasks:
            task_name = task_data.get('task_name', 'unknown')
            if 'error' in task_data:
                lines.append(f"{task_name}: error - {task_data['error']}")
            else:
                content = task_data.get('content', {})
                time_elapsed = content.get('time_elapsed_ms', 0)
                lines.append(f"{task_name}: {time_elapsed:.2f}ms")
        return ' | '.join(lines)

    def html_output(self, data: Dict[str, Any]) -> str:
        """Generate HTML output displaying task data in formatted cards."""
        tasks = data.get('tasks', [])
        if not tasks:
            return "<p>No task data found</p>"
        task_cards = [self._render_task_card(task_data) for task_data in tasks]
        return '\n'.join(task_cards)

    def _render_task_card(self, task_data: Dict[str, Any]) -> str:
        """Render a single task card as HTML."""
        task_name = task_data.get('task_name', 'unknown')
        file_name = task_data.get('file_name', '')
        if 'error' in task_data:
            return self._render_html_from_template('template/TaskDataError.html', {
                'task_name': html.escape(task_name),
                'file_name': html.escape(file_name),
                'error_message': html.escape(task_data['error'])
            })
        else:
            content = task_data.get('content', {})
            time_elapsed = content.get('time_elapsed_ms', 0)
            content_str = json.dumps(content, indent=2, ensure_ascii=False)
            return self._render_html_from_template('template/TaskDataSuccess.html', {
                'task_name': html.escape(task_name),
                'file_name': html.escape(file_name),
                'time_elapsed': f"{time_elapsed:.2f}",
                'content_str': html.escape(content_str)
            })

    def name(self) -> str:
        return "task_data"

    def interval(self) -> int:
        return 5

    def _get_json_files(self, output_dir: str) -> list:
        """Get sorted list of JSON files from the output directory."""
        files = os.listdir(output_dir)
        return sorted([f for f in files if f.endswith('.json')])
