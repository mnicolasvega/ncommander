from dotenv import load_dotenv
from task.DirObserver import DirObserver
from task.FlaskTask import FlaskTask
from task.Message import Message
from task.SystemMonitor import SystemMonitor
from task.YouTubeScannerTask import YouTubeScannerTask
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
        {
            'task': FlaskTask(),
            'parameters': {'port': 7000},
            'order': 1
        },
        # {
        #     'task': YouTubeScannerTask(),
        #     'parameters': {'channels': YOUTUBE_CHANNELS_JSON},
        #     'order': 1
        # },
        {
            'task': Message(),
            'parameters': {},
            'order': 2
        },
        {
            'task': DirObserver(PATH_DIR_OBSERVER),
            'parameters': {},
            'order': 3
        },
        {
            'task': SystemMonitor(),
            'parameters': {},
            'order': 4
        },
    ]
    commander = TaskCommander(
        print_cycles = DEBUG,
        print_docker_container_logs = DEBUG,
        print_docker_container_lifecycle = DEBUG,
        run_containerless = False,
        force_rebuild = True
    )
    commander.run(tasks)

if __name__ == "__main__":
    main()
