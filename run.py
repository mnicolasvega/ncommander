from dotenv import load_dotenv
from task.DirManager import DirManager
from task.DirObserver import DirObserver
from task.FlaskTask import FlaskTask
from task.LlamaLLM import LlamaLLM
from task.Message import Message
from task.SystemMonitor import SystemMonitor
from task.TaskData import TaskData
from task.UI import UI
from task.YouTubeDownloader import YouTubeDownloader
from task.YouTubeScannerTask import YouTubeScannerTask
from task.WhisperSubtitleTask import WhisperSubtitleTask
from TaskCommander import TaskCommander
import json
import os

load_dotenv()
PATH_DIR_OBSERVER = os.getenv("PATH_DIR_OBSERVER")
YOUTUBE_CHANNEL = os.getenv("YOUTUBE_CHANNEL")
YOUTUBE_CHANNELS = os.getenv("YOUTUBE_CHANNELS").split(",")
YOUTUBE_CHANNELS_JSON = json.loads(os.getenv("YOUTUBE_CHANNELS_JSON"))
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")
ROOT = '/app/tmp'
DEBUG = True

def main() -> None:
    tasks = [
        #{
        #    'task': FlaskTask(),
        #    'parameters': {'port': 7000},
        #    'order': 1
        #},
        {
            'task': UI(),
            'parameters': {'port': 7000},
            'order': 101
        },
        #{
        #    'task': LlamaLLM(),
        #    'parameters': {
        #        'prompts': [
        #            "What is a black hole?",
        #            "What is a white hole?",
        #            "What is a wormhole?",
        #        ],
        #        'model_name': LLM_MODEL_NAME,
        #    },
        #    'order': 1
        #},
        #{
        #    'task': YouTubeScannerTask(),
        #    'parameters': {'channels': YOUTUBE_CHANNELS_JSON},
        #    'order': 1
        #},
        #{
        #    'task': YouTubeDownloader(),
        #    'parameters': {
        #        'video_urls': [
        #            'https://www.youtube.com/watch?v=3QlHvz_N8m8',
        #            'https://www.youtube.com/watch?v=1WFhPFDRbWU',
        #        ]
        #    },
        #    'order': 1
        #},
        {
            'task': WhisperSubtitleTask(),
            'parameters': {
                'dir_path': '/app/var/youtube_downloader',
            },
            'order': 1
        },
        #{
        #    'task': Message(),
        #    'parameters': {},
        #    'order': 2
        #},
        #{
        #    'task': DirObserver(),
        #    'parameters': {
        #        'paths': [
        #            f"{ROOT}/output",
        #            PATH_DIR_OBSERVER,
        #        ],
        #    },
        #    'order': 3
        #},
        #{
        #    'task': SystemMonitor(),
        #    'parameters': {},
        #    'order': 100
        #},
        #{
        #    'task': TaskData(),
        #    'parameters': {},
        #    'order': 1
        #},
        #{
        #    'task': DirManager(),
        #    'parameters': {},
        #    'order': 5
        #},
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
