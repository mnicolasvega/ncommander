from task.BaseTask import BaseTask
from typing import Any, Dict, List
import cv2
import html
import json
import os

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".m4v", ".flv", ".mpg", ".mpeg", ".wmv"
}

# TODO: AI generated, review.
class SceneFrameExtractorTask(BaseTask):
    def name(self) -> str:
        return "scene_frame_extractor"

    def memory_gb(self) -> float:
        return 10.0

    def interval(self) -> int | None:
        return 60 * 60

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            video_paths_raw = carry.get("video_paths", [])
            if not isinstance(video_paths_raw, list) or len(video_paths_raw) == 0:
                return {"error": "video_paths is required and must be a non-empty list", "files": []}

            in_container = bool(carry.get("in_container", False))
            recursive = bool(carry.get("recursive", True))
            self._print(f"params: in_container={in_container}, recursive={recursive}")
            inputs: List[str] = [str(p).strip() for p in video_paths_raw if str(p).strip()]
            results: List[Dict[str, Any]] = []
            processed = 0
            skipped = 0
            failed = 0

            files, expand_skips = self._collect_scene_json_files(inputs, recursive, in_container, carry)
            self._print(f"collection: json_files={len(files)}, skips={len(expand_skips)}")
            results.extend(expand_skips)
            skipped += len(expand_skips)
            self._print(f"collected json_files={len(files)}, expand_skips={len(expand_skips)}")

            for idx, host_json_path in enumerate(files, start=1):
                try:
                    self._print(f"processing [{idx}/{len(files)}]: {host_json_path}")
                    mapped_json_path = self._map_host_to_container_file(host_json_path, carry) if in_container else host_json_path
                    if not os.path.exists(mapped_json_path):
                        skipped += 1
                        results.append({
                            "path": host_json_path,
                            "status": "skipped",
                            "reason": "json does not exist or is not mounted"
                        })
                        continue

                    with open(mapped_json_path, 'r', encoding='utf-8') as f:
                        payload = json.load(f)

                    video_path_in_json = str(payload.get("path", "")).strip()
                    if not video_path_in_json:
                        skipped += 1
                        results.append({
                            "path": host_json_path,
                            "status": "skipped",
                            "reason": "video path missing in json"
                        })
                        continue

                    video_path = video_path_in_json
                    if not os.path.exists(video_path):
                        alt = self._map_host_to_container_file(video_path, carry) if in_container else video_path
                        if os.path.exists(alt):
                            video_path = alt
                        else:
                            skipped += 1
                            results.append({
                                "path": host_json_path,
                                "status": "skipped",
                                "reason": "video path from json does not exist"
                            })
                            continue

                    scenes = payload.get("scenes", [])
                    dir_root = str(carry.get("outdir", "/app/tmp"))
                    frames_dir_container = self._derive_output_frames_dir(dir_root, video_path)
                    frames_dir_host = frames_dir_container
                    
                    # Skip if output folder exists and contains expected number of thumbnails
                    if os.path.exists(frames_dir_container):
                        try:
                            existing_frames = [f for f in os.listdir(frames_dir_container) if f.endswith('.jpg')]
                            expected_frames = len(scenes)
                            if len(existing_frames) == expected_frames and expected_frames > 0:
                                skipped += 1
                                results.append({
                                    "path": self._map_container_to_host_file(video_path, carry) if in_container else video_path,
                                    "status": "skipped",
                                    "reason": f"frames already exist ({len(existing_frames)}/{expected_frames})",
                                    "frames_dir": frames_dir_host,
                                    "frames": len(existing_frames)
                                })
                                self._print(f"Skipping {video_path}: frames already exist ({len(existing_frames)}/{expected_frames})")
                                continue
                        except Exception as e:
                            self._print(f"Error checking existing frames: {str(e)}")
                    
                    os.makedirs(frames_dir_container, exist_ok=True)

                    cap = cv2.VideoCapture(video_path)
                    if not cap.isOpened():
                        skipped += 1
                        results.append({
                            "path": frames_dir_host,
                            "status": "skipped",
                            "reason": "unable to open video"
                        })
                        continue

                    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
                    exported = 0
                    for sidx, s in enumerate(scenes, start=1):
                        try:
                            start_sec = float(s.get('start_seconds', 0.0))
                            end_sec = float(s.get('end_seconds', 0.0))
                            if end_sec > start_sec:
                                ts = start_sec + (end_sec - start_sec) / 2.0
                            else:
                                ts = start_sec
                            if fps > 0:
                                frame_index = max(0, int(ts * fps))
                                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                            else:
                                cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, ts * 1000.0))
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                out_name = f"scene_{sidx:04d}.jpg"
                                out_path = os.path.join(frames_dir_container, out_name)
                                if cv2.imwrite(out_path, frame):
                                    exported += 1
                        except Exception as inner_e:
                            self._print(f"frame export error: {str(inner_e)}")
                            continue

                    cap.release()

                    processed += 1
                    results.append({
                        "path": self._map_container_to_host_file(video_path, carry) if in_container else video_path,
                        "status": "success",
                        "frames_dir": frames_dir_host,
                        "frames": exported
                    })
                except Exception as e:
                    self._print(f"error processing {host_json_path}: {str(e)}")
                    failed += 1
                    results.append({
                        "path": host_json_path,
                        "status": "error",
                        "error": str(e)
                    })

            summary = {
                "files": results,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "files_count": len(results),
            }
            self._print(f"summary: processed={processed}, skipped={skipped}, failed={failed}, files={len(results)}")
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
        files = data.get('files', [])
        items_html_parts: List[str] = []
        
        for idx, item in enumerate(files, start=1):
            path = html.escape(str(item.get('path', '')))
            status = html.escape(str(item.get('status', 'unknown')))
            frames_count = html.escape(str(item.get('frames', 0)))
            frames_dir = str(item.get('frames_dir', '')).strip()
            err = html.escape(str(item.get('error', '')))
            reason = html.escape(str(item.get('reason', '')))
            
            # Get video name
            video_name = os.path.basename(path) if path else 'Unknown'
            
            # Build timestamps and thumbnails HTML
            timestamps_html = ''
            thumbnails_html = ''
            
            if status == 'success' and frames_dir and os.path.exists(frames_dir):
                # Get scene timestamps from the corresponding .scenes.json
                scenes_json_path = self._derive_scenes_json_path(path)
                if os.path.exists(scenes_json_path):
                    try:
                        with open(scenes_json_path, 'r', encoding='utf-8') as f:
                            scenes_data = json.load(f)
                        scenes = scenes_data.get('scenes', [])
                        
                        # Build timestamps rows
                        timestamp_rows = []
                        for sidx, scene in enumerate(scenes, start=1):
                            start_tc = html.escape(str(scene.get('start_timecode', '')))
                            end_tc = html.escape(str(scene.get('end_timecode', '')))
                            timestamp_rows.append(self._render_html_from_template('template/SceneFrameExtractorTimestamp.html', {
                                'index': str(sidx),
                                'start_timecode': start_tc,
                                'end_timecode': end_tc,
                            }))
                        
                        if timestamp_rows:
                            timestamps_html = self._render_html_from_template('template/SceneFrameExtractorTimestampBox.html', {
                                'rows': '\n'.join(timestamp_rows)
                            })
                    except Exception as e:
                        timestamps_html = html.escape(f"Error reading scenes: {str(e)}")
                
                # List thumbnail files
                try:
                    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
                    thumbnail_parts = []
                    for frame_file in frame_files:
                        frame_path = os.path.join(frames_dir, frame_file)
                        thumbnail_parts.append(self._render_html_from_template('template/SceneFrameExtractorThumbnail.html', {
                            'thumbnail_path': html.escape(frame_path),
                            'thumbnail_name': html.escape(frame_file),
                        }))
                    
                    if thumbnail_parts:
                        thumbnails_html = '\n'.join(thumbnail_parts)
                except Exception as e:
                    thumbnails_html = html.escape(f"Error listing frames: {str(e)}")
            
            items_html_parts.append(self._render_html_from_template('template/SceneFrameExtractorItem.html', {
                'index': str(idx),
                'video_name': html.escape(video_name),
                'path': path,
                'status': status,
                'frames_count': frames_count,
                'frames_dir': html.escape(frames_dir),
                'error': err,
                'reason': reason,
                'timestamps_box': timestamps_html,
                'thumbnails_box': thumbnails_html,
            }))
        
        summary_html = self._render_html_from_template('template/SceneFrameExtractorSummary.html', {
            'processed': str(data.get('processed', 0)),
            'skipped': str(data.get('skipped', 0)),
            'failed': str(data.get('failed', 0)),
        })
        
        return self._render_html_from_template('template/SceneFrameExtractorList.html', {
            'summary': summary_html,
            'items': '\n'.join(items_html_parts),
        })

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": [
                "numpy==1.26.4",
                "opencv-python-headless==4.9.0.80",
            ],
            "other": [
                "ffmpeg",
            ],
        }

    def _derive_output_frames_dir(self, outdir: str, video_path: str) -> str:
        base_name = os.path.basename(video_path)
        return os.path.join(outdir, "tasks", self.name(), "container", base_name)

    def _collect_scene_json_files(self, inputs: List[str], recursive: bool, in_container: bool, params: Dict[str, Any]) -> (List[str], List[Dict[str, Any]]):
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
                    for root, _, files in os.walk(mapped):
                        for f in files:
                            if f.endswith('.scenes.json'):
                                cont_path = os.path.join(root, f)
                                host_path = self._map_container_to_host_file(cont_path, params) if in_container else cont_path
                                if host_path not in seen:
                                    seen.add(host_path)
                                    found.append(host_path)
                else:
                    try:
                        for f in os.listdir(mapped):
                            cont_path = os.path.join(mapped, f)
                            if os.path.isfile(cont_path) and f.endswith('.scenes.json'):
                                host_path = self._map_container_to_host_file(cont_path, params) if in_container else cont_path
                                if host_path not in seen:
                                    seen.add(host_path)
                                    found.append(host_path)
                    except Exception:
                        skips.append({"path": raw, "status": "skipped", "reason": "unable to read directory"})
            else:
                if mapped.endswith('.scenes.json'):
                    host_path = self._map_container_to_host_file(mapped, params) if in_container else mapped
                    if host_path not in seen:
                        seen.add(host_path)
                        found.append(host_path)
                else:
                    ext = os.path.splitext(mapped)[1].lower()
                    if ext in VIDEO_EXTENSIONS:
                        cont_json = self._derive_scenes_json_path(mapped)
                        if os.path.exists(cont_json):
                            host_json = self._map_container_to_host_file(cont_json, params) if in_container else cont_json
                            if host_json not in seen:
                                seen.add(host_json)
                                found.append(host_json)
                        else:
                            skips.append({"path": raw, "status": "skipped", "reason": "scenes json not found"})
                    else:
                        skips.append({"path": raw, "status": "skipped", "reason": "unsupported extension"})
        return sorted(found), skips

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        volumes: Dict[str, Dict[str, str]] = {}
        video_paths = params.get("video_paths", []) or []
        mount_points: List[str] = []
        for p in video_paths:
            sp = str(p).strip()
            if not sp or not os.path.isabs(sp):
                continue
            ext = os.path.splitext(sp)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                mount_points.append(os.path.dirname(sp))
            else:
                mount_points.append(sp)
        unique_mounts = sorted(set(mount_points))
        for i, mount_point in enumerate(unique_mounts):
            volumes[mount_point] = {
                "bind": f"/mnt/scene_input_{i}",
                "mode": "rw",
            }
        return volumes

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

    def _derive_scenes_json_path(self, video_path: str) -> str:
        base, _ = os.path.splitext(video_path)
        return f"{base}.scenes.json"
