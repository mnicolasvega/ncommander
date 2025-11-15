from service.PromptService import PromptService
from task.BaseTask import BaseTask
from task.exception import LocalLLMError
from typing import Any, Dict
import html
import os
import urllib.request

class LocalLLM(BaseTask):
    DEFAULT_MODEL_URL = "https://huggingface.co/TheBloke/TinyLLaMA-1.1b-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    DEFAULT_MODEL_NAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

    def __init__(self) -> None:
        super().__init__()
        self._prompt_service = PromptService()

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = str(carry.get('prompt', '')).strip()
            if not prompt:
                raise LocalLLMError("prompt is required")
            model_name = str(carry.get('model_name', self.DEFAULT_MODEL_NAME))
            model_path = self._get_model_path(model_name)
            container_model_path = self._container_model_path(model_path, carry)
            response = self._evaluate_prompt(prompt, container_model_path, carry)
            return {"prompt": prompt, "response": response}
        except LocalLLMError as e:
            error_msg = f"LocalLLMError: {str(e)}"
            self._print(error_msg)
            return {"prompt": carry.get('prompt', ''), "error": str(e)}
        except Exception as e:
            import traceback
            error_msg = f"Unexpected error: {str(e)}"
            self._print(error_msg)
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
        models_dir = os.path.join(commander_dir, 'model')
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

    def _evaluate_prompt(self, prompt: str, llm_model_path: str, carry: Dict[str, Any]) -> str:
        """Load model and generate completion for prompt."""
        max_tokens = int(carry.get('max_tokens', 256))
        temperature = float(carry.get('temperature', 0.2))
        top_p = float(carry.get('top_p', 0.95))
        llm = self._get_model(llm_model_path, carry)
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

    def _get_model_path(self, model_name: str) -> str:
        """Get model path: use provided name, or download default if not provided."""
        if model_name:
            model_name = str(model_name).strip()
            return self._resolve_model_path(model_name)
        else:
            return self._get_or_download_default_model()

    def _get_model(self, llm_model_path: str, carry: Dict[str, Any]):
        """Load and initialize the LLM model."""
        from llama_cpp import Llama
        n_ctx = int(carry.get('n_ctx', 2048))
        n_gpu_layers = int(carry.get('n_gpu_layers', 0))
        self._print(f"Loading model: {llm_model_path}")
        llm = Llama(
            model_path = llm_model_path,
            n_ctx = n_ctx,
            n_gpu_layers = n_gpu_layers,
            verbose = True,
        )
        self._print(f"Model loaded successfully: {llm_model_path}")
        return llm

    def _container_model_path(self, model_path: str, params: Dict[str, Any]) -> str:
        if str(model_path).startswith('/ncommander/'):
            return model_path
        if 'model/' in str(model_path) or '/model/' in str(model_path):
            model_name = os.path.basename(model_path)
            return f"/ncommander/lib/model/{model_name}"
        mapping = self.volumes(params).get(model_path)
        return mapping['bind'] if mapping else model_path

    def _get_or_download_default_model(self) -> str:
        """Download default model to cache if it doesn't exist, return path."""
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'model')
        model_path = os.path.join(models_dir, self.DEFAULT_MODEL_NAME)
        if os.path.exists(model_path):
            return model_path
        os.makedirs(models_dir, exist_ok=True)
        try:
            urllib.request.urlretrieve(
                self.DEFAULT_MODEL_URL,
                model_path,
                reporthook=self._download_progress
            )
            self._print(f"Model downloaded: {model_path}")
            return model_path
        except Exception as e:
            raise LocalLLMError(f"Failed to download model: {str(e)}")

    def _download_progress(self, block_num: int, block_size: int, total_size: int) -> None:
        """Report download progress (silent)."""
        pass

    def _resolve_model_path(self, model_path: str) -> str:
        dir_task = os.path.dirname(os.path.abspath(__file__))
        dir_commander = os.path.dirname(dir_task)
        dir_models = os.path.join(dir_commander, 'model')
        model_file_path = os.path.join(dir_models, model_path)
        if os.path.exists(model_file_path):
            return model_file_path
        if not model_path.endswith('.gguf'):
            model_file_path_with_ext = os.path.join(dir_models, f"{model_path}.gguf")
            if os.path.exists(model_file_path_with_ext):
                return model_file_path_with_ext
        try:
            available = self._list_models(dir_models)
            models_str = ", ".join(available)
        except LocalLLMError:
            models_str = "(no models available)"
        raise LocalLLMError(f"Model '{model_path}' not found in model/ directory. Available models: {models_str}")

    def _list_models(self, models_dir: str) -> list[str]:
        """List available .gguf models in the models directory."""
        if not os.path.exists(models_dir):
            raise LocalLLMError(f"Models directory does not exist: {models_dir}")
        models = [f for f in os.listdir(models_dir) if f.endswith('.gguf')]
        if not models:
            raise LocalLLMError(f"No .gguf models found in {models_dir}")
        return models
