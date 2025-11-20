from dotenv import load_dotenv
from TaskCommander import TaskCommander
from task.DirManager import DirManager
from task.DirObserver import DirObserver
from task.FlaskTask import FlaskTask
from task.LlamaLLM import LlamaLLM
from task.LlamaVideoSummary import LlamaVideoSummary
from task.Message import Message
from task.SceneChangeDetectorTask import SceneChangeDetectorTask
from task.SceneFrameExtractorTask import SceneFrameExtractorTask
from task.SystemMonitor import SystemMonitor
from task.TaskData import TaskData
from task.UI import UI
from task.WhisperSubtitleTask import WhisperSubtitleTask
from task.YouTubeDownloader import YouTubeDownloader
from task.YouTubeScannerTask import YouTubeScannerTask
import json
import os

load_dotenv()
PATH_DIR_OBSERVER = os.getenv("PATH_DIR_OBSERVER")
PATH_DIR_SCENES = os.getenv("PATH_DIR_SCENES")
YOUTUBE_CHANNEL = os.getenv("YOUTUBE_CHANNEL")
# YOUTUBE_CHANNELS = os.getenv("YOUTUBE_CHANNELS").split(",")
# YOUTUBE_CHANNELS_JSON = json.loads(os.getenv("YOUTUBE_CHANNELS_JSON"))
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")
LLM_MAX_TOKENS = 2048 * 3 
LLM_MAX_CONTEXT_TOKENS = LLM_MAX_TOKENS * 2
ROOT = '/app/tmp'
DEBUG = True

def main() -> None:
    tasks = [
        #{
        #    'task': SceneChangeDetectorTask(),
        #    'parameters': {
        #        'video_paths': [
        #            PATH_DIR_SCENES
        #        ],
        #        'threshold': 27.0,
        #    },
        #    'order': 0
        #},
        {
            'task': SceneFrameExtractorTask(),
            'parameters': {
                'video_paths': [
                    PATH_DIR_SCENES
                ],
                'recursive': True,
            },
            'order': 1
        },
        {
            'task': UI(),
            'parameters': {'port': 7000},
            'order': 101
        },
        # {
        #     'task': LlamaLLM(),
        #     'parameters': {
        #         'prompts': [
        #             "What is a black hole?",
        #             "What is a white hole?",
        #             "What is a wormhole?",
        #         ],
        #         'model_name': LLM_MODEL_NAME,
        #     },
        #     'order': 1
        # },
        # {
        #     'task': YouTubeScannerTask(),
        #     'parameters': {'channels': YOUTUBE_CHANNELS_JSON},
        #     'order': 0
        # },
        # {
        #     'task': YouTubeDownloader(),
        #     'parameters': {
        #         'video_urls': [
        #             'https://www.youtube.com/watch?v=3QlHvz_N8m8',
        #             'https://www.youtube.com/watch?v=1WFhPFDRbWU',
        #         ]
        #     },
        #     'order': 2
        # },
        # {
        #     'task': WhisperSubtitleTask(),
        #     'parameters': {
        #         'dir_path': '/app/var/youtube_downloader',
        #     },
        #     'order': 1
        # },
        # {
        #     'task': LlamaVideoSummary(),
        #     'parameters': {
        #         'dir_path': '/app/var/youtube_downloader',
        #         'model_name': LLM_MODEL_NAME,
        #         'max_context_tokens': LLM_MAX_CONTEXT_TOKENS,
        #         'max_tokens': LLM_MAX_TOKENS,
        #         'temperature': 0.2,
        #     },
        #     'order': 0
        # },
        # {
        #     'task': Message(),
        #     'parameters': {},
        #     'order': 99
        # },
        # {
        #     'task': DirObserver(),
        #     'parameters': {
        #         'paths': [
        #             f"{ROOT}/output",
        #             PATH_DIR_OBSERVER,
        #         ],
        #     },
        #     'order': 3
        # },
        {
            'task': SystemMonitor(),
            'parameters': {},
            'order': 100
        },
        # {
        #     'task': TaskData(),
        #     'parameters': {},
        #     'order': 1
        # },
        # {
        #     'task': DirManager(),
        #     'parameters': {},
        #     'order': 5
        # },
    ]
    commander = TaskCommander(
        print_cycles = DEBUG,
        print_docker_container_logs = DEBUG,
        print_docker_container_lifecycle = DEBUG,
        run_containerless = False,
        force_rebuild = False
    )
    commander.run(tasks)

if __name__ == "__main__":
    main()
