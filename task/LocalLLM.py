from task.BaseTask import BaseTask
from typing import Any, Dict
import html
import json
import os
import urllib.request

class LocalLLM(BaseTask):
    DEFAULT_MODEL_URL = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    DEFAULT_MODEL_NAME = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        self._print("LocalLLM task started")
        prompt = str(carry.get('prompt', '')).strip()
        if not prompt:
            return {"error": "prompt is required"}
        
        model_path = str(carry.get('model_path', '')).strip()
        self._print(f"Input model_path: '{model_path}'")
        
        if not model_path:
            self._print("No model_path provided, using default model")
            model_path = self._get_or_download_default_model()
            if model_path.startswith('ERROR:'):
                return {"prompt": prompt, "error": model_path}
        else:
            # Resolve model name to model/ directory
            self._print(f"Resolving model name: '{model_path}'")
            model_path = self._resolve_model_path(model_path)
            if model_path.startswith('ERROR:'):
                return {"prompt": prompt, "error": model_path}
        
        self._print(f"Resolved model_path: {model_path}")
        container_model_path = self._container_model_path(model_path, carry)
        self._print(f"Container model path: {container_model_path}")
        
        try:
            from llama_cpp import Llama
        except Exception as e:
            return {"prompt": prompt, "error": f"failed to import llama_cpp: {e}"}
        
        try:
            n_ctx = int(carry.get('n_ctx', 2048))
            n_gpu_layers = int(carry.get('n_gpu_layers', 0))
            max_tokens = int(carry.get('max_tokens', 256))
            temperature = float(carry.get('temperature', 0.2))
            top_p = float(carry.get('top_p', 0.95))
            
            self._print(f"Loading model with n_ctx={n_ctx}, n_gpu_layers={n_gpu_layers}")
            llm = Llama(
                model_path=container_model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
            
            self._print(f"Generating completion (max_tokens={max_tokens}, temp={temperature})")
            result = llm.create_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            text = result.get('choices', [{}])[0].get('text', '').strip()
            self._print(f"Generation complete, response length: {len(text)} chars")
            return {"prompt": prompt, "response": text}
        except Exception as e:
            self._print(f"Error during model execution: {e}")
            return {"prompt": prompt, "error": str(e)}

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
                "bind": "/app/model",
                "mode": "rw",
            }
        }
        model_path = params.get('model_path', '')
        if model_path and not str(model_path).startswith('/app/'):
            if 'model/' not in str(model_path) and '/model/' not in str(model_path):
                # Only mount if model_path is an absolute path
                # Docker requires absolute paths for host volume mounts
                if os.path.isabs(model_path):
                    container_path = f"/mnt/llm/{os.path.basename(model_path)}"
                    volumes[model_path] = {
                        "bind": container_path,
                        "mode": "ro",
                    }
        return volumes

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def requires_connection(self) -> bool:
        return True

    def max_time_expected(self) -> float | None:
        return None

    def _container_model_path(self, model_path: str, params: Dict[str, Any]) -> str:
        if str(model_path).startswith('/app/'):
            return model_path
        if 'model/' in str(model_path) or '/model/' in str(model_path):
            model_name = os.path.basename(model_path)
            return f"/app/model/{model_name}"
        mapping = self.volumes(params).get(model_path)
        return mapping['bind'] if mapping else model_path

    def _get_or_download_default_model(self) -> str:
        """Download default model to cache if it doesn't exist, return path."""
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'model')
        model_path = os.path.join(models_dir, self.DEFAULT_MODEL_NAME)
        if os.path.exists(model_path):
            self._print(f"Using cached model: {model_path}")
            return model_path
        os.makedirs(models_dir, exist_ok=True)
        self._print(f"Downloading default model ({self.DEFAULT_MODEL_NAME})...")
        self._print(f"This may take several minutes (~4.4GB)")
        try:
            urllib.request.urlretrieve(
                self.DEFAULT_MODEL_URL,
                model_path,
                reporthook=self._download_progress
            )
            self._print(f"Model downloaded successfully to: {model_path}")
            return model_path
        except Exception as e:
            return f"ERROR: Failed to download model: {str(e)}"

    def _download_progress(self, block_num: int, block_size: int, total_size: int) -> None:
        """Report download progress."""
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, (downloaded / total_size) * 100)
            if block_num % 100 == 0:
                self._print(f"Download progress: {percent:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")

    def _resolve_model_path(self, model_path: str) -> str:
        """Resolve model path. If not absolute, treat as model name in model/ dir."""
        # If already absolute path, return as-is if it exists
        if os.path.isabs(model_path):
            if os.path.exists(model_path):
                return model_path
            return f"ERROR: Model file not found at {model_path}"
        
        # Treat as model name and look in model/ directory
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        models_dir = os.path.join(commander_dir, 'model')
        
        # Try the name as-is first
        model_file_path = os.path.join(models_dir, model_path)
        if os.path.exists(model_file_path):
            self._print(f"Found model in model/ directory: {model_path}")
            return model_file_path
        
        # Try adding .gguf extension if not present
        if not model_path.endswith('.gguf'):
            model_file_path_with_ext = os.path.join(models_dir, f"{model_path}.gguf")
            if os.path.exists(model_file_path_with_ext):
                self._print(f"Found model in model/ directory: {model_path}.gguf")
                return model_file_path_with_ext
        
        return f"ERROR: Model '{model_path}' not found in model/ directory. Available models: {self._list_models(models_dir)}"
    
    def _list_models(self, models_dir: str) -> str:
        """List available models in the models directory."""
        if not os.path.exists(models_dir):
            return "(directory does not exist)"
        models = [f for f in os.listdir(models_dir) if f.endswith('.gguf')]
        if not models:
            return "(no .gguf files found)"
        return ", ".join(models)
