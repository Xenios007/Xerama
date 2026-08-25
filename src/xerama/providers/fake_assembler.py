"""In-memory fake `EpisodeAssembler` for tests/local runs without a real
`ffmpeg` binary - same "record calls, return a deterministic placeholder"
pattern as every other fake provider in this codebase."""

from xerama.domain.assembly import AssemblyPlan


class FakeAssembler:
    def __init__(self) -> None:
        self.calls: list[AssemblyPlan] = []

    async def assemble(
        self, plan: AssemblyPlan, inputs: dict[str, bytes]
    ) -> tuple[bytes, list[list[str]]]:
        self.calls.append(plan)
        marker = f"fake-render:{plan.episode_id}:clips={len(plan.clips)}:audio={len(plan.audio_tracks)}"
        commands = [["ffmpeg", "-fake-assemble", plan.episode_id]]
        return marker.encode(), commands
