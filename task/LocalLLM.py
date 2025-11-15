from service.ModelFactory import ModelFactory
from service.PromptService import PromptService
from task.BaseTask import BaseTask
from task.exception import LocalLLMError
from typing import Any, Dict
import html
import os

class LocalLLM(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self._prompt_service = PromptService()
        self._model_factory = ModelFactory(print_fn=self._print)

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = str(carry.get('prompt', '')).strip()
            if not prompt:
                raise LocalLLMError("prompt is required")
            llm = self._model_factory.get_model(carry)
            response = self._evaluate_prompt(prompt, llm, carry)
            return {"prompt": prompt, "response": response}
        except LocalLLMError as e:
            self._print(f"Error: {str(e)}")
            return {"prompt": carry.get('prompt', ''), "error": str(e)}
        except Exception as e:
            import traceback
            self._print(f"Error: {str(e)}")
            self._print(f"Traceback: {traceback.format_exc()}")
            return {"prompt": carry.get('prompt', ''), "error": str(e)}

    def text_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return f"error: {data['error']}"
        response = data.get('response', '')
        return response[:2000]

    def html_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return self._render_html_from_template('template/LocalLLMError.html', {
                'error_message': html.escape(str(data['error']))
            })
        prompt = html.escape(str(data.get('prompt', '')))
        response = html.escape(str(data.get('response', '')))
        return self._render_html_from_template('template/LocalLLM.html', {
            'prompt': prompt,
            'response': response
        })

    def name(self) -> str:
        return "local_llm"

    def interval(self) -> int:
        return 300

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": [
                "llama-cpp-python==0.3.2",
            ],
            "other": [
                "cmake",
                "build-essential",
                "libopenblas-dev",
            ],
        }

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'lib', 'model')
        volumes = {
            models_dir: {
                "bind": "/app/lib/model",
                "mode": "rw",
            }
        }
        return volumes

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def requires_connection(self) -> bool:
        return True

    def max_time_expected(self) -> float | None:
        return None

    def _evaluate_prompt(self, prompt: str, llm, carry: Dict[str, Any]) -> str:
        """Generate completion for prompt using loaded model."""
        max_tokens = int(carry.get('max_tokens', 256))
        temperature = float(carry.get('temperature', 0.2))
        top_p = float(carry.get('top_p', 0.95))
        formatted_prompt = self._prompt_service.get_formatted_prompt(prompt)
        self._print(f"Executing: {prompt}")
        result = llm.create_completion(
            prompt = formatted_prompt,
            max_tokens = max_tokens,
            temperature = temperature,
            top_p = top_p,
        )
        text = result.get('choices', [{}])[0].get('text', '').strip()
        self._print(f"Answer: {text}")
        return text
