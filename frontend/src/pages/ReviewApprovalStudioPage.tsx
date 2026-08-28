import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import type { Asset, EpisodeRender } from "../api/types";
import {
  useAcceptAsset,
  useApproveEpisodeRender,
  useAssetQc,
  useEpisodeRenders,
  usePendingAssets,
  useProjectStatus,
  useRejectAsset,
} from "../api/queries";
import "./ReviewApprovalStudioPage.css";

function QcEvidence({ assetId }: { assetId: string }) {
  const qc = useAssetQc(assetId);
  return (
    <QueryState isLoading={qc.isLoading} error={qc.error}>
      {qc.data?.length ? (
        <ul className="xr-review__qc-list">
          {qc.data.map((attempt) => (
            <li key={attempt.id} className={`xr-qc xr-qc--${attempt.status}`}>
              {attempt.dimension}: {attempt.status} ({attempt.score.toFixed(1)})
              {attempt.reasons.length > 0 && <> - {attempt.reasons.join("; ")}</>}
              {attempt.repair_recommendation && (
                <div className="xr-review__recommendation">→ {attempt.repair_recommendation}</div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p>No QC attempts recorded for this asset.</p>
      )}
    </QueryState>
  );
}

function PendingAssetRow({ asset }: { asset: Asset }) {
  const [expanded, setExpanded] = useState(false);
  const [reason, setReason] = useState("");
  const acceptAsset = useAcceptAsset();
  const rejectAsset = useRejectAsset();

  return (
    <div className="xr-review__row">
      <div className="xr-review__row-header">
        <span>
          {asset.type} take {asset.take_number}
        </span>
        <button className="xr-review__toggle" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Hide QC" : "Show QC"}
        </button>
      </div>
      {expanded && <QcEvidence assetId={asset.id} />}
      <div className="xr-review__actions">
        <Button onClick={() => acceptAsset.mutate(asset.id)} disabled={acceptAsset.isPending}>
          Approve
        </Button>
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for rejection / retake"
          aria-label={`Rejection reason for ${asset.id}`}
        />
        <Button
          variant="danger"
          disabled={rejectAsset.isPending || !reason.trim()}
          onClick={() => rejectAsset.mutate({ assetId: asset.id, reason: reason.trim() })}
        >
          Reject / request retake
        </Button>
      </div>
    </div>
  );
}

function RenderVersionRow({ render, projectId }: { render: EpisodeRender; projectId?: string }) {
  const approve = useApproveEpisodeRender();
  return (
    <div className="xr-review__row">
      <span>
        v{render.version} - {render.status}
      </span>
      {render.status !== "approved" ? (
        <Button onClick={() => approve.mutate(render.id)} disabled={approve.isPending}>
          Approve for publish
        </Button>
      ) : (
        projectId && <Link to={`/library/${projectId}`}>Find it in the Library →</Link>
      )}
    </div>
  );
}

function EpisodePublishPanel({ episodeId, projectId }: { episodeId: string; projectId?: string }) {
  const renders = useEpisodeRenders(episodeId);
  return (
    <QueryState isLoading={renders.isLoading} error={renders.error}>
      {renders.data?.length ? (
        renders.data.map((render) => (
          <RenderVersionRow key={render.id} render={render} projectId={projectId} />
        ))
      ) : (
        <p>No renders yet for this episode.</p>
      )}
    </QueryState>
  );
}

export function ReviewApprovalStudioPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const pending = usePendingAssets(projectId);
  const status = useProjectStatus(projectId);

  return (
    <div>
      <h1>Review &amp; Approval</h1>
      <Card title={`Awaiting review (${pending.data?.length ?? 0})`}>
        <QueryState isLoading={pending.isLoading} error={pending.error}>
          {pending.data?.length ? (
            pending.data.map((asset) => <PendingAssetRow key={asset.id} asset={asset} />)
          ) : (
            <p>Nothing waiting on human review.</p>
          )}
        </QueryState>
      </Card>

      <div style={{ marginTop: "1rem" }}>
        <Card title="Episode publish approval">
          <QueryState isLoading={status.isLoading} error={status.error}>
            {status.data?.series.flatMap((series) => series.episodes).length ? (
              status.data.series.map((series) =>
                series.episodes.map((episode) => (
                  <div key={episode.id} className="xr-review__episode-block">
                    <strong>
                      {series.title} - Episode {episode.episode_number}
                    </strong>
                    <EpisodePublishPanel episodeId={episode.id} projectId={projectId} />
                  </div>
                )),
              )
            ) : (
              <p>No episodes yet.</p>
            )}
          </QueryState>
        </Card>
      </div>
    </div>
  );
}
