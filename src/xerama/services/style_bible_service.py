"""Style Bible service (Module 06, ADR-013).

Same lock/immutability pattern as `CharacterCastingService` (Module 05):
`locked=True` blocks edits until an explicit `unlock_for_recast`, which
bumps `version`. One Style Bible per series - a production anchor, not a
kept version history.
"""

from xerama.domain.style_bible import StyleBible
from xerama.repositories.interfaces import StyleBibleRepository


class StyleBibleService:
    def __init__(self, repo: StyleBibleRepository) -> None:
        self._repo = repo

    async def get_or_create(self, series_id: str) -> StyleBible:
        return await self._repo.get_or_create(series_id)

    async def update(
        self,
        series_id: str,
        style_asset_id: str | None = None,
        style_dna: str | None = None,
        palette: list[str] | None = None,
        lighting: str | None = None,
        texture: str | None = None,
        color_temperature: str | None = None,
        composition_rules: list[str] | None = None,
        negatives: list[str] | None = None,
    ) -> StyleBible:
        style_bible = await self.get_or_create(series_id)
        if style_bible.locked:
            raise PermissionError(
                f"style bible for series {series_id} is locked - call unlock_for_recast first"
            )
        if style_asset_id is not None:
            style_bible.style_asset_id = style_asset_id
        if style_dna is not None:
            style_bible.style_dna = style_dna
        if palette is not None:
            style_bible.palette = palette
        if lighting is not None:
            style_bible.lighting = lighting
        if texture is not None:
            style_bible.texture = texture
        if color_temperature is not None:
            style_bible.color_temperature = color_temperature
        if composition_rules is not None:
            style_bible.composition_rules = composition_rules
        if negatives is not None:
            style_bible.negatives = negatives
        return await self._repo.save(style_bible)

    async def lock(self, series_id: str) -> StyleBible:
        await self.get_or_create(series_id)
        return await self._repo.set_lock(series_id, locked=True)

    async def unlock_for_recast(self, series_id: str) -> StyleBible:
        await self.get_or_create(series_id)
        return await self._repo.unlock_and_bump_version(series_id)
