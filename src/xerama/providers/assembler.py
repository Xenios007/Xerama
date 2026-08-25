"""Episode-assembly contract (MODULE-046, ADR-025).

Unlike image/video/voice generation, there is exactly one real "vendor"
here - FFmpeg itself - so this is a plain swappable Protocol (real/fake),
not a `MediaProviderRouter` capability pool.
"""

from typing import Protocol

from xerama.domain.assembly import AssemblyPlan


class AssemblerError(RuntimeError):
    """Raised when assembly fails - a missing FFmpeg dependency, a
    subprocess failure, or an unusable input file."""


class EpisodeAssembler(Protocol):
    async def assemble(
        self, plan: AssemblyPlan, inputs: dict[str, bytes]
    ) -> tuple[bytes, list[list[str]]]:
        """`inputs` maps every asset id referenced by `plan` (clips,
        audio tracks, subtitle) to its raw bytes - the caller resolves
        these via `AssetService`, this layer never touches storage.
        Returns `(rendered_bytes, ffmpeg_commands)` - the exact argv of
        every FFmpeg invocation used, for the render manifest."""
        ...
