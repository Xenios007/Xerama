import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { ApiError } from "../api/client";
import { useGenerateSeries, useJobs, useProjectObservability, useProjectStatus } from "../api/queries";

function StartSeriesForm({ projectId }: { projectId: string }) {
  const generateSeries = useGenerateSeries(projectId);
  const [genre, setGenre] = useState("thriller");
  const [episodeCount, setEpisodeCount] = useState(3);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    generateSeries.mutate({ genre, episode_count: episodeCount, episode_duration_seconds: 75 });
  }

  return (
    <Card title="Start a series">
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <input value={genre} onChange={(e) => setGenre(e.target.value)} aria-label="Genre" placeholder="Genre" />
        <input
          type="number"
          min={1}
          max={100}
          value={episodeCount}
          onChange={(e) => setEpisodeCount(Number(e.target.value))}
          aria-label="Episode count"
          style={{ width: "4rem" }}
        />
        <Button type="submit" disabled={generateSeries.isPending}>
          {generateSeries.isPending ? "Generating…" : "Generate series"}
        </Button>
      </form>
      {generateSeries.isError && (
        <p style={{ color: "var(--xr-color-danger, #dc2626)" }}>
          {generateSeries.error instanceof ApiError
            ? generateSeries.error.detail
            : "Series generation failed."}
        </p>
      )}
    </Card>
  );
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const status = useProjectStatus(projectId);
  const observability = useProjectObservability(projectId);
  const jobs = useJobs(projectId);

  return (
    <div>
      <h1>Project</h1>
      <QueryState isLoading={status.isLoading} error={status.error}>
        {status.data && (
          <>
            <Card title={status.data.project.name}>
              <p>{status.data.project.description || "No description."}</p>
              <p>Status: {status.data.project.status}</p>
            </Card>
            <div style={{ marginTop: "1rem" }}>
              {status.data.series.length === 0 ? (
                projectId && <StartSeriesForm projectId={projectId} />
              ) : (
                <Card title="Series">
                  {status.data.series.map((series) => (
                    <div key={series.id} style={{ marginBottom: "0.75rem" }}>
                      <Link to={`/story/${series.id}`}>
                        <strong>{series.title}</strong>
                      </Link>{" "}
                      - {series.status} ·{" "}
                      <Link to={`/characters/${series.id}`}>Cast</Link>
                      <ul>
                        {series.episodes.map((episode) => (
                          <li key={episode.id}>
                            Episode {episode.episode_number}: {episode.status}
                            {episode.current_render_version != null &&
                              ` (render v${episode.current_render_version})`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </Card>
              )}
            </div>
          </>
        )}
      </QueryState>

      <div style={{ marginTop: "1rem" }}>
        <Card title="Production activity">
          <QueryState isLoading={observability.isLoading} error={observability.error}>
            {observability.data && (
              <p>
                Queue depth: {observability.data.queue_depth} · Providers tracked:{" "}
                {observability.data.provider_reliability.length}
              </p>
            )}
          </QueryState>
          <QueryState isLoading={jobs.isLoading} error={jobs.error}>
            {jobs.data && <p>{jobs.data.length} job(s) recorded for this project.</p>}
          </QueryState>
        </Card>
      </div>
    </div>
  );
}
