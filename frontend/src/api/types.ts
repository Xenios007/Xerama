/**
 * Types mirroring the Xerama backend's Pydantic response models
 * (src/xerama/repositories/interfaces.py, src/xerama/domain/*.py).
 *
 * Hand-maintained rather than codegen'd for MODULE-055's initial shell -
 * revisit with an OpenAPI-generated client once the schema stabilizes
 * across more of modules 056-060's pages.
 */

export interface ProjectRecord {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
}

export interface EpisodeStatusSummary {
  id: string;
  episode_number: number;
  status: string;
  current_render_version: number | null;
}

export interface SeriesStatusSummary {
  id: string;
  title: string;
  status: string;
  episodes: EpisodeStatusSummary[];
}

export interface ProjectStatusResponse {
  project: ProjectRecord;
  series: SeriesStatusSummary[];
}

export interface CreativeBrief {
  genre: string;
  premise?: string;
  target_audience?: string;
  episode_count?: number;
  episode_duration_seconds?: number;
  tone?: string;
}

export interface GenerateSeriesResult {
  series_id: string;
  episode1_id: string;
}

export interface SeriesRecord {
  id: string;
  project_id: string;
  title: string;
  logline: string;
  genre: string[];
  target_audience: string;
  episode_count_target: number;
  episode_duration_target_seconds: number;
  status: string;
}

export interface SeriesBible {
  title: string;
  logline: string;
  premise: string;
  emotional_engine: string;
  central_dramatic_question: string;
}

export interface EpisodeRecord {
  id: string;
  series_id: string;
  episode_number: number;
  status: string;
  version: number;
}

export interface EpisodeGenerationResult {
  episode_id: string;
  episode_number: number;
  version: number;
  retention_qc: QCResult;
  continuity_qc: QCResult;
  canon_committed: boolean;
}

export type QCStatus = "pass" | "warn" | "block";

export interface QCResult {
  gate: string;
  status: QCStatus;
  score: number;
  reasons: string[];
  repair_recommendation: string;
}

export interface SeasonPlanRecord {
  id: string;
  series_id: string;
  version: number;
  status: string;
  qc_status: string;
  qc_score: number;
  qc_reasons: string[];
}

export interface ConceptCandidateRecord {
  id: string;
  batch_id: string;
  slot: string;
  provider: string;
  model: string;
  accepted: boolean;
  candidate: { title: string; logline: string };
  created_at: string;
}

export interface JudgeDecisionRecord {
  id: string;
  batch_id: string;
  decision: string;
  provider: string;
  model: string;
  approved_concept: { title: string };
  created_at: string;
}

export interface CanonEvent {
  change_type: string;
  episode_number: number;
  description: string;
  committed: boolean;
}

export interface CharacterDNA {
  eyes?: string;
  hair?: string;
  build?: string;
  distinguishing_features?: string;
}

export interface CharacterProvenance {
  identity_type: "synthetic_original" | "licensed_authorized";
  consent_reference: string;
  notes: string;
}

export interface Character {
  id: string;
  name: string;
  role: string;
  age: string;
  description: string;
  personality: string;
  character_dna: CharacterDNA;
  visual_identity_id: string | null;
  voice_identity_id: string | null;
  reference_pack: Record<string, string>;
  identity_provenance: CharacterProvenance;
  locked: boolean;
  version: number;
}

export interface CharacterCast {
  characters: Character[];
}

export interface WardrobeVariant {
  id: string;
  character_id: string;
  label: string;
  reference_asset_ids: string[];
  description: string;
}

export type PhysicalStateVariant = WardrobeVariant;

export type AudioMode = "native" | "tts_lipsync" | "hybrid";

export interface Shot {
  shot_number: number;
  scene_number: number;
  narrative_function: string;
  character_ids: string[];
  dialogue: string;
  duration_seconds: number;
  audio_mode: AudioMode;
  continuity_group: string | null;
}

export interface Scene {
  scene_number: number;
  location: string;
  shots: Shot[];
}

export interface EpisodeShotPlan {
  episode_number: number;
  scenes: Scene[];
}

export interface Storyboard {
  id: string;
  episode_id: string;
  scene_number: number;
  shot_number: number;
  status: string;
  approved_keyframe_asset_id: string | null;
}

export interface ShotVideoProduction {
  id: string;
  episode_id: string;
  scene_number: number;
  shot_number: number;
  status: string;
  approved_take_asset_id: string | null;
}

export interface ShotAudioProduction {
  id: string;
  episode_id: string;
  scene_number: number;
  shot_number: number;
  audio_mode: string;
  status: string;
  approved_take_asset_id: string | null;
}

export interface VoiceProfile {
  id: string;
  character_id: string;
  provider: string;
  provider_voice_id: string;
  language: string;
  style: string;
  locked: boolean;
  version: number;
  provenance: CharacterProvenance;
}

export type AssetType = "image" | "video" | "audio" | "subtitle" | "document" | "other";
export type AssetStatus = "pending" | "accepted" | "rejected";

export interface Asset {
  id: string;
  type: AssetType;
  status: AssetStatus;
  storage_path: string;
  content_hash: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  take_number: number;
  rejection_reason: string;
  created_at: string;
}

export type JobStatus = "queued" | "running" | "retrying" | "succeeded" | "failed" | "cancelled";

export interface JobRecord {
  id: string;
  project_id: string;
  stage: string;
  status: JobStatus;
  provider: string;
  model: string;
  attempt: number;
  error: string;
  result_asset_ids: string[];
}

export interface ObservabilitySnapshot {
  queue_depth: number;
  stage_durations: { stage: string; sample_count: number; average_seconds: number }[];
  provider_reliability: {
    provider: string;
    attempt_count: number;
    failure_count: number;
    retry_count: number;
  }[];
}

export interface AcceptedOutputCost {
  unit: string;
  total_known_cost_usd: number;
  unknown_cost_attempts: number;
  accepted_quantity: number;
  cost_per_accepted_unit_usd: number | null;
}

export interface CostSummaryResponse {
  image: AcceptedOutputCost;
  video: AcceptedOutputCost;
  cost_by_episode_usd: Record<string, number>;
}
