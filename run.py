from dotenv import load_dotenv
from task.DirObserver import DirObserver
from task.Message import Message
from task.SystemMonitor import SystemMonitor
from task.YouTubeScannerTask import YouTubeScannerTask
from task.YouTubeChannelScannerTask import YouTubeChannelScannerTask
from TaskCommander import TaskCommander
import json
import os

load_dotenv()
PATH_DIR_OBSERVER = os.getenv("PATH_DIR_OBSERVER")
YOUTUBE_CHANNEL = os.getenv("YOUTUBE_CHANNEL")
YOUTUBE_CHANNELS = os.getenv("YOUTUBE_CHANNELS").split(",")
YOUTUBE_CHANNELS_JSON = json.loads(os.getenv("YOUTUBE_CHANNELS_JSON"))
DEBUG = True

def main() -> None:
    tasks = [
        [Message(), {}],
        [DirObserver(PATH_DIR_OBSERVER), {}],
        [SystemMonitor(), {}],
        #[YouTubeChannelScannerTask(), {
        #    'channel': YOUTUBE_CHANNEL
        #}],
        [YouTubeScannerTask(), {
            'channels': YOUTUBE_CHANNELS_JSON
        }]
    ]
    commander = TaskCommander(
        print_cycles = DEBUG,
        print_docker_container_logs = DEBUG,
        print_docker_container_lifecycle = DEBUG
    )
    commander.run(tasks)

if __name__ == "__main__":
    main()
