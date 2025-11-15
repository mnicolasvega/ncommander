from task.exception import LocalLLMError
from typing import Any, Dict
import os
import urllib.request

class ModelFactory:
    DEFAULT_MODEL_URL = "https://huggingface.co/TheBloke/TinyLLaMA-1.1b-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    DEFAULT_MODEL_NAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    MODEL_URLS = {
        "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf": "https://huggingface.co/TheBloke/TinyLLaMA-1.1b-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "mistral-7b-instruct-v0.2.Q4_K_M.gguf": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    }

    def __init__(self, print_fn=None):
        """
        Initialize ModelFactory.
        """
        self._print_fn = print_fn

    def _print(self, message: str) -> None:
        """Print message using provided print function."""
        if self._print_fn:
            self._print_fn(message)

    def get_model(self, carry: Dict[str, Any]):
        """
        Get a loaded LLM model instance based on carry parameters.
        """
        model_name = str(carry.get('model_name', self.DEFAULT_MODEL_NAME))
        model_path = self._get_model_path(model_name)
        container_model_path = self._container_model_path(model_path, carry)
        return self._load_model(container_model_path, carry)

    def _get_model_path(self, model_name: str) -> str:
        """Resolve or download the model under lib/model based on model_name."""
        if model_name:
            model_name = str(model_name).strip()
            try:
                return self._resolve_model_path(model_name)
            except LocalLLMError:
                return self._download_model_by_name(model_name)
        return self._get_or_download_default_model()

    def _load_model(self, llm_model_path: str, carry: Dict[str, Any]):
        """Load and initialize the LLM model."""
        from llama_cpp import Llama
        max_context_tokens = int(carry.get('max_context_tokens', 2048))
        n_gpu_layers = int(carry.get('n_gpu_layers', 0))
        self._print(f"Loading model: {llm_model_path}")
        try:
            llm = Llama(
                model_path = llm_model_path,
                n_ctx = max_context_tokens,
                n_gpu_layers = n_gpu_layers,
                verbose = True,
            )
            self._print(f"Model loaded successfully: {llm_model_path}")
            return llm
        except Exception as e:
            import traceback
            self._print(f"Error loading model: {e}")
            self._print(f"Traceback: {traceback.format_exc()}")
            raise LocalLLMError(f"Failed to load model: {e}")

    def _container_model_path(self, model_path: str, params: Dict[str, Any]) -> str:
        """Convert host model path to container path."""
        model_path = os.path.abspath(model_path)
        if model_path.startswith('/app/'):
            return model_path
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'lib', 'model')
        if model_path.startswith(models_dir):
            rel = os.path.relpath(model_path, models_dir)
            return f"/app/lib/model/{rel}" if rel != '.' else "/app/lib/model"
        if model_path.startswith(commander_dir):
            rel = os.path.relpath(model_path, commander_dir)
            return f"/app/{rel}"
        return model_path

    def _get_or_download_default_model(self) -> str:
        """Download default model to cache if it doesn't exist, return path."""
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'lib', 'model')
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
            return model_path
        except Exception as e:
            raise LocalLLMError(f"Failed to download model: {str(e)}")

    def _download_model_by_name(self, model_name: str) -> str:
        """Download a specific model by name."""
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'lib', 'model')
        os.makedirs(models_dir, exist_ok=True)
        target_path = os.path.join(models_dir, model_name)
        url = self.MODEL_URLS.get(model_name)
        if not url:
            available = ", ".join(sorted(self.MODEL_URLS.keys()))
            raise LocalLLMError(f"No download URL configured for '{model_name}'. Supported: {available}")
        try:
            urllib.request.urlretrieve(url, target_path, reporthook=self._download_progress)
            return target_path
        except Exception as e:
            raise LocalLLMError(f"Failed to download '{model_name}': {e}")

    def _download_progress(self, block_num: int, block_size: int, total_size: int) -> None:
        """Report download progress (silent)."""
        pass

    def _resolve_model_path(self, model_path: str) -> str:
        """Resolve model path in lib/model directory."""
        dir_task = os.path.dirname(os.path.abspath(__file__))
        dir_commander = os.path.dirname(dir_task)
        dir_models = os.path.join(dir_commander, 'lib', 'model')
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
        raise LocalLLMError(f"Model '{model_path}' not found in lib/model/ directory. Available models: {models_str}")

    def _list_models(self, models_dir: str) -> list[str]:
        """List available .gguf models in the models directory."""
        if not os.path.exists(models_dir):
            raise LocalLLMError(f"Models directory does not exist: {models_dir}")
        models = [f for f in os.listdir(models_dir) if f.endswith('.gguf')]
        if not models:
            raise LocalLLMError(f"No .gguf models found in {models_dir}")
        return models
