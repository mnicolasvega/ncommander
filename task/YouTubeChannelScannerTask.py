from bs4 import BeautifulSoup
from dotenv import load_dotenv
from task.BaseSeleniumTask import BaseSeleniumTask
from typing import Any, Dict, List
import re

load_dotenv()

OUTPUT_VIDEOS = 10

class YouTubeChannelScannerTask(BaseSeleniumTask):
    def __init__(self) -> None:
        super().__init__()

    def name(self) -> str:
        return "youtube_channel_scanner"

    def interval(self) -> int:
        return 5 * 60

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        channel = params['channel']
        params.update({
            'url': f"https://www.youtube.com/@{channel}/videos",
            'script': 'youtube_script',
            'sleep_seconds': 5,
            'scroll_down': True
        })
        result = super().run(params)
        result['channel'] = channel
        return result

    def text_output(self, data: Dict[str, Any]) -> str:
        videos = self._get_videos(data.get('html', ''))
        text = ''
        for idx, video in videos.items():
            title = video.get('title', '')
            text += f"{idx}. {title}\n"
        return text

    def html_output(self, data: Dict[str, Any]) -> str:
        videos_data_list = self._get_videos_data(data)
        channel_data = self._get_channel_data(data)
        channel = data.get('channel', '')
        video_htmls = []
        for video_data in videos_data_list:
            video_html = self._render_html_from_template('template/YouTubeChannelScannerTaskVideo.html', video_data)
            video_htmls.append(video_html)
        display_data = {
            'channel': channel,
            'videos_list': "<br/>\n".join(video_htmls)
        }
        display_data.update(channel_data)
        html = self._render_html_from_template('template/YouTubeChannelScannerTaskChannel.html', display_data)
        return html

    def _get_videos_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        videos = self._get_videos(data.get('html', ''))
        videos_data = []
        for i, video in enumerate(videos.values()):
            if i >= OUTPUT_VIDEOS:
                break
            video_data = self._get_video_data(video)
            videos_data.append(video_data)
        return videos_data

    def _get_videos(self, html: str) -> Dict[int, Dict[str, Any]]:
        if not html:
            return ''
        soup = None
        try:
            soup = BeautifulSoup(html, 'html.parser')
            videos = {}
            items = soup.find_all('ytd-rich-item-renderer')
            for i, item in enumerate(items):
                videos[i] = {}
                content_div = item.find('div', id='content')
                if not content_div:
                    continue
                videos[i]['title'] = self._extract_title(content_div)
                videos[i]['img_src'] = self._extract_img_src(content_div)
                videos[i]['duration'] = self._extract_duration(content_div)
                videos[i]['metadata'] = self._extract_video_metadata(content_div)
                videos[i]['url'] = self._extract_url(content_div)
        except Exception:
            videos = {}
        return videos

    def _get_video_data(self, video: Dict[str, Any]) -> Dict[str, Any]:
        metadata = video.get('metadata', [])
        metadata_str = ", ".join(metadata)
        metadata_dict = self._parse_metadata(metadata_str)
        metadata_lower = metadata_str.lower()
        is_new = any(unit in metadata_lower for unit in ['day', 'hour', 'minute'])
        table_bg_color = 'rgba(0, 255, 0, 0.1)' \
            if is_new else \
            'rgba(255, 255, 255, 0.05)'
        return {
            'url': video.get('url', ''),
            'title': video.get('title', ''),
            'duration': video.get('duration', ''),
            'views': metadata_dict.get('views', ''),
            'video_age': metadata_dict.get('video_age', ''),
            'is_new': "yes" if is_new else "no",
            'table_bg_color': table_bg_color,
        }

    def _parse_metadata(self, data: str) -> Dict[str, Any]:
        m = re.search(r'^\s*([0-9,\.]*[Kk]?)\s+views,\s+(\d+)\s+(\w+)\s+ago\s*$', data)
        if not m:
            return {'views': '', 'video_age': ''}
        views_str = m.group(1).lower()
        views = views_str.replace('k', ' k')
        video_age = m.group(2)
        video_age_len = m.group(3)
        return {'views': views, 'video_age': f"{video_age} {video_age_len}"}

    def _extract_title(self, content_div) -> str:
        title_tag = content_div.find('yt-formatted-string', id='video-title')
        if title_tag:
            text = title_tag.get_text(strip=True)
            if text:
                return text
        return ''

    def _extract_img_src(self, content_div) -> str:
        yt_img_container = content_div.find('yt-image')
        if yt_img_container:
            img_tag = yt_img_container.find('img')
            if img_tag and img_tag.has_attr('src'):
                src = img_tag['src']
                if src:
                    return src
        return ''

    def _extract_duration(self, content_div) -> str:
        time_status_div = content_div.find('div', id='time-status')
        if time_status_div:
            span_text = time_status_div.find('span', id='text')
            if span_text:
                duration = span_text.get_text(strip=True)
                if duration:
                    return duration
        return ''

    def _extract_video_metadata(self, content_div) -> List[str]:
        metadata_div = content_div.find('div', id='metadata-line')
        if not metadata_div:
            return []
        spans = metadata_div.find_all('span')
        meta_texts = []
        for sp in spans:
            t = sp.get_text(strip=True)
            if t:
                meta_texts.append(t)
        return meta_texts

    def _extract_url(self, content_div) -> str:
        link = content_div.find('a', id='video-title-link')
        if not link or not link.has_attr('href'):
            return ''
        href = link['href'].strip()
        if not href:
            return ''
        if href.startswith('http://') or href.startswith('https://'):
            return href
        if href.startswith('/'):
            return f"https://www.youtube.com{href}"
        return f"https://www.youtube.com/{href}"

    def _get_channel_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        html = data.get('html', '')
        soup = BeautifulSoup(html, 'html.parser')
        channel_data = {}
        page_header_container = soup.find('div', id='page-header-container')
        if not page_header_container:
            return channel_data
        channel_data = self._extract_channel_metadata(page_header_container)
        channel_data['channel_display_name'] = self._extract_display_name(page_header_container)
        channel_data['profile_picture'] = self._extract_profile_picture(page_header_container)
        return channel_data

    def _extract_display_name(self, page_header_container) -> str:
        text_view_model = page_header_container.find('yt-dynamic-text-view-model')
        display_name = ''
        if text_view_model:
            channel_name_span = text_view_model.find('span', class_='yt-core-attributed-string')
            if channel_name_span:
                display_name = channel_name_span.get_text(strip=True)
        return display_name

    def _extract_profile_picture(self, page_header_container) -> str:
        avatar_shape = page_header_container.find('yt-avatar-shape')
        pic_src = ''
        if avatar_shape:
            img_tag = avatar_shape.find('img')
            if img_tag and img_tag.has_attr('src'):
                pic_src = img_tag['src']
        return pic_src

    def _extract_channel_metadata(self, page_header_container) -> Dict[str, str]:
        metadata = {}
        metadata_view = page_header_container.find('yt-content-metadata-view-model')
        if metadata_view:
            metadata_spans = metadata_view.find_all('span', class_='yt-core-attributed-string')
            for span in metadata_spans:
                text = span.get_text(strip=True)
                if 'subscriber' in text.lower():
                    metadata['subscriber_count'] = text
                elif 'video' in text.lower() and any(char.isdigit() for char in text):
                    metadata['video_count'] = text
        return metadata
