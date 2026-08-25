"""Versioned media evaluation dataset (MODULE-073).

Curated test shots covering the five shot classes the module requires:
identity, dialogue, motion, establishing, multi-character. Each case
declares which `MediaQCDimension`s (MODULE-044) matter for its class -
"record QC" reuses the exact same `MediaQCProvider` contract every real
production QC gate already goes through, not a second scoring system.
"""

from dataclasses import dataclass

from xerama.domain.asset import AssetType
from xerama.domain.enums import MediaQCDimension, ShotClass

DATASET_VERSION = "v1"


SHOT_CLASS_QC_DIMENSIONS: dict[ShotClass, tuple[MediaQCDimension, ...]] = {
    ShotClass.IDENTITY: (MediaQCDimension.IDENTITY,),
    ShotClass.DIALOGUE: (MediaQCDimension.IDENTITY, MediaQCDimension.COMPOSITION),
    ShotClass.MOTION: (MediaQCDimension.MOTION,),
    ShotClass.ESTABLISHING: (MediaQCDimension.COMPOSITION,),
    ShotClass.MULTI_CHARACTER: (MediaQCDimension.IDENTITY, MediaQCDimension.COMPOSITION),
}


@dataclass(frozen=True)
class MediaEvalCase:
    id: str
    shot_class: ShotClass
    asset_type: AssetType
    name: str
    prompt: str
    negative_prompt: str = ""
    # How many placeholder reference images this case supplies to the
    # provider - identity/multi-character cases need at least one
    # (there's a character to stay consistent with); establishing shots
    # need none.
    reference_image_count: int = 0
    duration_seconds: float = 5.0  # video cases only
    description: str = ""


IMAGE_CASES: list[MediaEvalCase] = [
    MediaEvalCase(
        id="image-identity-closeup",
        shot_class=ShotClass.IDENTITY,
        asset_type=AssetType.IMAGE,
        name="Character close-up against reference",
        prompt="Close-up of Mara, tear-streaked face, holding a letter, warm apartment lighting.",
        reference_image_count=2,
        description="Tests whether the generated face matches the character reference pack.",
    ),
    MediaEvalCase(
        id="image-dialogue-two-shot",
        shot_class=ShotClass.DIALOGUE,
        asset_type=AssetType.IMAGE,
        name="Two-person dialogue framing",
        prompt="Mara and her sister face each other across a kitchen table, mid-argument, "
        "over-the-shoulder framing.",
        reference_image_count=2,
        description="Tests dialogue-shot composition and identity for two characters.",
    ),
    MediaEvalCase(
        id="image-establishing-skyline",
        shot_class=ShotClass.ESTABLISHING,
        asset_type=AssetType.IMAGE,
        name="City skyline establishing shot",
        prompt="Wide establishing shot of a rain-soaked city skyline at dusk, neon reflections.",
        reference_image_count=0,
        description="No character reference needed - tests pure composition/framing quality.",
    ),
    MediaEvalCase(
        id="image-multi-character-ensemble",
        shot_class=ShotClass.MULTI_CHARACTER,
        asset_type=AssetType.IMAGE,
        name="Three-character ensemble shot",
        prompt="Three siblings standing together at a funeral, formal dress, overcast daylight.",
        reference_image_count=3,
        description="Tests identity consistency and composition across multiple characters at once.",
    ),
]

VIDEO_CASES: list[MediaEvalCase] = [
    MediaEvalCase(
        id="video-motion-chase",
        shot_class=ShotClass.MOTION,
        asset_type=AssetType.VIDEO,
        name="Running chase sequence",
        prompt="Mara sprints down a rain-slicked alley, camera tracking alongside her.",
        reference_image_count=1,
        duration_seconds=4.0,
        description="Tests motion coherence and physical plausibility under real movement.",
    ),
    MediaEvalCase(
        id="video-identity-turn",
        shot_class=ShotClass.IDENTITY,
        asset_type=AssetType.VIDEO,
        name="Character turns to camera",
        prompt="Mara turns from the window to face the camera, revealing her expression.",
        reference_image_count=2,
        duration_seconds=3.0,
        description="Tests identity consistency held across a moving/rotating shot, not just a still.",
    ),
]

_CASES_BY_ASSET_TYPE: dict[AssetType, list[MediaEvalCase]] = {
    AssetType.IMAGE: IMAGE_CASES,
    AssetType.VIDEO: VIDEO_CASES,
}


def cases_for_asset_type(asset_type: AssetType) -> list[MediaEvalCase]:
    return list(_CASES_BY_ASSET_TYPE.get(asset_type, []))
