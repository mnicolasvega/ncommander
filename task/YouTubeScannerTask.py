from task.YouTubeChannelScannerTask import YouTubeChannelScannerTask
from typing import Any, Dict, List

OUTPUT_VIDEOS = 10

class YouTubeScannerTask(YouTubeChannelScannerTask):
    def __init__(self) -> None:
        super().__init__()

    def name(self) -> str:
        return "youtube_scanner"

    def interval(self) -> int:
        return 60 * 60

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        channels = params['channels']
        result = {}
        for group_name, channels in channels.items():
            channel_list = channels.split(",")
            print(f"Processing group: {group_name}")
            group_result = {}
            for channel in channel_list:
                print(f"  Processing channel: {channel}")
                channel_params = params.copy()
                channel_params['channel'] = channel
                channel_result = super().run(channel_params)
                group_result[channel] = channel_result
            result[group_name] = group_result
        return result

    def text_output(self, data: Dict[str, Any]) -> str:
        text = ''
        for group_name, group in data.items():
            for channel_name, channel in group.items():
                text += f"\n\n{channel_name}\n" + super().text_output(channel)
        return text

    def html_output(self, data: Dict[str, Any]) -> str:
        group_htmls = ""
        for group_name, group_data in data.items():
            channel_htmls = ""
            for channel_name, channel_data in group_data.items():
                channel_html = super().html_output(channel_data)
                channel_html = self._render_html_from_template('template/YouTubeScannerTaskChannel.html', {
                    'channel_name': channel_name,
                    'channel_content': channel_html
                })
                channel_htmls += channel_html + "\n"
            group_html = self._render_html_from_template('template/YouTubeScannerTaskGroup.html', {
                'group_name': group_name,
                'channel_list': channel_htmls
            })
            group_htmls += group_html + "\n"
        html = self._render_html_from_template('template/YouTubeScannerTaskGroupList.html', {
            'group_list': group_htmls
        })
        return html

    def _get_videos_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        videos = self._get_videos(data.get('html', ''))
        videos_data_list = []
        for video in videos.values():
            video_data = self._get_video_data(video)
            if video_data.get('is_new') == "no":
                videos_data_list.append(video_data)
                break
            videos_data_list.append(video_data)
            if len(videos_data_list) >= OUTPUT_VIDEOS:
                break
        return videos_data_list
