"""Character, relationship and knowledge-state contracts.

See docs/DATA_MODEL.md and research/CHARACTER_CONTINUITY_PLAYBOOK.md.

XER-001 only generates the textual/structural layer (no image/voice
generation yet). The schema still carries the identity fields described in
ADR-012 / ADR-013 so later media stages do not require a redesign.
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import AwarenessStatus, TruthStatus


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
