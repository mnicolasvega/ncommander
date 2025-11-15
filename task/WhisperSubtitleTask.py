from task.BaseTask import BaseTask
from typing import Any, Dict, List
import whisper
from whisper.utils import get_writer
import html
import os
import time

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

            self._print(f"Loading model: {model_name}")
            model = self._get_model(model_name)

            processed = 0
            skipped = 0
            failed = 0
            results: List[Dict[str, Any]] = []
            for idx, video_path in enumerate(files, start=1):
                try:
                    srt_path = self._derive_srt_path(video_path)
                    if (not overwrite) and os.path.exists(srt_path):
                        skipped += 1
                        results.append({
                            "path": video_path,
                            "status": "skipped",
                            "reason": "subtitle already exists",
                            "srt": srt_path
                        })
                        continue

                    self._print(f"[{idx}/{len(files)}] Transcribing: {video_path}")
                    t0 = time.perf_counter()
                    result = model.transcribe(video_path, fp16=False, language=language, verbose=False)
                    # write SRT next to the video
                    writer = get_writer("srt", os.path.dirname(video_path))
                    writer(result, video_path)
                    dt = time.perf_counter() - t0

                    processed += 1
                    results.append({
                        "path": video_path,
                        "status": "success",
                        "srt": srt_path,
                        "language": result.get("language"),
                        "segments": len(result.get("segments", [])),
                        "seconds": round(dt, 2)
                    })
                except Exception as e:
                    failed += 1
                    results.append({
                        "path": video_path,
                        "status": "error",
                        "error": str(e)
                    })

            summary = {
                "dir_path": dir_path,
                "mapped_dir": mapped_dir,
                "model": model_name,
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
            return self._render_html_from_template('template/YouTubeDownloaderError.html', {
                'error_message': html.escape(str(data['error']))
            })
        rows = []
        for item in data.get('files', []):
            path = html.escape(str(item.get('path', '')))
            status = html.escape(str(item.get('status', 'unknown')))
            srt = html.escape(str(item.get('srt', '')))
            err = html.escape(str(item.get('error', '')))
            lang = html.escape(str(item.get('language', '')))
            segs = html.escape(str(item.get('segments', '')))
            secs = html.escape(str(item.get('seconds', '')))
            rows.append(f"<tr><td>{path}</td><td>{status}</td><td>{srt}</td><td>{lang}</td><td>{segs}</td><td>{secs}</td><td>{err}</td></tr>")
        table = "\n".join([
            "<table border=1 cellpadding=4 cellspacing=0>",
            "<thead><tr><th>file</th><th>status</th><th>srt</th><th>lang</th><th>segments</th><th>seconds</th><th>error</th></tr></thead>",
            "<tbody>",
            *rows,
            "</tbody></table>"
        ])
        header = f"<p>dir: {html.escape(str(data.get('dir_path', '')))} | model: {html.escape(str(data.get('model', '')))} | processed: {data.get('processed', 0)} | skipped: {data.get('skipped', 0)} | failed: {data.get('failed', 0)}</p>"
        return header + table

    def interval(self) -> int:
        return 60 * 60

    def name(self) -> str:
        return "whisper_subtitles"

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

    def _get_model(self, model_name: str):
        return whisper.load_model(model_name)
