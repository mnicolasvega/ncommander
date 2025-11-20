from task.BaseTask import BaseTask
from typing import Any, Dict
import os

"""
Creates a test file in the container's working directory to verify directory structure.
"""
class DirManager(BaseTask):
    TEST_FILE_PATH = "test.txt"
    TEST_FILE_CONTENT = "This file was created by DirManager task"

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        self._create_test_file()
        abs_path = os.path.abspath(self.TEST_FILE_PATH)
        self._print(f"Created test file at: {abs_path}")
        return {
            "file_path": abs_path,
            "content": self.TEST_FILE_CONTENT,
            "success": True
        }

    def text_output(self, data: Dict[str, Any]) -> str:
        return f"File created at: {data['file_path']}"

    def html_output(self, data: Dict[str, Any]) -> str:
        html = self._render_html_from_template('template/DirManager.html', {
            'file_path': data['file_path'],
            'content': data['content']
        })
        return html

    def interval(self) -> int:
        return 60

    def name(self) -> str:
        return "dir_manager"

    def _create_test_file(self) -> None:
        with open(self.TEST_FILE_PATH, 'w') as f:
            f.write(self.TEST_FILE_CONTENT)
