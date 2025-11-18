import json
import os
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
from task.BaseTask import BaseTask
from typing import Any, Dict, List, Tuple

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".m4v", ".flv", ".mpg", ".mpeg", ".wmv"
}

class SceneChangeDetectorTask(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            video_paths_raw = carry.get("video_paths", [])
            if not isinstance(video_paths_raw, list) or len(video_paths_raw) == 0:
                return {"error": "video_paths is required and must be a non-empty list", "files": []}

            in_container = bool(carry.get("in_container", False))
            threshold = float(carry.get("threshold", 27.0))
            recursive = bool(carry.get("recursive", True))
            inputs: List[str] = [str(p).strip() for p in video_paths_raw if str(p).strip()]
            results: List[Dict[str, Any]] = []
            processed = 0
            skipped = 0
            failed = 0

            files, expand_skips = self._collect_video_files(inputs, recursive, in_container, carry)
            results.extend(expand_skips)
            skipped += len(expand_skips)

            for idx, host_path in enumerate(files, start=1):
                try:
                    if not os.path.isabs(host_path):
                        skipped += 1
                        results.append({
                            "path": host_path,
                            "status": "skipped",
                            "reason": "path must be absolute"
                        })
                        continue

                    mapped_path = self._map_host_to_container_file(host_path, carry) if in_container else host_path
                    if not os.path.exists(mapped_path):
                        skipped += 1
                        results.append({
                            "path": host_path,
                            "status": "skipped",
                            "reason": "file does not exist or is not mounted"
                        })
                        continue

                    self._print(f"[{idx}/{len(files)}] Detecting scenes: {host_path}")
                    scene_list = self._detect_scenes(mapped_path, threshold)
                    scenes_serialized = self._serialize_scenes(scene_list)

                    json_host_path = self._derive_scenes_json_path(host_path)
                    json_container_path = self._map_host_to_container_file(json_host_path, carry) if in_container else json_host_path
                    self._write_json(json_container_path, {
                        "path": mapped_path,
                        "threshold": threshold,
                        "detector": "ContentDetector",
                        "total_scenes": len(scenes_serialized),
                        "scenes": scenes_serialized,
                    })

                    processed += 1
                    results.append({
                        "path": host_path,
                        "status": "success",
                        "scenes_json": json_host_path,
                        "scenes": len(scenes_serialized)
                    })
                except Exception as e:
                    failed += 1
                    results.append({
                        "path": host_path,
                        "status": "error",
                        "error": str(e)
                    })

            summary = {
                "files": results,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "threshold": threshold,
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
        return json.dumps(data)

    def interval(self) -> int:
        return 60 * 60

    def name(self) -> str:
        return "scene_change_detector"

    def cpus(self) -> float:
        return 2.0

    def memory_gb(self) -> float:
        return 2.0

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": [
                "scenedetect==0.6.4",
                "opencv-python-headless==4.9.0.80",
            ],
            "other": [
                "ffmpeg",
            ],
        }

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        volumes: Dict[str, Dict[str, str]] = {}
        video_paths = params.get("video_paths", []) or []
        mount_points: List[str] = []
        for p in video_paths:
            sp = str(p).strip()
            if not sp or not os.path.isabs(sp):
                continue
            if os.path.isdir(sp):
                if os.path.exists(sp):
                    mount_points.append(sp)
            else:
                parent = os.path.dirname(sp)
                if os.path.exists(parent):
                    mount_points.append(parent)
        for i, d in enumerate(sorted(set(mount_points))):
            volumes[d] = {
                "bind": f"/mnt/scene_input_{i}",
                "mode": "rw",
            }
        return volumes

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def requires_connection(self) -> bool:
        return False

    def max_time_expected(self) -> float | None:
        return None

    def _map_host_to_container_file(self, host_file: str, params: Dict[str, Any]) -> str:
        vids = self.volumes(params)
        for host_dir, data in vids.items():
            if host_file == host_dir or host_file.startswith(host_dir + os.sep):
                rel = os.path.relpath(host_file, host_dir)
                return os.path.join(data["bind"], rel)
        return host_file

    def _map_container_to_host_file(self, container_path: str, params: Dict[str, Any]) -> str:
        vids = self.volumes(params)
        for host_dir, data in vids.items():
            bind = data["bind"]
            if container_path == bind or container_path.startswith(bind + os.sep):
                rel = os.path.relpath(container_path, bind)
                return os.path.join(host_dir, rel)
        return container_path

    def _collect_video_files(self, inputs: List[str], recursive: bool, in_container: bool, params: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
        found: List[str] = []
        skips: List[Dict[str, Any]] = []
        seen = set()
        for raw in inputs:
            if not os.path.isabs(raw):
                skips.append({"path": raw, "status": "skipped", "reason": "path must be absolute"})
                continue
            mapped = self._map_host_to_container_file(raw, params) if in_container else raw
            if not os.path.exists(mapped):
                skips.append({"path": raw, "status": "skipped", "reason": "path does not exist or is not mounted"})
                continue
            if os.path.isdir(mapped):
                if recursive:
                    walker = os.walk(mapped)
                    for root, _, files in walker:
                        for f in files:
                            ext = os.path.splitext(f)[1].lower()
                            if ext in VIDEO_EXTENSIONS:
                                cont_path = os.path.join(root, f)
                                host_path = self._map_container_to_host_file(cont_path, params) if in_container else cont_path
                                if host_path not in seen:
                                    seen.add(host_path)
                                    found.append(host_path)
                else:
                    try:
                        for f in os.listdir(mapped):
                            cont_path = os.path.join(mapped, f)
                            if os.path.isfile(cont_path):
                                ext = os.path.splitext(f)[1].lower()
                                if ext in VIDEO_EXTENSIONS:
                                    host_path = self._map_container_to_host_file(cont_path, params) if in_container else cont_path
                                    if host_path not in seen:
                                        seen.add(host_path)
                                        found.append(host_path)
                    except Exception:
                        skips.append({"path": raw, "status": "skipped", "reason": "unable to read directory"})
            else:
                ext = os.path.splitext(raw)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    if raw not in seen:
                        seen.add(raw)
                        found.append(raw)
                else:
                    skips.append({"path": raw, "status": "skipped", "reason": "unsupported extension"})
        return sorted(found), skips

    def _detect_scenes(self, video_path: str, threshold: float) -> List[Tuple[Any, Any]]:
        video = open_video(video_path)
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=threshold))
        manager.detect_scenes(video)
        return manager.get_scene_list()

    def _serialize_scenes(self, scene_list: List[Tuple[Any, Any]]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for start, end in scene_list:
            items.append({
                "start_timecode": str(start),
                "end_timecode": str(end),
                "start_seconds": start.get_seconds(),
                "end_seconds": end.get_seconds(),
            })
        return items

    def _derive_scenes_json_path(self, video_path: str) -> str:
        base, _ = os.path.splitext(video_path)
        return f"{base}.scenes.json"

    def _write_json(self, path: str, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
