import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { ApiError } from "../api/client";
import type { AudioMode, Shot } from "../api/types";
import {
  useAudioProductions,
  useEpisode,
  useEpisodeShotPlan,
  useGenerateAudioTake,
  useGenerateKeyframe,
  useGenerateVideoTake,
  useJobs,
  useSeries,
  useStoryboards,
  useVideoProductions,
} from "../api/queries";
import "./ProductionStudioPage.css";

type MediumStatus = "not_started" | "draft" | "approved";

function statusOf(record: { status: string } | undefined): MediumStatus {
  if (!record) return "not_started";
  return record.status === "approved" ? "approved" : "draft";
}

function StatusBadge({ label, status }: { label: string; status: MediumStatus }) {
  return <span className={`xr-medium xr-medium--${status}`}>{label}: {status.replace("_", " ")}</span>;
}

interface ShotRowProps {
  episodeId: string;
  shot: Shot;
  storyboardStatus: MediumStatus;
  videoStatus: MediumStatus;
  audioStatus: MediumStatus;
}

function ShotRow({ episodeId, shot, storyboardStatus, videoStatus, audioStatus }: ShotRowProps) {
  const generateKeyframe = useGenerateKeyframe(episodeId);
  const generateVideo = useGenerateVideoTake(episodeId);
  const generateAudio = useGenerateAudioTake(episodeId);
  const needsAudio: AudioMode[] = ["tts_lipsync", "hybrid"];
  const busy = generateKeyframe.isPending || generateVideo.isPending || generateAudio.isPending;
  const error = generateKeyframe.error ?? generateVideo.error ?? generateAudio.error;

  const coords = { sceneNumber: shot.scene_number, shotNumber: shot.shot_number };

  return (
    <div className="xr-shot-row">
      <div className="xr-shot-row__header">
        <strong>
          Scene {shot.scene_number} / Shot {shot.shot_number}
        </strong>
        <span className="xr-shot-row__function">{shot.narrative_function}</span>
      </div>
      <div className="xr-shot-row__statuses">
        <StatusBadge label="Storyboard" status={storyboardStatus} />
        <StatusBadge label="Video" status={videoStatus} />
        {needsAudio.includes(shot.audio_mode) && <StatusBadge label="Audio" status={audioStatus} />}
      </div>
      <div className="xr-shot-row__actions">
        <Button
          variant="secondary"
          disabled={busy || storyboardStatus === "approved"}
          onClick={() => generateKeyframe.mutate(coords)}
        >
          {storyboardStatus === "approved" ? "Keyframe ✓" : "Generate keyframe"}
        </Button>
        <Button
          variant="secondary"
          disabled={busy || videoStatus === "approved" || storyboardStatus !== "approved"}
          onClick={() => generateVideo.mutate(coords)}
        >
          {videoStatus === "approved" ? "Video ✓" : "Generate video"}
        </Button>
        {needsAudio.includes(shot.audio_mode) && (
          <Button
            variant="secondary"
            disabled={busy || audioStatus === "approved" || !shot.character_ids[0]}
            onClick={() =>
              shot.character_ids[0] &&
              generateAudio.mutate({ ...coords, characterId: shot.character_ids[0] })
            }
          >
            {audioStatus === "approved" ? "Audio ✓" : "Generate audio"}
          </Button>
        )}
      </div>
      {error && (
        <p className="xr-shot-row__error">{error instanceof ApiError ? error.detail : "Generation failed."}</p>
      )}
    </div>
  );
}

export function ProductionStudioPage() {
  const { episodeId } = useParams<{ episodeId: string }>();
  const episode = useEpisode(episodeId);
  const series = useSeries(episode.data?.series_id);
  const shotPlan = useEpisodeShotPlan(episodeId);
  const storyboards = useStoryboards(episodeId);
  const videoProductions = useVideoProductions(episodeId);
  const audioProductions = useAudioProductions(episodeId);
  const jobs = useJobs(series.data?.project_id);
  const [filter, setFilter] = useState<"all" | "waiting" | "complete">("all");

  const storyboardByKey = useMemo(
    () => new Map((storyboards.data ?? []).map((s) => [`${s.scene_number}.${s.shot_number}`, s])),
    [storyboards.data],
  );
  const videoByKey = useMemo(
    () => new Map((videoProductions.data ?? []).map((v) => [`${v.scene_number}.${v.shot_number}`, v])),
    [videoProductions.data],
  );
  const audioByKey = useMemo(
    () => new Map((audioProductions.data ?? []).map((a) => [`${a.scene_number}.${a.shot_number}`, a])),
    [audioProductions.data],
  );

  const shots = (shotPlan.data?.scenes ?? []).flatMap((scene) => scene.shots);

  const rows = shots.map((shot) => {
    const key = `${shot.scene_number}.${shot.shot_number}`;
    return {
      shot,
      storyboardStatus: statusOf(storyboardByKey.get(key)),
      videoStatus: statusOf(videoByKey.get(key)),
      audioStatus: statusOf(audioByKey.get(key)),
    };
  });

  const filteredRows = rows.filter((row) => {
    if (filter === "all") return true;
    const needsAudio = row.shot.audio_mode !== "native";
    const complete =
      row.storyboardStatus === "approved" &&
      row.videoStatus === "approved" &&
      (!needsAudio || row.audioStatus === "approved");
    return filter === "complete" ? complete : !complete;
  });

  return (
    <div>
      <h1>Production Studio</h1>
      <QueryState isLoading={episode.isLoading} error={episode.error}>
        {episode.data && (
          <Card>
            <p>
              Episode {episode.data.episode_number} - {episode.data.status}
            </p>
          </Card>
        )}
      </QueryState>

      <div className="xr-production__filters">
        <Button variant={filter === "all" ? "primary" : "secondary"} onClick={() => setFilter("all")}>
          All ({rows.length})
        </Button>
        <Button
          variant={filter === "waiting" ? "primary" : "secondary"}
          onClick={() => setFilter("waiting")}
        >
          Waiting
        </Button>
        <Button
          variant={filter === "complete" ? "primary" : "secondary"}
          onClick={() => setFilter("complete")}
        >
          Complete
        </Button>
      </div>

      <QueryState isLoading={shotPlan.isLoading} error={shotPlan.error}>
        {episodeId && filteredRows.length > 0 ? (
          <div className="xr-production__list">
            {filteredRows.map((row) => (
              <ShotRow
                key={`${row.shot.scene_number}.${row.shot.shot_number}`}
                episodeId={episodeId}
                shot={row.shot}
                storyboardStatus={row.storyboardStatus}
                videoStatus={row.videoStatus}
                audioStatus={row.audioStatus}
              />
            ))}
          </div>
        ) : (
          <p>No shots match this filter.</p>
        )}
      </QueryState>

      <div style={{ marginTop: "1rem" }}>
        <Card title="Recent jobs">
          <QueryState isLoading={jobs.isLoading} error={jobs.error}>
            {jobs.data?.length ? (
              <ul>
                {jobs.data.slice(0, 10).map((job) => (
                  <li key={job.id}>
                    {job.stage}: {job.status} {job.provider && `(${job.provider}/${job.model})`}
                    {job.error && ` - ${job.error}`}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No jobs recorded yet.</p>
            )}
          </QueryState>
        </Card>
      </div>
    </div>
  );
}
