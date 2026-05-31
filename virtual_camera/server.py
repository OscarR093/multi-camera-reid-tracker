import subprocess
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class VirtualCameraServer:
    def __init__(
        self,
        video_path: str,
        rtsp_port: int = 8554,
        loop: bool = True,
    ):
        self.video_path = video_path
        self.rtsp_port = rtsp_port
        self.loop = loop
        self.process: Optional[subprocess.Popen] = None
        self._running = False

    @property
    def rtsp_url(self) -> str:
        return f"rtsp://localhost:{self.rtsp_port}/stream"

    def start(self) -> bool:
        if not os.path.exists(self.video_path):
            logger.error(f"Video file not found: {self.video_path}")
            return False

        loop_flag = "-stream_loop -1" if self.loop else ""

        cmd = (
            f"ffmpeg -re {loop_flag} -i {self.video_path} "
            f"-c copy -f rtsp "
            f"-rtsp_transport tcp "
            f"rtsp://localhost:{self.rtsp_port}/stream"
        )

        logger.info(f"Starting virtual camera on port {self.rtsp_port}")
        logger.info(f"Source video: {self.video_path}")

        self.process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._running = True
        return True

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self._running = False
            logger.info(f"Virtual camera on port {self.rtsp_port} stopped")

    @property
    def running(self) -> bool:
        return self._running
