import { useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { API_BASE_URL } from "../api/client";
import { useFinishedEpisodes, useProject } from "../api/queries";
import type { FinishedEpisode } from "../api/types";
import "./LibraryPage.css";

function formatSize(bytes: number | null): string {
  if (bytes === null) return "unknown size";
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "unknown length";
  return `${seconds.toFixed(0)}s`;
}

function EpisodeCard({ episode }: { episode: FinishedEpisode }) {
  const videoUrl = `${API_BASE_URL}${episode.download_url}`;
  return (
    <Card>
      <video className="xr-library__video" controls preload="metadata" src={videoUrl} />
      <div className="xr-library__meta">
        <strong>
          {episode.series_title} - Episode {episode.episode_number}
        </strong>
        <span className="xr-library__submeta">
          v{episode.version} - {formatDuration(episode.duration_seconds)} -{" "}
          {formatSize(episode.size_bytes)}
        </span>
        <code className="xr-library__path">{episode.friendly_path}</code>
        <a href={videoUrl} download className="xr-library__download">
          Download
        </a>
      </div>
    </Card>
  );
}

export function LibraryPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const project = useProject(projectId);
  const episodes = useFinishedEpisodes(projectId);

  return (
    <div>
      <h1>Finished episodes{project.data ? ` - ${project.data.name}` : ""}</h1>
      <p className="xr-library__intro">
        Every episode with an approved render, ready to preview or download. Files are also mirrored on
        disk under <code>storage/finished_videos/</code>.
      </p>
      <QueryState isLoading={episodes.isLoading} error={episodes.error}>
        {episodes.data?.length ? (
          <div className="xr-library__grid">
            {episodes.data.map((episode) => (
              <EpisodeCard key={episode.render_id} episode={episode} />
            ))}
          </div>
        ) : (
          <p>No finished episodes yet - approve a render from the Review &amp; Approval studio.</p>
        )}
      </QueryState>
    </div>
  );
}
