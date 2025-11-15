from service.ModelFactory import ModelFactory
from service.PromptService import PromptService
from task.BaseTask import BaseTask
from task.exception import LocalLLMError
from typing import Any, Dict, List
import html
import os

class LlamaLLM(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self._prompt_service = PromptService()
        self._model_factory = ModelFactory(print_fn=self._print)

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompts = carry.get('prompts', [])
            if not prompts:
                raise LocalLLMError("prompts list is required")
            if not isinstance(prompts, list):
                raise LocalLLMError("prompts must be a list of strings")
            
            llm = self._model_factory.get_model(carry)
            results = []
            
            for prompt in prompts:
                prompt_str = str(prompt).strip()
                if not prompt_str:
                    continue
                response = self._evaluate_prompt(prompt_str, llm, carry)
                results.append({"prompt": prompt_str, "response": response})
            
            return {"results": results}
        except LocalLLMError as e:
            self._print(f"Error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            import traceback
            self._print(f"Error: {str(e)}")
            self._print(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e)}

    def text_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return f"error: {data['error']}"
        results = data.get('results', [])
        output_lines = []
        for result in results:
            prompt = result.get('prompt', '')
            response = result.get('response', '')
            output_lines.append(f"Q: {prompt}")
            output_lines.append(f"A: {response[:500]}")
            output_lines.append("")
        return "\n".join(output_lines)[:2000]

    def html_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return self._render_html_from_template('template/LlamaLLMError.html', {
                'error_message': html.escape(str(data['error']))
            })
        results = data.get('results', [])
        composed_html = []
        for result in results:
            prompt = html.escape(str(result.get('prompt', '')))
            response = html.escape(str(result.get('response', '')))
            prompt_html = self._render_html_from_template('template/LlamaLLMPrompt.html', {
                'prompt': prompt,
                'response': response
            })
            composed_html.append(prompt_html)
        content = '\n'.join(composed_html)
        return self._render_html_from_template('template/LlamaLLM.html', {
            'content': content
        })

    def name(self) -> str:
        return "llama_llm"

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
