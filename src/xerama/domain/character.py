"""Character, relationship and knowledge-state contracts.

See docs/DATA_MODEL.md and research/CHARACTER_CONTINUITY_PLAYBOOK.md.

XER-001 only generates the textual/structural layer (no image/voice
generation yet). The schema still carries the identity fields described in
ADR-012 / ADR-013 so later media stages do not require a redesign.
"""

from pydantic import BaseModel, Field, model_validator

from xerama.domain.enums import AwarenessStatus, IdentityType, TruthStatus


class CharacterDNA(BaseModel):
    """Compact, provider-independent visual signature.

    See research/CHARACTER_CONTINUITY_PLAYBOOK.md "Character DNA". Populated
    once a root reference image exists; all fields are optional in XER-001
    because no image generation has run yet.
    """

    eyes: str = ""
    face_shape: str = ""
    nose: str = ""
    mouth: str = ""
    hairstyle: str = ""
    hair_color: str = ""
    skin_tone: str = ""
    signature_outfit: str = ""


def format_character_dna(character: "Character") -> str:
    """Compact DNA text for prompt injection. Shared by `PromptCompiler` and
    `ConsistencyPolicy` so identity phrasing never drifts between the two -
    see research/CHARACTER_CONTINUITY_PLAYBOOK.md "Character DNA"."""

    dna = character.character_dna
    parts = [
        p
        for p in (
            dna.eyes,
            dna.face_shape,
            dna.nose,
            dna.mouth,
            dna.hairstyle,
            dna.hair_color,
            dna.skin_tone,
            dna.signature_outfit,
        )
        if p
    ]
    signature = ", ".join(parts) if parts else character.description
    return f"{character.name}: {signature}" if signature else character.name


class CharacterProvenance(BaseModel):
    """Identity provenance/consent metadata - see
    modules/05_CHARACTER_CASTING_STUDIO.md "Do not implement unauthorized
    celebrity-cloning workflows." `IdentityType` deliberately has no
    "unlicensed real person" value, so that workflow cannot be represented
    here at all; a licensed identity must additionally record what it was
    licensed under."""

    identity_type: IdentityType = IdentityType.SYNTHETIC_ORIGINAL
    consent_reference: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _licensed_requires_consent_reference(self) -> "CharacterProvenance":
        if self.identity_type == IdentityType.LICENSED_AUTHORIZED and not self.consent_reference:
            raise ValueError(
                "identity_type=licensed_authorized requires a non-empty consent_reference"
            )
        return self


class WardrobeVariant(BaseModel):
    """A versioned outfit asset - see playbook "Wardrobe as assets": episode
    state points to an asset ID rather than prompting "same clothes as
    before"."""

    id: str
    character_id: str
    label: str
    reference_asset_ids: list[str] = Field(default_factory=list)
    description: str = ""


class PhysicalStateVariant(BaseModel):
    """A versioned physical-state asset (injured, wet, aged/time-jump, ...)
    - see playbook "Physical State"."""

    id: str
    character_id: str
    label: str
    reference_asset_ids: list[str] = Field(default_factory=list)
    description: str = ""


class Character(BaseModel):
    """See docs/DATA_MODEL.md Character."""

    id: str
    name: str
    role: str
    age: str = ""
    description: str = ""
    personality: str = ""
    goal: str = ""
    fear: str = ""
    flaw: str = ""
    secret: str = ""
    character_dna: CharacterDNA = Field(default_factory=CharacterDNA)
    visual_identity_id: str | None = None
    voice_identity_id: str | None = None
    # Multi-view reference pack: view name (front/three_quarter/side/
    # full_body/expression_neutral/...) -> Asset id. See playbook
    # "Reference pack".
    reference_pack: dict[str, str] = Field(default_factory=dict)
    identity_provenance: CharacterProvenance = Field(default_factory=CharacterProvenance)
    # Once locked, root identity (visual_identity_id/reference_pack/
    # character_dna/identity_provenance) is immutable - see playbook "Never
    # generate a recurring character from scratch once the identity is
    # approved." `version` increments only on an explicit deliberate recast
    # (unlock), mirroring the Episode.version precedent from Module 02.
    locked: bool = False
    version: int = 1
    status: str = "active"


class RelationshipState(BaseModel):
    """Versionable relationship state. See docs/DATA_MODEL.md Relationship."""

    source_character_id: str
    target_character_id: str
    relationship_type: str
    public_status: str = ""
    private_status: str = ""
    trust_level: float = Field(default=0.5, ge=0, le=1)
    romantic_state: str = ""
    valid_from_episode: int = 1
    valid_to_episode: int | None = None


class KnowledgeState(BaseModel):
    """Per-party awareness of a single fact. See docs/DATA_MODEL.md Knowledge State."""

    audience: AwarenessStatus = AwarenessStatus.UNKNOWN
    characters: dict[str, AwarenessStatus] = Field(default_factory=dict)


class CanonFact(BaseModel):
    """A trackable story fact and who knows it. See docs/DATA_MODEL.md."""

    id: str
    statement: str
    truth_status: TruthStatus = TruthStatus.TRUE
    importance: float = Field(default=0.5, ge=0, le=1)
    introduced_episode: int | None = None
    planned_reveal_episode: int | None = None
    actual_reveal_episode: int | None = None
    knowledge: KnowledgeState = Field(default_factory=KnowledgeState)


class CharacterCast(BaseModel):
    """AI generation output for the character-creation stage."""

    characters: list[Character]
    relationships: list[RelationshipState] = Field(default_factory=list)
