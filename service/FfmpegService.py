import subprocess

class FfmpegService:
    def get_video_duration(video_path: str, timeout: int = 10) -> float:
        """
        Get video duration in seconds using ffprobe.
        """
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        duration_str = result.stdout.strip()
        if not duration_str:
            raise ValueError(f"No duration found for video: {video_path}")
        try:
            return float(duration_str)
        except ValueError as e:
            raise ValueError(f"Invalid duration format: {duration_str}") from e
