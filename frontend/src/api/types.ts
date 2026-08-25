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

export interface EpisodeRecord {
  id: string;
  series_id: string;
  episode_number: number;
  status: string;
  version: number;
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
