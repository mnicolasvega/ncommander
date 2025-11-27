from typing import Any, Dict, List
import os
import time

FILE_NAME_TEMPLATE = '../task/template/template.html'

class Builder:
    def __init__(self):
        self._items: Dict[str, Dict[str, Any]] = {}
        self._template_cache: Dict[str, str] = {}

    def add(self, task: str, data: dict, task_obj=None) -> None:
        self._items[task] = {'data': data, 'task_obj': task_obj}

    def build(self) -> str:
        html = self.__load_html_template()
        html_items = '\n'.join(self.__build_items(self._items))
        return html.replace('{{items}}', html_items)

    def save(self, output_path: str, html_content: str) -> None:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def __build_items(self, items: Dict[str, Dict[str, Any]]) -> List[str]:
        html = []
        for task_name, item in items.items():
            data = item.get('data', {})
            task_obj = item.get('task_obj')
            output_data = data.get('data', {})
            output_html = data.get('html', '')
            is_previous = data.get('is_previous', False)
            execution_time = self.__get_formatted_execution_time(output_data)
            finish_time = self.__get_formatted_finish_time(output_data)
            template_name = 'template/BaseTaskTemplate.html'
            if task_obj:
                try:
                    template_name = task_obj.html_template()
                except:
                    pass
            elif 'html_template' in output_data:
                template_name = output_data['html_template']
            html_task_template = self.__load_template(template_name)
            html_task = html_task_template[:] \
                .replace('{{task_name}}', task_name) \
                .replace('{{execution_time}}', execution_time) \
                .replace('{{finished_time}}', finish_time) \
                .replace('{{output}}', output_html)
            for key, value in output_data.items():
                placeholder = f'{{{{{key}}}}}'
                if placeholder in html_task:
                    html_task = html_task.replace(placeholder, str(value))
            html.append('<tr><td class="item-wrapper">')
            html.append(html_task)
            html.append('</td></tr>')
        return html

    def __load_html_template(self) -> str:
        template_path = os.path.join(os.path.dirname(__file__), FILE_NAME_TEMPLATE)
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def __load_template(self, template_name: str) -> str:
        if template_name not in self._template_cache:
            template_path = os.path.join(os.path.dirname(__file__), '..', 'task', template_name)
            with open(template_path, 'r', encoding='utf-8') as f:
                self._template_cache[template_name] = f.read()
        return self._template_cache[template_name]

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
