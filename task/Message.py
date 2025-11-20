from task.BaseTask import BaseTask
from typing import Any, Dict
import random

MESSAGES = [
    "Hello world!",
    "Hola mundo!",
    "Hiii"
]

"""
Displays a random message from a list of messages.
"""
class Message(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        message = random.choice(MESSAGES)
        self._print(f"Message Task: '{message}'")
        return {
            "message": message
        }

    def text_output(self, data: Dict[str, Any]) -> str:
        return data['message']

    def html_output(self, data: Dict[str, Any]) -> str:
        html = self._render_html_from_template('template/Message.html', {'message': data['message']})
        return html

    def interval(self) -> int:
        return 14

    def name(self) -> str:
        return "random_messager"
