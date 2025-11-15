from task.BaseTask import BaseTask
from typing import Any, Dict
import html
import json
import os
import uuid

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
                "yt-dlp==2024.8.6",
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

    def _download_video(self, video_url: str) -> Dict[str, Any]:
        """Download a single YouTube video."""
        import yt_dlp
        video_uuid = str(uuid.uuid4())
        task_dir = os.path.dirname(os.path.abspath(__file__))
        commander_dir = os.path.dirname(task_dir)
        download_dir = os.path.join(commander_dir, 'var', self.name(), video_uuid)
        os.makedirs(download_dir, exist_ok=True)
        self._print(f"Downloading: {video_url} -> {video_uuid}")
        ydl_opts = self._get_config()
        ydl_opts['outtmpl'] = os.path.join(download_dir, '%(title)s.%(ext)s')
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_id = info.get('id', video_uuid)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            filename = ydl.prepare_filename(info)
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

    def _get_config(self) -> Dict[str, Any]:
        """Load yt-dlp configuration from /cfg/yt_downloader_config.json."""
        config_path = '/cfg/yt_downloader_config.json'
        with open(config_path, 'r') as f:
            return json.load(f)
