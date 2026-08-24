"""Last-frame extraction contract (Module 08).

See research/PRODUCTION_STACK_2026.md "Previous-frame continuity": for
adjacent continuous shots, the real final frame of Shot N is a better
continuity reference for Shot N+1 than the original storyboard.
"""

from typing import Protocol


class FrameExtractor(Protocol):
    async def extract_last_frame(self, video_bytes: bytes) -> bytes: ...
