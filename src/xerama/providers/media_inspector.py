"""Media-health inspection contract (MODULE-048, ADR-025).

ffprobe's job, not FFmpeg's: verify what a render *actually* produced
(duration, resolution, streams, corruption) independently of what the
encode step intended to produce - defense in depth beyond "the subprocess
returned exit code 0."
"""

from typing import Protocol

from xerama.domain.export import MediaProbeResult


class MediaInspector(Protocol):
    async def inspect(self, data: bytes) -> MediaProbeResult: ...
