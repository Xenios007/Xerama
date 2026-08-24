from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.ffmpeg_frame_extractor import FFmpegFrameExtractor


async def test_fake_frame_extractor_returns_deterministic_marker() -> None:
    extractor = FakeFrameExtractor()
    frame = await extractor.extract_last_frame(b"some video bytes")
    assert frame == b"fake-last-frame:some video bytes"
    assert extractor.calls == [b"some video bytes"]


def test_ffmpeg_frame_extractor_constructs_with_default_binary_name() -> None:
    extractor = FFmpegFrameExtractor()
    assert extractor._ffmpeg_path == "ffmpeg"  # noqa: SLF001


def test_ffmpeg_frame_extractor_accepts_custom_binary_path() -> None:
    extractor = FFmpegFrameExtractor(ffmpeg_path="/usr/local/bin/ffmpeg")
    assert extractor._ffmpeg_path == "/usr/local/bin/ffmpeg"  # noqa: SLF001
