import { Link, useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { ApiError } from "../api/client";
import type { QCResult } from "../api/types";
import {
  useApproveSeasonPlan,
  useCanonEvents,
  useConceptCandidates,
  useGenerateNextEpisode,
  useJudgeDecisions,
  useSeasonPlan,
  useSeries,
  useSeriesBible,
  useSeriesEpisodes,
} from "../api/queries";
import "./StoryStudioPage.css";

function QcBadge({ result }: { result: QCResult }) {
  return (
    <span className={`xr-qc xr-qc--${result.status}`} title={result.reasons.join("; ")}>
      {result.gate}: {result.status} ({result.score.toFixed(1)})
    </span>
  );
}

function ConceptLineage({ projectId }: { projectId: string }) {
  const candidates = useConceptCandidates(projectId);
  const decisions = useJudgeDecisions(projectId);

  return (
    <Card title="Concept lineage">
      <QueryState isLoading={candidates.isLoading} error={candidates.error}>
        {candidates.data?.length ? (
          <ul>
            {candidates.data.map((c) => (
              <li key={c.id}>
                [{c.slot}] {c.candidate.title} {c.accepted && "✓ accepted"}
              </li>
            ))}
          </ul>
        ) : (
          <p>No candidates recorded.</p>
        )}
      </QueryState>
      <QueryState isLoading={decisions.isLoading} error={decisions.error}>
        {decisions.data?.map((d) => (
          <p key={d.id}>
            Judge decision: <strong>{d.decision}</strong> - approved "{d.approved_concept.title}"
          </p>
        ))}
      </QueryState>
    </Card>
  );
}

function SeasonPlanPanel({ seriesId }: { seriesId: string }) {
  const seasonPlan = useSeasonPlan(seriesId);
  const approve = useApproveSeasonPlan(seriesId);

  return (
    <Card title="Season plan">
      <QueryState isLoading={seasonPlan.isLoading} error={seasonPlan.error}>
        {seasonPlan.data && (
          <>
            <p>
              Version {seasonPlan.data.version} - {seasonPlan.data.status} (QC:{" "}
              {seasonPlan.data.qc_status})
            </p>
            {seasonPlan.data.qc_reasons.length > 0 && (
              <ul>
                {seasonPlan.data.qc_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {seasonPlan.data.status !== "approved" && (
              <Button onClick={() => approve.mutate(seasonPlan.data!.version)} disabled={approve.isPending}>
                Approve
              </Button>
            )}
          </>
        )}
      </QueryState>
    </Card>
  );
}

function EpisodesPanel({ projectId, seriesId }: { projectId: string; seriesId: string }) {
  const episodes = useSeriesEpisodes(seriesId);
  const generateNext = useGenerateNextEpisode(projectId, seriesId);

  return (
    <Card title="Episodes">
      <QueryState isLoading={episodes.isLoading} error={episodes.error}>
        {episodes.data?.length ? (
          <ul className="xr-story__episode-list">
            {episodes.data.map((episode) => (
              <li key={episode.id}>
                <Link to={`/production/${episode.id}`}>Episode {episode.episode_number}</Link>:{" "}
                {episode.status} (v{episode.version})
              </li>
            ))}
          </ul>
        ) : (
          <p>No episodes yet.</p>
        )}
      </QueryState>
      <Button onClick={() => generateNext.mutate()} disabled={generateNext.isPending}>
        {generateNext.isPending ? "Generating…" : "Generate next episode"}
      </Button>
      {generateNext.isError && (
        <p style={{ color: "var(--xr-color-danger, #dc2626)" }}>
          {generateNext.error instanceof ApiError ? generateNext.error.detail : "Generation failed."}
        </p>
      )}
      {generateNext.data && (
        <div className="xr-story__qc-row">
          <QcBadge result={generateNext.data.retention_qc} />
          <QcBadge result={generateNext.data.continuity_qc} />
          <span>{generateNext.data.canon_committed ? "Canon committed" : "Canon not committed"}</span>
        </div>
      )}
    </Card>
  );
}

function CanonPanel({ seriesId }: { seriesId: string }) {
  const canonEvents = useCanonEvents(seriesId);
  return (
    <Card title="Canon state">
      <QueryState isLoading={canonEvents.isLoading} error={canonEvents.error}>
        {canonEvents.data?.length ? (
          <ul>
            {canonEvents.data.map((event, index) => (
              <li key={index}>
                Ep {event.episode_number} - {event.change_type}: {event.description}
              </li>
            ))}
          </ul>
        ) : (
          <p>No committed canon events yet.</p>
        )}
      </QueryState>
    </Card>
  );
}

export function StoryStudioPage() {
  const { seriesId } = useParams<{ seriesId: string }>();
  const series = useSeries(seriesId);
  const bible = useSeriesBible(seriesId);

  return (
    <div>
      <h1>Story Studio</h1>
      <QueryState isLoading={series.isLoading} error={series.error}>
        {series.data && (
          <>
            <Card title={series.data.title}>
              <p>{series.data.logline}</p>
              <p>Status: {series.data.status}</p>
            </Card>
            <div className="xr-story__grid">
              <Card title="Series Bible">
                <QueryState isLoading={bible.isLoading} error={bible.error}>
                  {bible.data && (
                    <>
                      <p>{bible.data.premise}</p>
                      <p>
                        <em>{bible.data.central_dramatic_question}</em>
                      </p>
                    </>
                  )}
                </QueryState>
              </Card>
              <ConceptLineage projectId={series.data.project_id} />
              <SeasonPlanPanel seriesId={series.data.id} />
              <EpisodesPanel projectId={series.data.project_id} seriesId={series.data.id} />
              <CanonPanel seriesId={series.data.id} />
            </div>
          </>
        )}
      </QueryState>
    </div>
  );
}
