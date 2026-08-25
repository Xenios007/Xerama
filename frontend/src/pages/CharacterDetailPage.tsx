import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import {
  useAcceptAsset,
  useCharacter,
  useCharacterAssets,
  useLockCharacter,
  usePhysicalStateVariants,
  useRejectAsset,
  useSeries,
  useUnlockCharacterForRecast,
  useVoiceProfile,
  useWardrobeVariants,
} from "../api/queries";
import "./CharacterStudioPage.css";

export function CharacterDetailPage() {
  const { seriesId, characterId } = useParams<{ seriesId: string; characterId: string }>();
  const series = useSeries(seriesId);
  const character = useCharacter(characterId);
  const voiceProfile = useVoiceProfile(characterId);
  const wardrobe = useWardrobeVariants(characterId);
  const physicalStates = usePhysicalStateVariants(characterId);
  const assets = useCharacterAssets(series.data?.project_id, characterId);
  const lock = useLockCharacter(characterId);
  const unlock = useUnlockCharacterForRecast(characterId);
  const acceptAsset = useAcceptAsset();
  const rejectAsset = useRejectAsset();
  const [showRecastWarning, setShowRecastWarning] = useState(false);

  return (
    <div>
      <h1>Character</h1>
      <QueryState isLoading={character.isLoading} error={character.error}>
        {character.data && (
          <>
            <Card title={character.data.name}>
              <p>
                {character.data.role} · {character.data.age}
              </p>
              <p>{character.data.description}</p>
              <div className="xr-detail__actions">
                {character.data.locked ? (
                  <>
                    <Button variant="secondary" disabled>
                      Locked (v{character.data.version})
                    </Button>
                    {!showRecastWarning ? (
                      <Button variant="danger" onClick={() => setShowRecastWarning(true)}>
                        Unlock for recast
                      </Button>
                    ) : (
                      <Button
                        variant="danger"
                        onClick={() => unlock.mutate()}
                        disabled={unlock.isPending}
                      >
                        Confirm recast
                      </Button>
                    )}
                  </>
                ) : (
                  <Button onClick={() => lock.mutate()} disabled={lock.isPending}>
                    Lock identity
                  </Button>
                )}
              </div>
              {showRecastWarning && (
                <p className="xr-detail__warning">
                  Recasting unlocks the root identity for regeneration. Any shot, storyboard, or
                  video take already generated against this identity may become visually
                  inconsistent - they are not automatically invalidated or regenerated.
                </p>
              )}
            </Card>

            <div className="xr-detail__grid">
              <Card title="Character DNA">
                <p>Eyes: {character.data.character_dna.eyes || "—"}</p>
                <p>Hair: {character.data.character_dna.hair || "—"}</p>
                <p>Build: {character.data.character_dna.build || "—"}</p>
                <p>Distinguishing: {character.data.character_dna.distinguishing_features || "—"}</p>
              </Card>

              <Card title="Provenance">
                <p
                  className={`xr-detail__provenance${
                    character.data.identity_provenance.identity_type === "licensed_authorized" &&
                    !character.data.identity_provenance.consent_reference
                      ? " xr-detail__provenance--unknown"
                      : ""
                  }`}
                >
                  Type: {character.data.identity_provenance.identity_type}
                </p>
                <p>Consent reference: {character.data.identity_provenance.consent_reference || "none"}</p>
                <p>Notes: {character.data.identity_provenance.notes || "—"}</p>
              </Card>

              <Card title="Reference pack">
                {Object.keys(character.data.reference_pack).length === 0 ? (
                  <p>No reference views yet.</p>
                ) : (
                  <ul>
                    {Object.entries(character.data.reference_pack).map(([view, assetId]) => (
                      <li key={view}>
                        {view}: {assetId}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card title="Voice">
                <QueryState isLoading={voiceProfile.isLoading} error={voiceProfile.error}>
                  {voiceProfile.data && (
                    <>
                      <p>Provider: {voiceProfile.data.provider || "unassigned"}</p>
                      <p>Language: {voiceProfile.data.language}</p>
                      <p>{voiceProfile.data.locked ? "Locked" : "Unlocked"}</p>
                    </>
                  )}
                </QueryState>
              </Card>

              <Card title="Wardrobe">
                <QueryState isLoading={wardrobe.isLoading} error={wardrobe.error}>
                  {wardrobe.data?.length ? (
                    <ul>
                      {wardrobe.data.map((v) => (
                        <li key={v.id}>{v.label}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No wardrobe variants yet.</p>
                  )}
                </QueryState>
              </Card>

              <Card title="Physical states">
                <QueryState isLoading={physicalStates.isLoading} error={physicalStates.error}>
                  {physicalStates.data?.length ? (
                    <ul>
                      {physicalStates.data.map((v) => (
                        <li key={v.id}>{v.label}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No physical-state variants yet.</p>
                  )}
                </QueryState>
              </Card>
            </div>

            <div style={{ marginTop: "1rem" }}>
              <Card title="Visual takes">
                <QueryState isLoading={assets.isLoading} error={assets.error}>
                  {assets.data?.length ? (
                    assets.data.map((asset) => (
                      <div key={asset.id} className="xr-asset-row">
                        <span>
                          {asset.type} take {asset.take_number} - {asset.status}
                        </span>
                        {asset.status === "pending" && (
                          <span style={{ display: "flex", gap: "0.4rem" }}>
                            <Button onClick={() => acceptAsset.mutate(asset.id)}>Accept</Button>
                            <Button
                              variant="danger"
                              onClick={() => rejectAsset.mutate({ assetId: asset.id, reason: "manual review" })}
                            >
                              Reject
                            </Button>
                          </span>
                        )}
                      </div>
                    ))
                  ) : (
                    <p>No visual takes recorded for this character yet.</p>
                  )}
                </QueryState>
              </Card>
            </div>
          </>
        )}
      </QueryState>
    </div>
  );
}
