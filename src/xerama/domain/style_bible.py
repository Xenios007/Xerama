"""Style Bible domain contract (Module 06, ADR-013).

"Each production should have an approved canonical Style Bible frame/
textual style description before bulk generation. Visual QC can compare
shots against this anchor and retry style-drift failures." One row per
series - a production anchor, not a versioned-history record. Locking
follows the same immutability pattern as `Character` (Module 05):
`locked=True` blocks further edits until an explicit recast.
"""

from pydantic import BaseModel, Field


class StyleBible(BaseModel):
    id: str
    series_id: str
    style_asset_id: str | None = None
    style_dna: str = ""
    palette: list[str] = Field(default_factory=list)
    lighting: str = ""
    texture: str = ""
    color_temperature: str = ""
    composition_rules: list[str] = Field(default_factory=list)
    negatives: list[str] = Field(default_factory=list)
    locked: bool = False
    version: int = 1
