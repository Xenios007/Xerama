import { useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { useJobs, useProjectObservability, useProjectStatus } from "../api/queries";

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
              <Card title="Series">
                {status.data.series.length === 0 ? (
                  <p>No series generated yet.</p>
                ) : (
                  status.data.series.map((series) => (
                    <div key={series.id} style={{ marginBottom: "0.75rem" }}>
                      <strong>{series.title}</strong> - {series.status}
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
                  ))
                )}
              </Card>
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
