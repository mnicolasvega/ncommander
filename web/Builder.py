from typing import Any, Dict, List
import os
import time

FILE_NAME_TEMPLATE = '../task/template/template.html'
FILE_NAME_TASK_TEMPLATE = '../task/template/task_template.html'

class Builder:
    def __init__(self):
        self._items: Dict[str, Dict[str, Any]] = {}

    def add(self, task: str, data: dict) -> None:
        self._items[task] = data

    def build(self) -> str:
        html = self.__load_html_template()
        html_items = '\n'.join(self.__build_items(self._items))
        return html.replace('{{items}}', html_items)

    def save(self, output_path: str, html_content: str) -> None:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def __build_items(self, items: Dict[str, Dict[str, Any]]) -> List[str]:
        html = []
        html_task_template = self.__load_task_template()
        for task, data in items.items():
            output_data = data.get('data', {})
            output_html = data.get('html', '')
            is_previous = data.get('is_previous', False)
            execution_time = self.__get_formatted_execution_time(output_data)
            finish_time = self.__get_formatted_finish_time(output_data)
            html_task = html_task_template[:] \
                .replace('{{task_name}}', task) \
                .replace('{{execution_time}}', execution_time) \
                .replace('{{finished_time}}', finish_time) \
                .replace('{{output}}', output_html)
            html.append('<tr><td class="item-wrapper">')
            html.append(html_task)
            html.append('</td></tr>')
        return html

    def __load_html_template(self) -> str:
        template_path = os.path.join(os.path.dirname(__file__), FILE_NAME_TEMPLATE)
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def __load_task_template(self) -> str:
        template_path = os.path.join(os.path.dirname(__file__), FILE_NAME_TASK_TEMPLATE)
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def __get_formatted_execution_time(self, data: Dict[str, Any]) -> str:
        time_elapsed_ms = float(data.get('time_elapsed_ms', 0))
        if time_elapsed_ms < 1000 * 10:
            return f"{time_elapsed_ms:.1f} ms"
        elif time_elapsed_ms < 1000 * 60:
            seconds = time_elapsed_ms / 1000
            return f"{seconds:.1f} sec"
        else:
            minutes = time_elapsed_ms / (1000 * 60)
            return f"{minutes:.1f} min"

    def __get_formatted_finish_time(self, data: Dict[str, Any]) -> str:
        finish_time_ms = float(data.get('time_finish_ms', 0))
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(finish_time_ms / 1000))
