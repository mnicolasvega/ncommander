from service.ModelFactory import ModelFactory
from service.PromptService import PromptService
from task.BaseTask import BaseTask
from task.exception import LocalLLMError
from typing import Any, Dict, List
import html
import json
import os

class LlamaVideoSummary(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self._prompt_service = PromptService()
        self._model_factory = ModelFactory(print_fn=self._print)

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            dir_path = carry.get('dir_path', '').strip()
            if not dir_path:
                raise LocalLLMError("dir_path is required")
            if not os.path.isabs(dir_path):
                raise LocalLLMError("dir_path must be an absolute path")
            if not os.path.exists(dir_path):
                raise LocalLLMError(f"Directory does not exist: {dir_path}")
            # Find all TXT files for processing
            txt_files = self._find_txt_files(dir_path)
            if not txt_files:
                self._print("No TXT files found")
                return {"processed": 0, "skipped": 0, "failed": 0, "results": []}
            llm = self._model_factory.get_model(carry)
            processed = 0
            skipped = 0
            failed = 0
            results = []
            for txt_file in txt_files:
                try:
                    parsed_txt_path = self._derive_parsed_txt_path(txt_file)
                    self._print(f"Parsed TXT path: {parsed_txt_path}")
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        original_txt = f.read()
                    video_title = os.path.splitext(os.path.basename(txt_file))[0]
                    self._print(f"Processing {os.path.basename(txt_file)}...")
                    corrected_txt = self._correct_txt_with_llm(original_txt, video_title, llm, carry)
                    self._save_txt(parsed_txt_path, corrected_txt)
                    processed += 1
                    results.append({
                        "file": txt_file,
                        "status": "success",
                        "parsed_txt_path": parsed_txt_path
                    })
                    self._print(f"✓ Processed {os.path.basename(txt_file)}")
                except Exception as e:
                    failed += 1
                    error_msg = str(e)
                    self._print(f"✗ Failed {os.path.basename(txt_file)}: {error_msg}")
                    results.append({
                        "file": txt_file,
                        "status": "failed",
                        "error": error_msg
                    })
            return {
                "dir_path": dir_path,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "results": results
            }
            
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
        processed = data.get('processed', 0)
        skipped = data.get('skipped', 0)
        failed = data.get('failed', 0)
        return f"Video Summary Correction: {processed} processed, {skipped} skipped, {failed} failed"

    def html_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return self._render_html_from_template('template/LlamaVideoSummaryError.html', {
                'error_message': html.escape(str(data['error']))
            })
        results = data.get('results', [])
        items_html = []
        for result in results:
            file_name = os.path.basename(result.get('file', ''))
            status = result.get('status', 'unknown')
            parsed_txt_path = result.get('parsed_txt_path', '')
            # Read parsed TXT content if available
            parsed_txt_content = ''
            if status == 'success' and parsed_txt_path and os.path.exists(parsed_txt_path):
                try:
                    with open(parsed_txt_path, 'r', encoding='utf-8') as f:
                        parsed_txt_content = f.read()
                except Exception:
                    parsed_txt_content = ''
            item_html = self._render_html_from_template('template/LlamaVideoSummaryItem.html', {
                'file_name': html.escape(file_name),
                'status': html.escape(status),
                'parsed_txt_path': html.escape(parsed_txt_path),
                'parsed_txt_content': html.escape(parsed_txt_content),
                'error': html.escape(result.get('error', ''))
            })
            items_html.append(item_html)
        return self._render_html_from_template('template/LlamaVideoSummary.html', {
            'dir_path': html.escape(data.get('dir_path', '')),
            'processed': data.get('processed', 0),
            'skipped': data.get('skipped', 0),
            'failed': data.get('failed', 0),
            'items': '\n'.join(items_html)
        })

    def name(self) -> str:
        return "llama_video_summary"

    def interval(self) -> int:
        return 60 * 60

    def cpus(self) -> float:
        return 20.0

    def memory_gb(self) -> float:
        return 20.0

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
        dir_path = str(params.get("dir_path", "")).strip()
        if dir_path and os.path.isabs(dir_path) and os.path.exists(dir_path):
            volumes[dir_path] = {
                "bind": "/mnt/video_input",
                "mode": "rw",
            }
        return volumes

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def requires_connection(self) -> bool:
        return True

    def max_time_expected(self) -> float | None:
        return None

    def _find_txt_files(self, root_dir: str) -> List[str]:
        """Find all TXT files for processing."""
        txt_files = []
        for current_root, _, files in os.walk(root_dir):
            for f in files:
                if f.endswith('.txt') and not f.endswith('.parsed.txt'):
                    txt_path = os.path.join(current_root, f)
                    txt_files.append(txt_path)
        return sorted(txt_files)

    def _derive_parsed_txt_path(self, txt_path: str) -> str:
        """Derive parsed TXT path from TXT path."""
        base, _ = os.path.splitext(txt_path)
        return f"{base}.parsed.txt"

    def _correct_txt_with_llm(self, txt_content: str, context: str, llm, carry: Dict[str, Any]) -> str:
        """Use LLM to correct text content."""
        self._print(f"Input TXT has {len(txt_content)} chars")
        task_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(task_dir, 'video_summary_correction.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        prompt = prompt_template.format(context=context, txt_content=txt_content)
        self._print(f"Prompt: \"{prompt}\"")
        llm_response = self._get_llm_response(prompt, llm, carry)
        self._print(f"LLM Resposne: \"{llm_response}\"")
        return llm_response

    def _get_llm_response(self, prompt: str, llm, carry: Dict[str, Any]) -> str:
        self._print(f"Prompt length: {len(prompt)} chars")
        max_tokens = int(carry.get('max_tokens', 2048))
        temperature = float(carry.get('temperature', 0.2))
        top_p = float(carry.get('top_p', 0.95))
        self._print(f"LLM params: max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}")
        self._print(f"Sending prompt directly (length: {len(prompt)} chars)")
        result = llm.create_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        response_text = result.get('choices', [{}])[0].get('text', '').strip()
        self._print(f"LLM Response length: {len(response_text)} chars")
        self._print(f"LLM Response preview (first 500 chars): {response_text[:500]}")
        return response_text

    def _save_txt(self, txt_path: str, content: str) -> None:
        """Save corrected TXT content to file."""
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)
