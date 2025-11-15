from task.BaseTask import BaseTask
from typing import Any, Dict, List
from whisper.utils import get_writer
import html
import json
import os
import time
import whisper

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".m4v", ".flv", ".mpg", ".mpeg", ".wmv"
}

class WhisperSubtitleTask(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            dir_path = str(carry.get("dir_path", "")).strip()
            if not dir_path:
                return {"error": "dir_path is required", "files": []}

            in_container = bool(carry.get("in_container", False))
            mapped_dir = self._get_volume(dir_path, carry) if in_container else dir_path
            if not os.path.exists(mapped_dir):
                return {"error": "directory does not exist or is not mounted", "dir_path": dir_path, "mapped_dir": mapped_dir, "files": []}

            model_name = str(carry.get("model", "base")).strip() or "base"
            language = carry.get("language")
            overwrite = bool(carry.get("overwrite", False))

            self._print(f"Scanning: {mapped_dir}")
            files = self._list_video_files(mapped_dir)
            if len(files) == 0:
                return {"dir_path": dir_path, "mapped_dir": mapped_dir, "model": model_name, "files": [], "processed": 0, "skipped": 0, "failed": 0}

            self._print(f"Filtering: " + '\n  * '.join(files))
            files_to_process, results, skipped = self._filter_processed_videos(files, overwrite)

            if len(files_to_process) == 0:
                self._print("No files to process")
                summary = {
                    "dir_path": dir_path,
                    "mapped_dir": mapped_dir,
                    "model": model_name,
                    "files": results,
                    "processed": 0,
                    "skipped": skipped,
                    "failed": 0,
                }
                return summary

            self._print(f"Loading model: {model_name}")
            model = self._get_model(model_name)

            processed = 0
            failed = 0
            for idx, video_path in enumerate(files_to_process, start=1):
                success, result_item = self._do_transcribe_video(model, video_path, idx, len(files_to_process), language)
                if success:
                    processed += 1
                else:
                    failed += 1
                results.append(result_item)

            summary = {
                "dir_path": dir_path,
                "mapped_dir": mapped_dir,
                "model": model_name,
                "language": language if language else "auto",
                "files": results,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
            }
            return summary
        except Exception as e:
            import traceback
            self._print(f"Error: {str(e)}")
            self._print(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "files": []}

    def text_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data and not data.get('files'):
            return f"error: {data['error']}"
        processed = int(data.get('processed', 0))
        skipped = int(data.get('skipped', 0))
        failed = int(data.get('failed', 0))
        total = processed + skipped + failed
        return f"videos: {total}, processed: {processed}, skipped: {skipped}, failed: {failed}"

    def html_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data and not data.get('files'):
            self._print(f"Rendering error template: {data['error']}")
            return self._render_html_from_template('template/YouTubeDownloaderError.html', {
                'error_message': html.escape(str(data['error']))
            })
        files = data.get('files', [])
        self._print(f"Rendering html_output with {len(files)} files")
        items_html_parts: List[str] = []
        for idx, item in enumerate(files, start=1):
            path = html.escape(str(item.get('path', '')))
            status_raw = str(item.get('status', 'unknown'))
            # Add emoji based on status
            if status_raw == 'success':
                status = '💾 ' + html.escape(status_raw)
            elif status_raw == 'skipped':
                status = '✅ ⏩ ' + html.escape(status_raw)
            elif status_raw == 'error':
                status = '❌ ' + html.escape(status_raw)
            else:
                status = html.escape(status_raw)
            srt = html.escape(str(item.get('srt', '')))
            err = html.escape(str(item.get('error', '')))
            lang = html.escape(str(item.get('language', '')))
            segs = html.escape(str(item.get('segments', '')))
            secs = html.escape(str(item.get('seconds', '')))
            
            # Read SRT file and parse into table format
            parsed_srt_content = ''
            srt_path_raw = item.get('srt', '')
            if srt_path_raw and os.path.exists(srt_path_raw):
                try:
                    parsed_srt_content = self._parse_srt_to_table(srt_path_raw)
                except Exception as e:
                    parsed_srt_content = html.escape(f"Error reading file: {str(e)}")
            
            # Read JSON file and render subtitle component
            subtitle_html = ''
            json_path_raw = item.get('srt', '').replace('.srt', '.json') if item.get('srt') else ''
            if json_path_raw and os.path.exists(json_path_raw):
                try:
                    with open(json_path_raw, 'r', encoding='utf-8') as f:
                        subtitle_data = json.load(f)
                        # Build rows for the subtitle table
                        rows_html = []
                        for timestamp in sorted(subtitle_data.keys(), key=int):
                            text = html.escape(subtitle_data[timestamp])
                            rows_html.append(self._render_html_from_template('template/WhisperSubtitleRow.html', {
                                'timestamp': timestamp,
                                'text': text,
                            }))
                        subtitle_html = self._render_html_from_template('template/WhisperSubtitleBox.html', {
                            'rows': '\n'.join(rows_html)
                        })
                except Exception as e:
                    subtitle_html = html.escape(f"Error reading subtitle: {str(e)}")
            
            self._print(f"  [{idx}/{len(files)}] Rendering item: {status} - {path}")
            items_html_parts.append(self._render_html_from_template('template/WhisperSubtitleItem.html', {
                'path': path,
                'status': status,
                'srt': srt,
                'language': lang,
                'segments': segs,
                'seconds': secs,
                'error': err,
                'parsed_srt_content': parsed_srt_content,
                'subtitle_box': subtitle_html,
            }))
        items_html = "\n".join(items_html_parts)
        self._print(f"Rendering summary widget")
        summary_html = self._render_html_from_template('template/WhisperSubtitleSummary.html', {
            'dir_path': html.escape(str(data.get('dir_path', ''))),
            'model': html.escape(str(data.get('model', ''))),
            'language': html.escape(str(data.get('language', 'auto'))),
            'processed': str(data.get('processed', 0)),
            'skipped': str(data.get('skipped', 0)),
            'failed': str(data.get('failed', 0)),
        })
        self._print(f"Rendering main list template with {len(items_html_parts)} items")
        return self._render_html_from_template('template/WhisperSubtitleList.html', {
            'summary': summary_html,
            'items': items_html,
        })

    def interval(self) -> int:
        return 60 * 60

    def name(self) -> str:
        return "whisper_subtitles"

    def cpus(self) -> float:
        return 10.0

    def memory_gb(self) -> float:
        return 10.0

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": [
                "openai-whisper==20231117",
            ],
            "other": [
                "ffmpeg",
            ],
        }

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        volumes: Dict[str, Dict[str, str]] = {}
        dir_path = str(params.get("dir_path", "")).strip()
        if dir_path and os.path.isabs(dir_path) and os.path.exists(dir_path):
            # mount host dir into container to read/write SRT files next to the videos
            volumes[dir_path] = {
                "bind": f"/mnt/whisper_input",
                "mode": "rw",
            }
        return volumes

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def requires_connection(self) -> bool:
        # model download on first run
        return True

    def max_time_expected(self) -> float | None:
        return None

    def _list_video_files(self, root_dir: str) -> List[str]:
        video_files: List[str] = []
        for current_root, _, files in os.walk(root_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    video_files.append(os.path.join(current_root, f))
        return sorted(video_files)

    def _derive_srt_path(self, video_path: str) -> str:
        base, _ = os.path.splitext(video_path)
        return f"{base}.srt"

    def _derive_txt_path(self, video_path: str) -> str:
        base, _ = os.path.splitext(video_path)
        return f"{base}.txt"

    def _derive_json_path(self, video_path: str) -> str:
        base, _ = os.path.splitext(video_path)
        return f"{base}.json"

    def _write_plain_transcription(self, txt_path: str, segments: List[Dict[str, Any]]) -> None:
        """Write plain text transcription to file, one segment per line."""
        with open(txt_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                text = segment.get("text", "").strip()
                if text:
                    f.write(text + "\n")

    def _write_json_transcription(self, json_path: str, segments: List[Dict[str, Any]]) -> None:
        """Write JSON transcription with timestamps as keys and text as values."""
        transcription_dict = {}
        for segment in segments:
            start_time = int(segment.get("start", 0))
            text = segment.get("text", "").strip()
            if text:
                transcription_dict[start_time] = text
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcription_dict, f, ensure_ascii=False, indent=2)

    def _parse_srt_to_table(self, srt_path: str) -> str:
        """Parse SRT file and return HTML table with timestamps and text."""
        import re
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse SRT format: index, timestamp, text, blank line
        pattern = r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            return html.escape("No subtitles found")
        
        rows_html = []
        for start_time, _, text in matches:
            # Convert timestamp from HH:MM:SS,mmm to HH:MM:SS
            timestamp = start_time.split(',')[0]
            text_clean = text.strip().replace('\n', ' ')
            rows_html.append(self._render_html_from_template('template/WhisperSubtitleTableRow.html', {
                'timestamp': html.escape(timestamp),
                'text': html.escape(text_clean),
            }))
        
        return self._render_html_from_template('template/WhisperSubtitleTable.html', {
            'rows': '\n'.join(rows_html)
        })

    def _get_model(self, model_name: str):
        return whisper.load_model(model_name)

    def _filter_processed_videos(self, files: List[str], overwrite: bool) -> tuple[List[str], List[Dict[str, Any]], int]:
        """
        Filter videos to process by excluding those with existing SRT when overwrite is False.
        Returns: (files_to_process, skipped_results, skipped_count)
        """
        files_to_process: List[str] = []
        results: List[Dict[str, Any]] = []
        skipped = 0
        for video_path in files:
            srt_path = self._derive_srt_path(video_path)
            if (not overwrite) and os.path.exists(srt_path):
                skipped += 1
                results.append({
                    "path": video_path,
                    "status": "skipped",
                    "reason": "subtitle already exists",
                    "srt": srt_path
                })
            else:
                files_to_process.append(video_path)
        return files_to_process, results, skipped

    def _do_transcribe_video(self, model: Any, video_path: str, idx: int, total: int, language: Any) -> tuple[bool, Dict[str, Any]]:
        """
        Transcribe a single video file and return (success, result_dict).
        """
        try:
            srt_path = self._derive_srt_path(video_path)
            txt_path = self._derive_txt_path(video_path)
            json_path = self._derive_json_path(video_path)
            self._print(f"[{idx}/{total}] Transcribing: {video_path}")
            t0 = time.perf_counter()
            result = model.transcribe(video_path, fp16=False, language=language, verbose=False)
            writer = get_writer("srt", os.path.dirname(video_path))
            writer(result, video_path)
            segments = result.get("segments", [])
            self._write_plain_transcription(txt_path, segments)
            self._write_json_transcription(json_path, segments)
            dt = time.perf_counter() - t0
            return True, {
                "path": video_path,
                "status": "success",
                "srt": srt_path,
                "language": result.get("language"),
                "segments": len(result.get("segments", [])),
                "seconds": round(dt, 2)
            }
        except Exception as e:
            return False, {
                "path": video_path,
                "status": "error",
                "error": str(e)
            }
