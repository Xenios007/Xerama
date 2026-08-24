"""Rights/licensing metadata shared by Music (MODULE-037) and Sound Effect
(MODULE-038) cues - both need the exact same "prevent unlicensed/unknown
provenance assets from publish-ready state" gate, so it lives in one place
rather than being duplicated per cue type.
"""

from pydantic import BaseModel


class RightsMetadata(BaseModel):
    source: str = "library"  # "library" | "generated"
    license_type: str = ""  # e.g. "royalty_free", "licensed", "cc0" - empty/"unknown" blocks approval
    rights_owner: str = ""
    license_reference: str = ""

    @property
    def is_known(self) -> bool:
        return bool(self.license_type) and self.license_type != "unknown"
