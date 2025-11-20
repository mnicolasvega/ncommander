import html
import os
import subprocess
from task.BaseTask import BaseTask
from typing import Any, Dict, List

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".m4v", ".flv", ".mpg", ".mpeg", ".wmv"
}


class ThumbnailCreatorTask(BaseTask):
    def name(self) -> str:
        return "thumbnail_creator"

    def memory_gb(self) -> float:
        return 4.0

    def interval(self) -> int | None:
        return 60 * 60

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            video_paths_raw = carry.get("video_paths", [])
            if not isinstance(video_paths_raw, list) or len(video_paths_raw) == 0:
                return {"error": "video_paths is required and must be a non-empty list", "files": []}

            interval_ms = int(carry.get("interval_ms", 5000))
            if interval_ms <= 0:
                return {"error": "interval_ms must be a positive integer", "files": []}

            in_container = bool(carry.get("in_container", False))
            recursive = bool(carry.get("recursive", True))
            self._print(f"params: in_container={in_container}, recursive={recursive}, interval_ms={interval_ms}")
            
            inputs: List[str] = [str(p).strip() for p in video_paths_raw if str(p).strip()]
            results: List[Dict[str, Any]] = []
            processed = 0
            skipped = 0
            failed = 0

            files, expand_skips = self._collect_video_files(inputs, recursive, in_container, carry)
            self._print(f"collection: video_files={len(files)}, skips={len(expand_skips)}")
            results.extend(expand_skips)
            skipped += len(expand_skips)

            for idx, host_video_path in enumerate(files, start=1):
                try:
                    self._print(f"processing [{idx}/{len(files)}]: {host_video_path}")
                    mapped_video_path = self._map_host_to_container_file(host_video_path, carry) if in_container else host_video_path
                    
                    if not os.path.exists(mapped_video_path):
                        skipped += 1
                        results.append({
                            "path": host_video_path,
                            "status": "skipped",
                            "reason": "video does not exist or is not mounted"
                        })
                        continue

                    dir_root = str(carry.get("outdir", "/app/tmp"))
                    frames_dir_container = self._derive_output_frames_dir(dir_root, mapped_video_path)
                    frames_dir_host = self._map_container_to_host_file(frames_dir_container, carry) if in_container else frames_dir_container
                    
                    # Skip if output folder exists and contains thumbnails
                    if os.path.exists(frames_dir_container):
                        try:
                            existing_frames = [f for f in os.listdir(frames_dir_container) if f.endswith('.jpg')]
                            if len(existing_frames) > 0:
                                skipped += 1
                                results.append({
                                    "path": host_video_path,
                                    "status": "skipped",
                                    "reason": f"frames already exist ({len(existing_frames)})",
                                    "frames_dir": frames_dir_host,
                                    "frames": len(existing_frames)
                                })
                                self._print(f"Skipping {mapped_video_path}: frames already exist ({len(existing_frames)})")
                                continue
                        except Exception as e:
                            self._print(f"Error checking existing frames: {str(e)}")
                    
                    os.makedirs(frames_dir_container, exist_ok=True)

                    # Extract frames using ffmpeg
                    exported = self._extract_frames_ffmpeg(mapped_video_path, frames_dir_container, interval_ms)

                    if exported > 0:
                        processed += 1
                        results.append({
                            "path": host_video_path,
                            "status": "success",
                            "frames_dir": frames_dir_host,
                            "frames": exported
                        })
                    else:
                        failed += 1
                        results.append({
                            "path": host_video_path,
                            "status": "error",
                            "error": "no frames extracted"
                        })

                except Exception as e:
                    self._print(f"error processing {host_video_path}: {str(e)}")
                    failed += 1
                    results.append({
                        "path": host_video_path,
                        "status": "error",
                        "error": str(e)
                    })

            summary = {
                "files": results,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "files_count": len(results),
                "interval_ms": interval_ms,
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
        interval_ms = int(data.get('interval_ms', 0))
        return f"videos: {total}, processed: {processed}, skipped: {skipped}, failed: {failed}, interval: {interval_ms}ms"

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
            
            # Build thumbnails HTML
            thumbnails_html = ''
            
            # Show thumbnails for both success and skipped (when frames already exist)
            should_show_thumbnails = (status == 'success' or (status == 'skipped' and 'frames already exist' in reason)) and frames_dir and os.path.exists(frames_dir)
            
            if should_show_thumbnails:
                # List thumbnail files
                try:
                    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
                    thumbnail_parts = []
                    for frame_file in frame_files:
                        frame_path = os.path.join(frames_dir, frame_file)
                        # Convert to var-relative path for Flask serving
                        relative_path = self._get_var_relative_path(frame_path)
                        thumbnail_parts.append(self._render_html_from_template('template/ThumbnailCreatorThumbnail.html', {
                            'thumbnail_path': html.escape(relative_path),
                            'thumbnail_name': html.escape(frame_file),
                        }))
                    
                    if thumbnail_parts:
                        thumbnails_html = '\n'.join(thumbnail_parts)
                except Exception as e:
                    thumbnails_html = html.escape(f"Error listing frames: {str(e)}")
            
            items_html_parts.append(self._render_html_from_template('template/ThumbnailCreatorItem.html', {
                'index': str(idx),
                'video_name': html.escape(video_name),
                'path': path,
                'status': status,
                'frames_count': frames_count,
                'frames_dir': html.escape(frames_dir),
                'error': err,
                'reason': reason,
                'thumbnails_box': thumbnails_html,
            }))
        
        summary_html = self._render_html_from_template('template/ThumbnailCreatorSummary.html', {
            'processed': str(data.get('processed', 0)),
            'skipped': str(data.get('skipped', 0)),
            'failed': str(data.get('failed', 0)),
            'interval_ms': str(data.get('interval_ms', 0)),
        })
        
        return self._render_html_from_template('template/ThumbnailCreatorList.html', {
            'summary': summary_html,
            'items': '\n'.join(items_html_parts),
        })

    def dependencies(self) -> Dict[str, Any]:
        return {
            "other": [
                "ffmpeg",
            ],
        }

    def _extract_frames_ffmpeg(self, video_path: str, output_dir: str, interval_ms: int) -> int:
        """
        Extract frames at regular intervals using ffmpeg.
        Returns the number of frames extracted.
        """
        try:
            # Calculate fps for ffmpeg (1 frame per interval_ms milliseconds)
            # fps = 1 / (interval_ms / 1000)
            fps_str = f"1/{interval_ms/1000}"
            
            # ffmpeg command to extract frames at specified intervals
            # -vf fps=<fps> extracts frames at the specified rate
            # thumb_%04d.jpg names the output files
            output_pattern = os.path.join(output_dir, "thumb_%04d.jpg")
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"fps={fps_str}",
                "-q:v", "2",  # Quality level (2 is high quality)
                output_pattern,
                "-loglevel", "error",  # Only show errors
                "-y"  # Overwrite output files
            ]
            
            self._print(f"Running ffmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self._print(f"ffmpeg error: {result.stderr}")
                return 0
            
            # Count generated frames
            frame_files = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
            self._print(f"Extracted {len(frame_files)} frames at {interval_ms}ms intervals")
            return len(frame_files)
            
        except Exception as e:
            self._print(f"Error extracting frames: {str(e)}")
            return 0

    def _derive_output_frames_dir(self, outdir: str, video_path: str) -> str:
        base_name = os.path.basename(video_path)
        # Use var/thumbnail_creator/<video_name>/
        commander_dir = os.path.dirname(outdir)  # Gets /app or /path/to/ncommander
        return os.path.join(commander_dir, "var", self.name(), base_name)

    def _collect_video_files(self, inputs: List[str], recursive: bool, in_container: bool, params: Dict[str, Any]) -> (List[str], List[Dict[str, Any]]):
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
                ext = os.path.splitext(mapped)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    host_path = self._map_container_to_host_file(mapped, params) if in_container else mapped
                    if host_path not in seen:
                        seen.add(host_path)
                        found.append(host_path)
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
                "bind": f"/mnt/thumbnail_input_{i}",
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
