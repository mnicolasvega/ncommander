from task.BaseTask import BaseTask
from typing import Any, Dict
import html
import json
import os
import re
import uuid
import yt_dlp

class YouTubeDownloader(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            video_urls = carry.get('video_urls', [])
            if not video_urls or len(video_urls) == 0:
                return {"error": "video_urls list is required", "downloads": []}
            downloads = []
            for video_url in video_urls:
                url_str = str(video_url).strip()
                if not url_str:
                    continue
                try:
                    # Check if video exists locally first (without API call)
                    existing_result = self._check_local_video_exists(url_str)
                    if existing_result:
                        self._print(f"Skipping: {existing_result.get('title', 'Unknown')} ({existing_result.get('video_id', 'unknown')}) - already exists")
                        downloads.append(existing_result)
                        continue
                    
                    # Video doesn't exist locally, proceed with download
                    result = self._download_video(url_str)
                    downloads.append(result)
                except Exception as e:
                    self._print(f"Error downloading {url_str}: {str(e)}")
                    downloads.append({
                        "url": url_str,
                        "status": "error",
                        "error": str(e)
                    })
            
            return {"downloads": downloads}
        except Exception as e:
            import traceback
            self._print(f"Error: {str(e)}")
            self._print(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "downloads": []}

    def text_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data and not data.get('downloads'):
            return f"error: {data['error']}"
        downloads = data.get('downloads', [])
        output_lines = []
        for download in downloads:
            url = download.get('url', '')
            status = download.get('status', 'unknown')
            if status == 'success':
                video_id = download.get('video_id', '')
                title = download.get('title', 'Unknown')
                output_lines.append(f"✓ {title} ({video_id})")
            else:
                error = download.get('error', 'Unknown error')
                output_lines.append(f"✗ {url}: {error}")
        return "\n".join(output_lines)[:2000]

    def html_output(self, data: Dict[str, Any]) -> str:
        if 'error' in data and not data.get('downloads'):
            return self._render_html_from_template('template/YouTubeDownloaderError.html', {
                'error_message': html.escape(str(data['error']))
            })
        downloads = data.get('downloads', [])
        composed_html = []
        for download in downloads:
            status = download.get('status', 'unknown')
            if status == 'success':
                url = html.escape(str(download.get('url', '')))
                video_id = html.escape(str(download.get('video_id', '')))
                title = html.escape(str(download.get('title', 'Unknown')))
                path = html.escape(str(download.get('path', '')))
                duration = html.escape(str(download.get('duration', '')))
                download_html = self._render_html_from_template('template/YouTubeDownloaderSuccess.html', {
                    'url': url,
                    'video_id': video_id,
                    'title': title,
                    'path': path,
                    'duration': duration
                })
            else:
                url = html.escape(str(download.get('url', '')))
                error = html.escape(str(download.get('error', 'Unknown error')))
                download_html = self._render_html_from_template('template/YouTubeDownloaderFailed.html', {
                    'url': url,
                    'error': error
                })
            composed_html.append(download_html)
        content = '\n'.join(composed_html)
        return self._render_html_from_template('template/YouTubeDownloader.html', {
            'content': content
        })

    def name(self) -> str:
        return "youtube_downloader"

    def interval(self) -> int:
        return 60 * 60

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": [
                "yt-dlp>=2024.11.18",
            ],
            "other": [],
        }

    def volumes(self, params: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        var_dir = os.path.join(commander_dir, 'var', self.name())
        config_file = os.path.join(commander_dir, 'cfg', 'yt_downloader_config.json')
        volumes = {
            var_dir: {
                "bind": f"/app/var/{self.name()}",
                "mode": "rw",
            },
            config_file: {
                "bind": "/cfg/yt_downloader_config.json",
                "mode": "ro",
            }
        }
        return volumes

    def ports(self, params: Dict[str, Any]) -> Dict[int, int]:
        return {}

    def requires_connection(self) -> bool:
        return True

    def max_time_expected(self) -> float | None:
        return None

    def _extract_video_id_from_url(self, video_url: str) -> str | None:
        """Extract YouTube video ID from URL without making API calls."""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/|v\/|youtu\.be\/)([0-9A-Za-z_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                return match.group(1)
        return None

    def _check_local_video_exists(self, video_url: str) -> Dict[str, Any] | None:
        """Check if video exists locally without making API calls."""
        video_id = self._extract_video_id_from_url(video_url)
        if not video_id:
            return None
        
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        var_root = os.path.join(commander_dir, 'var', self.name())
        video_dir = os.path.join(var_root, video_id)
        
        if os.path.isdir(video_dir):
            # Look for video files in the directory
            video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.m4v')
            for file in os.listdir(video_dir):
                if file.lower().endswith(video_extensions):
                    existing_path = os.path.join(video_dir, file)
                    # Extract title from filename (remove extension)
                    title = os.path.splitext(file)[0]
                    return {
                        "url": video_url,
                        "video_id": video_id,
                        "video_uuid": "",
                        "title": title,
                        "duration": "unknown",
                        "path": existing_path,
                        "status": "success"
                    }
        return None

    def _download_video(self, video_url: str) -> Dict[str, Any]:
        """Download a single YouTube video."""
        video_uuid = str(uuid.uuid4())
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        var_root = os.path.join(commander_dir, 'var', self.name())
        
        # Get video info and check if it exists (with API call)
        ydl_opts = self._get_config()
        ydl_opts['outtmpl'] = os.path.join(var_root, '%(title)s.%(ext)s')
        result, probe_video_id, probe_title, probe_duration = self._check_video_exists(video_url, ydl_opts, var_root, video_uuid)
        if result:
            return result
        
        # Video doesn't exist, proceed with download
        self._print(f"Downloading: {video_url} -> {video_uuid}")
        download_dir = os.path.join(var_root, probe_video_id)
        os.makedirs(download_dir, exist_ok=True)
        ydl_opts['outtmpl'] = os.path.join(download_dir, '%(title)s.%(ext)s')
        info, filename = self._perform_download(video_url, ydl_opts, probe_video_id, probe_title, probe_duration)
        video_id = info.get('id', probe_video_id)
        title = info.get('title', probe_title)
        duration = info.get('duration', probe_duration)
        channel_name = info.get('uploader') or info.get('channel') or ''
        self._update_video_ids_map(var_root, video_id, video_uuid, channel_name, title)
        self._print(f"Downloaded: {title} ({video_id})")
        return {
            "url": video_url,
            "video_id": video_id,
            "video_uuid": video_uuid,
            "title": title,
            "duration": f"{duration}s" if duration else "unknown",
            "path": filename,
            "status": "success"
        }

    def _check_video_exists(self, video_url: str, ydl_opts: Dict[str, Any], var_root: str, video_uuid: str) -> tuple:
        """Check if video already exists. Returns (result_dict or None, probe_video_id, probe_title, probe_duration)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_probe = ydl.extract_info(video_url, download=False)
            probe_video_id = info_probe.get('id', video_uuid)
            probe_title = info_probe.get('title', 'Unknown')
            probe_duration = info_probe.get('duration', 0)
        
        # Check if video_id directory exists and contains video files
        video_dir = os.path.join(var_root, probe_video_id)
        if os.path.isdir(video_dir):
            # Look for video files in the directory
            video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.m4v')
            for file in os.listdir(video_dir):
                if file.lower().endswith(video_extensions):
                    existing_path = os.path.join(video_dir, file)
                    return {
                        "url": video_url,
                        "video_id": probe_video_id,
                        "video_uuid": "",
                        "title": probe_title,
                        "duration": f"{probe_duration}s" if probe_duration else "unknown",
                        "path": existing_path,
                        "status": "success"
                    }, probe_video_id, probe_title, probe_duration
        
        return None, probe_video_id, probe_title, probe_duration

    def _update_video_ids_map(self, var_root: str, video_id: str, video_uuid: str, channel_name: str, title: str) -> None:
        """Append video mapping to uuids.csv."""
        uuids_file = os.path.join(var_root, 'uuids.csv')
        try:
            with open(uuids_file, 'a', encoding='utf-8') as f:
                f.write(f"{video_id},{video_uuid},{channel_name},{title.replace('\n', ' ').replace('\r', ' ')}\n")
        except Exception:
            pass

    def _perform_download(self, video_url: str, ydl_opts: Dict[str, Any], probe_video_id: str, probe_title: str, probe_duration: int) -> tuple:
        """Download video file and return (info dict, filename)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
        return info, filename

    def _get_config(self) -> Dict[str, Any]:
        """Load yt-dlp configuration from /cfg/yt_downloader_config.json."""
        config_path = '/cfg/yt_downloader_config.json'
        with open(config_path, 'r') as f:
            return json.load(f)
