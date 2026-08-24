"""In-memory fake `FrameExtractor` for tests/local runs without `ffmpeg`."""


class FakeFrameExtractor:
    def __init__(self) -> None:
        self.calls: list[bytes] = []

    async def extract_last_frame(self, video_bytes: bytes) -> bytes:
        self.calls.append(video_bytes)
        return b"fake-last-frame:" + video_bytes
