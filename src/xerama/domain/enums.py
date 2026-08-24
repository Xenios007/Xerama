"""Shared enums for Xerama domain contracts.

Values are intentionally lowercase/snake_case strings so they serialize
identically in JSON schemas sent to LLMs and in persisted database rows.
"""

from enum import Enum


class ModelRole(str, Enum):
    """Logical AI worker roles. See docs/AI_MODELS.md.

    Application code requests a role; configuration resolves the role to a
    provider/model. Roles must never be replaced by hard-coded model IDs.
    """

    CONCEPT_GENERATOR_A = "concept_generator_a"
    CONCEPT_GENERATOR_B = "concept_generator_b"
    JUDGE = "judge"
    STORY_ARCHITECT = "story_architect"
    EPISODE_WRITER = "episode_writer"
    CONTINUITY_CHECKER = "continuity_checker"
    RETENTION_CRITIC = "retention_critic"
    SHOT_PLANNER = "shot_planner"
    SHOWRUNNER = "showrunner"


class ExecutionMode(str, Enum):
    """Planned execution modes. See docs/ARCHITECTURE.md section 13."""

    FAST = "fast"
    STANDARD = "standard"
    QUALITY = "quality"


class JudgeDecision(str, Enum):
    A = "A"
    B = "B"
    MERGE = "MERGE"


class JobStage(str, Enum):
    CONCEPT_GENERATION = "concept_generation"
    JUDGE = "judge"
    CONCEPT_MERGE = "concept_merge"
    SERIES_BIBLE = "series_bible"
    CHARACTERS = "characters"
    SEASON_PLAN = "season_plan"
    EPISODE_OUTLINES = "episode_outlines"
    EPISODE_SCRIPT = "episode_script"
    SCENE_SHOT_PLANNING = "scene_shot_planning"
    RETENTION_VALIDATION = "retention_validation"
    CONTINUITY_VALIDATION = "continuity_validation"
    CANON_COMMIT = "canon_commit"
    FULL_PIPELINE = "full_pipeline"


class JobStatus(str, Enum):
    """Minimum generation job states. See docs/ARCHITECTURE.md section 11."""

    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QCStatus(str, Enum):
    """Quality gate verdicts. See docs/DECISIONS.md ADR-018."""

    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class TruthStatus(str, Enum):
    TRUE = "true"
    FALSE = "false"
    AMBIGUOUS = "ambiguous"


class AwarenessStatus(str, Enum):
    """Per-party awareness of a knowledge fact. See docs/DATA_MODEL.md."""

    KNOWS = "knows"
    SUSPECTS = "suspects"
    BELIEVES_FALSE = "believes_false"
    UNKNOWN = "unknown"


class CliffhangerType(str, Enum):
    """See docs/STORY_FORMULA.md section 5."""

    IDENTITY_REVEAL = "identity_reveal"
    UNEXPECTED_ARRIVAL = "unexpected_arrival"
    BETRAYAL = "betrayal"
    DISCOVERY = "discovery"
    THREAT = "threat"
    POWER_REVERSAL = "power_reversal"
    INTERRUPTED_CONFESSION = "interrupted_confession"
    PHYSICAL_DANGER = "physical_danger"
    EXPOSED_SECRET = "exposed_secret"
    IMPOSSIBLE_CHOICE = "impossible_choice"
    FALSE_VICTORY = "false_victory"
    NEW_MYSTERY = "new_mystery"
    RELATIONSHIP_REVERSAL = "relationship_reversal"
    EVIDENCE_REVEAL = "evidence_reveal"
    COUNTDOWN_DEADLINE = "countdown_deadline"


class AudioMode(str, Enum):
    """See docs/ARCHITECTURE.md section 12."""

    NATIVE = "native"
    TTS_LIPSYNC = "tts_lipsync"
    HYBRID = "hybrid"


class ProductionPriority(str, Enum):
    """See MODULE-021 - Director Engine: "production priority per scene/
    shot." A router/scheduler can use this to sequence expensive media
    generation (e.g. hero shots before b-roll) once one exists
    (MODULE-041/042); purely informational until then."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ScreenPosition(str, Enum):
    """See MODULE-022 - lightweight left/center/right blocking, extensible
    to real coordinates later. Deliberately five positions, not a
    continuous axis - matches the module's "keep schema extensible to
    coordinates later" rather than building a full 3D engine now."""

    LEFT = "left"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    RIGHT = "right"


class BlockingDepth(str, Enum):
    """See MODULE-022 - depth relative to camera."""

    FOREGROUND = "foreground"
    MIDGROUND = "midground"
    BACKGROUND = "background"


class ProviderErrorKind(str, Enum):
    """See docs/ARCHITECTURE.md section 12 (Provider Health)."""

    AUTHENTICATION = "authentication"
    QUOTA = "quota"
    RATE_LIMIT = "rate_limit"
    PROVIDER_SATURATION = "provider_saturation"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    TRANSIENT_FAILURE = "transient_failure"
    UNKNOWN = "unknown"


class ThreadStatus(str, Enum):
    """Status of a season-level mystery or promise/payoff thread."""

    OPEN = "open"
    PARTIAL = "partial"
    RESOLVED = "resolved"


class SeasonPlanStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"


class ArcStage(str, Enum):
    """Where a character-arc milestone sits in a change arc."""

    SETUP = "setup"
    TEST = "test"
    CRISIS = "crisis"
    CHANGE = "change"
    RESOLUTION = "resolution"


class EpisodeGenerationStatus(str, Enum):
    """Per-episode generation progress. See modules/02_MULTI_EPISODE_ENGINE.md
    "Persist generation status per episode"."""

    OUTLINED = "outlined"
    SCRIPTED = "scripted"
    SHOT_PLANNED = "shot_planned"
    QC_BLOCKED = "qc_blocked"
    CANON_COMMITTED = "canon_committed"
    STALE = "stale"


class IdentityType(str, Enum):
    """See modules/05_CHARACTER_CASTING_STUDIO.md - the schema intentionally
    offers no "unlicensed real person" option, so an unauthorized
    celebrity-cloning workflow has no value to select here."""

    SYNTHETIC_ORIGINAL = "synthetic_original"
    LICENSED_AUTHORIZED = "licensed_authorized"


class CanonChangeType(str, Enum):
    """See docs/DATA_MODEL.md (Episode State Change)."""

    CHARACTER_LEARNS_FACT = "character_learns_fact"
    RELATIONSHIP_CHANGE = "relationship_change"
    SECRET_EXPOSED = "secret_exposed"
    INJURY_ADDED = "injury_added"
    INJURY_REMOVED = "injury_removed"
    CHARACTER_MOVES_LOCATION = "character_moves_location"
    PROP_OWNERSHIP_CHANGE = "prop_ownership_change"
    PROMISE_CREATED = "promise_created"
    PROMISE_PAID_OFF = "promise_paid_off"
