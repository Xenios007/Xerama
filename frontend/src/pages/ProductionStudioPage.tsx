import type { ReactElement } from "react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { QueryState } from "../components/ui/QueryState";
import {
  IconArrowRight,
  IconBack,
  IconCollapse,
  IconFilm,
  IconFilter,
  IconFlower,
  IconGrid,
  IconHelp,
  IconMore,
  IconPerson,
  IconPlus,
  IconSearch,
  IconSettings,
  IconSliders,
  IconSparkles,
  IconTrash,
  IconWand,
} from "../components/ui/icons";
import { ApiError, API_BASE_URL } from "../api/client";
import type { AudioMode, Character, Shot, ShotAudioProduction, ShotVideoProduction, Storyboard } from "../api/types";
import {
  useAcceptKeyframe,
  useAcceptVideoTake,
  useAudioProductions,
  useCharacterCast,
  useEpisode,
  useEpisodeShotPlan,
  useGenerateAudioTake,
  useGenerateKeyframe,
  useGenerateVideoTake,
  useRejectAsset,
  useSeries,
  useStoryboards,
  useVideoProductions,
  type PendingKeyframe,
  type PendingVideoTake,
} from "../api/queries";
import "./ProductionStudioPage.css";

function assetUrl(assetId: string): string {
  return `${API_BASE_URL}/assets/${assetId}/download`;
}

type SidebarSection = "media" | "characters" | "scenes" | "tools" | "trash";
type Mode = "image" | "video";

interface Entry {
  shot: Shot;
  storyboard: Storyboard | undefined;
  videoProduction: ShotVideoProduction | undefined;
  audioProduction: ShotAudioProduction | undefined;
}

function keyOf(shot: Shot): string {
  return `${shot.scene_number}.${shot.shot_number}`;
}

// --- Sidebar ---

interface SidebarProps {
  section: SidebarSection;
  onSection: (s: SidebarSection) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

function Sidebar({ section, onSection, collapsed, onToggleCollapsed }: SidebarProps) {
  const items: { id: SidebarSection; label: string; icon: (p: { className?: string }) => ReactElement }[] = [
    { id: "media", label: "All Media", icon: IconGrid },
    { id: "characters", label: "Characters", icon: IconPerson },
    { id: "scenes", label: "Scenes", icon: IconFilm },
  ];

  return (
    <nav className={`xr-flow__sidebar${collapsed ? " xr-flow__sidebar--collapsed" : ""}`}>
      <div className="xr-flow__sidebar-main">
        {items.map((item) => (
          <button
            key={item.id}
            className={`xr-flow__nav-item${section === item.id ? " xr-flow__nav-item--active" : ""}`}
            onClick={() => onSection(item.id)}
            title={item.label}
          >
            <item.icon />
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
        <hr className="xr-flow__sidebar-divider" />
        <button
          className={`xr-flow__nav-item${section === "tools" ? " xr-flow__nav-item--active" : ""}`}
          onClick={() => onSection("tools")}
          title="Tools"
        >
          <IconSparkles />
          {!collapsed && <span>Tools</span>}
        </button>
      </div>
      <div className="xr-flow__sidebar-bottom">
        <button
          className={`xr-flow__nav-item${section === "trash" ? " xr-flow__nav-item--active" : ""}`}
          onClick={() => onSection("trash")}
          title="Trash"
        >
          <IconTrash />
          {!collapsed && <span>Trash</span>}
        </button>
        <button className="xr-flow__nav-item" onClick={onToggleCollapsed} title="Collapse">
          <IconCollapse />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </nav>
  );
}

// --- Top bar ---

function TopBar({
  title,
  badge,
  search,
  onSearch,
}: {
  title: string;
  badge: string;
  search: string;
  onSearch: (v: string) => void;
}) {
  return (
    <header className="xr-flow__topbar">
      <div className="xr-flow__topbar-left">
        <Link to=".." relative="path" className="xr-flow__icon-btn" title="Back">
          <IconBack />
        </Link>
        <span className="xr-flow__title">{title}</span>
        <button className="xr-flow__icon-btn" disabled title="More">
          <IconMore />
        </button>
      </div>
      <div className="xr-flow__search">
        <IconSearch />
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search shots"
          aria-label="Search shots"
        />
        <IconFilter />
      </div>
      <div className="xr-flow__topbar-right">
        <button className="xr-flow__icon-btn" disabled title="Add">
          <IconPlus />
        </button>
        <button className="xr-flow__icon-btn" disabled title="Help">
          <IconHelp />
        </button>
        <Link to="/settings" className="xr-flow__icon-btn" title="Settings">
          <IconSettings />
        </Link>
        <button className="xr-flow__icon-btn" disabled title="More">
          <IconMore />
        </button>
        <span className="xr-flow__badge">{badge}</span>
        <span className="xr-flow__avatar">{title.charAt(0).toUpperCase() || "X"}</span>
      </div>
    </header>
  );
}

// --- Canvas ---

function EmptyCanvas({ text }: { text: string }) {
  return (
    <div className="xr-flow__empty">
      <IconFlower className="xr-flow__empty-icon" />
      <p>{text}</p>
    </div>
  );
}

// --- Timeline strip (bottom of the "All Media" canvas) ---

function ShotStrip({
  entries,
  activeKey,
  onSelect,
}: {
  entries: Entry[];
  activeKey: string;
  onSelect: (key: string) => void;
}) {
  return (
    <div className="xr-flow__strip">
      {entries.map(({ shot, storyboard }) => {
        const key = keyOf(shot);
        const thumb = storyboard?.approved_keyframe_asset_id;
        return (
          <button
            key={key}
            className={`xr-flow__strip-item${key === activeKey ? " xr-flow__strip-item--active" : ""}`}
            onClick={() => onSelect(key)}
          >
            {thumb ? (
              <img src={assetUrl(thumb)} alt="" />
            ) : (
              <div className="xr-flow__strip-thumb-empty" />
            )}
          </button>
        );
      })}
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
  const characterCast = useCharacterCast(episode.data?.series_id);

  const [section, setSection] = useState<SidebarSection>("media");
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("image");
  const [search, setSearch] = useState("");
  const [pendingKeyframe, setPendingKeyframe] = useState<PendingKeyframe | null>(null);
  const [pendingVideo, setPendingVideo] = useState<PendingVideoTake | null>(null);

  const generateKeyframe = useGenerateKeyframe(episodeId ?? "");
  const acceptKeyframe = useAcceptKeyframe(episodeId ?? "");
  const generateVideo = useGenerateVideoTake(episodeId ?? "");
  const acceptVideo = useAcceptVideoTake(episodeId ?? "");
  const rejectAsset = useRejectAsset();
  const generateAudio = useGenerateAudioTake(episodeId ?? "");

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

  const allShots = (shotPlan.data?.scenes ?? []).flatMap((scene) => scene.shots);
  const filteredShots = search.trim()
    ? allShots.filter((s) =>
        `${s.narrative_function} ${s.action} ${s.dialogue}`.toLowerCase().includes(search.trim().toLowerCase()),
      )
    : allShots;
  const entries: Entry[] = filteredShots.map((shot) => {
    const key = keyOf(shot);
    return {
      shot,
      storyboard: storyboardByKey.get(key),
      videoProduction: videoByKey.get(key),
      audioProduction: audioByKey.get(key),
    };
  });

  const firstKey = entries[0] ? keyOf(entries[0].shot) : "";
  const activeKey = selectedKey ?? firstKey;
  const active = entries.find((e) => keyOf(e.shot) === activeKey);

  function selectShot(key: string) {
    setSelectedKey(key);
    setPendingKeyframe(null);
    setPendingVideo(null);
    setSection("media");
  }

  function handleSend() {
    if (!active || !episodeId) return;
    const coords = { sceneNumber: active.shot.scene_number, shotNumber: active.shot.shot_number };
    if (mode === "image") {
      generateKeyframe.mutate(coords, { onSuccess: setPendingKeyframe });
    } else {
      generateVideo.mutate(coords, { onSuccess: setPendingVideo });
    }
  }

  const busy = generateKeyframe.isPending || generateVideo.isPending || acceptKeyframe.isPending || acceptVideo.isPending || rejectAsset.isPending;
  const genError = generateKeyframe.error ?? generateVideo.error;

  const approvedImageId = active?.storyboard?.approved_keyframe_asset_id ?? null;
  const approvedVideoId = active?.videoProduction?.approved_take_asset_id ?? null;

  const episodeTitle = series.data
    ? `${series.data.title} · Episode ${episode.data?.episode_number ?? "?"}`
    : "Production Studio";

  return (
    <div className="xr-flow">
      <TopBar title={episodeTitle} badge={episode.data?.status ?? ""} search={search} onSearch={setSearch} />

      <div className="xr-flow__body">
        <Sidebar
          section={section}
          onSection={setSection}
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed((v) => !v)}
        />

        <main className="xr-flow__canvas">
          <QueryState isLoading={shotPlan.isLoading} error={shotPlan.error}>
            {section === "media" && (
              <>
                {!active ? (
                  <EmptyCanvas text="Start creating or drop media" />
                ) : (
                  <div className="xr-flow__canvas-inner">
                    {mode === "image" ? (
                      pendingKeyframe ? (
                        <div className="xr-flow__media-wrap">
                          <img className="xr-flow__media" src={assetUrl(pendingKeyframe.asset.id)} alt="Generated keyframe" />
                          <div className="xr-flow__overlay">
                            <Button
                              disabled={busy}
                              onClick={() =>
                                acceptKeyframe.mutate(
                                  { storyboardId: pendingKeyframe.storyboardId, assetId: pendingKeyframe.asset.id },
                                  { onSuccess: () => setPendingKeyframe(null) },
                                )
                              }
                            >
                              Accept
                            </Button>
                            <Button
                              variant="danger"
                              disabled={busy}
                              onClick={() =>
                                rejectAsset.mutate(
                                  { assetId: pendingKeyframe.asset.id, reason: "regenerate" },
                                  { onSuccess: () => setPendingKeyframe(null) },
                                )
                              }
                            >
                              Reject
                            </Button>
                          </div>
                        </div>
                      ) : approvedImageId ? (
                        <div className="xr-flow__media-wrap">
                          <img className="xr-flow__media" src={assetUrl(approvedImageId)} alt="Approved keyframe" />
                        </div>
                      ) : (
                        <EmptyCanvas text="Start creating or drop media" />
                      )
                    ) : pendingVideo ? (
                      <div className="xr-flow__media-wrap">
                        <video className="xr-flow__media" controls src={assetUrl(pendingVideo.asset.id)} />
                        <div className="xr-flow__overlay">
                          <Button
                            disabled={busy}
                            onClick={() =>
                              acceptVideo.mutate(
                                { productionId: pendingVideo.productionId, assetId: pendingVideo.asset.id },
                                { onSuccess: () => setPendingVideo(null) },
                              )
                            }
                          >
                            Accept
                          </Button>
                          <Button
                            variant="danger"
                            disabled={busy}
                            onClick={() =>
                              rejectAsset.mutate(
                                { assetId: pendingVideo.asset.id, reason: "regenerate" },
                                { onSuccess: () => setPendingVideo(null) },
                              )
                            }
                          >
                            Reject
                          </Button>
                        </div>
                      </div>
                    ) : approvedVideoId ? (
                      <div className="xr-flow__media-wrap">
                        <video className="xr-flow__media" controls src={assetUrl(approvedVideoId)} />
                      </div>
                    ) : (
                      <EmptyCanvas text="Start creating or drop media" />
                    )}
                    {genError && (
                      <p className="xr-flow__error">
                        {genError instanceof ApiError ? genError.detail : "Generation failed."}
                      </p>
                    )}
                  </div>
                )}
                {entries.length > 0 && <ShotStrip entries={entries} activeKey={activeKey} onSelect={selectShot} />}
              </>
            )}

            {section === "characters" && (
              <div className="xr-flow__grid-panel">
                {(characterCast.data?.characters ?? []).length === 0 ? (
                  <p className="xr-flow__panel-empty">No characters cast yet.</p>
                ) : (
                  <div className="xr-flow__character-grid">
                    {characterCast.data?.characters.map((c: Character) => (
                      <div key={c.id} className="xr-flow__character-card">
                        {c.visual_identity_id ? (
                          <img src={assetUrl(c.visual_identity_id)} alt={c.name} />
                        ) : (
                          <div className="xr-flow__character-thumb-empty">
                            <IconPerson />
                          </div>
                        )}
                        <strong>{c.name}</strong>
                        <span>{c.role}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {section === "scenes" && (
              <div className="xr-flow__grid-panel">
                {(shotPlan.data?.scenes ?? []).map((scene) => (
                  <button
                    key={scene.scene_number}
                    className="xr-flow__scene-row"
                    onClick={() => scene.shots[0] && selectShot(keyOf(scene.shots[0]))}
                  >
                    <strong>Scene {scene.scene_number}</strong>
                    <span>{scene.location}</span>
                    <span className="xr-flow__scene-count">{scene.shots.length} shots</span>
                  </button>
                ))}
              </div>
            )}

            {section === "tools" && active && (
              <div className="xr-flow__grid-panel xr-flow__tools">
                <h3>Shot Inspector</h3>
                <dl className="xr-flow__dl">
                  <dt>Narrative function</dt>
                  <dd>{active.shot.narrative_function || "—"}</dd>
                  <dt>Action</dt>
                  <dd>{active.shot.action || "—"}</dd>
                  {active.shot.dialogue && (
                    <>
                      <dt>Dialogue</dt>
                      <dd>&ldquo;{active.shot.dialogue}&rdquo;</dd>
                    </>
                  )}
                  <dt>Duration</dt>
                  <dd>{active.shot.duration_seconds}s</dd>
                </dl>
                <h4>Camera</h4>
                <dl className="xr-flow__dl">
                  <dt>Shot size</dt>
                  <dd>{active.shot.camera.shot_size || "—"}</dd>
                  <dt>Angle</dt>
                  <dd>{active.shot.camera.angle || "—"}</dd>
                  <dt>Lens</dt>
                  <dd>{active.shot.camera.lens || "—"}</dd>
                  <dt>Movement</dt>
                  <dd>{active.shot.camera.movement || "—"}</dd>
                </dl>
                <h4>Visual</h4>
                <dl className="xr-flow__dl">
                  <dt>Composition</dt>
                  <dd>{active.shot.visual.composition || "—"}</dd>
                  <dt>Lighting</dt>
                  <dd>{active.shot.visual.lighting || "—"}</dd>
                  <dt>Emotion</dt>
                  <dd>{active.shot.visual.emotion || "—"}</dd>
                </dl>
                {(["tts_lipsync", "hybrid"] as AudioMode[]).includes(active.shot.audio_mode) && (
                  <>
                    <h4>Audio</h4>
                    {active.audioProduction?.approved_take_asset_id ? (
                      <audio controls src={assetUrl(active.audioProduction.approved_take_asset_id)} />
                    ) : (
                      <Button
                        variant="secondary"
                        disabled={generateAudio.isPending || !active.shot.character_ids[0]}
                        onClick={() =>
                          active.shot.character_ids[0] &&
                          generateAudio.mutate({
                            sceneNumber: active.shot.scene_number,
                            shotNumber: active.shot.shot_number,
                            characterId: active.shot.character_ids[0],
                          })
                        }
                      >
                        Generate audio
                      </Button>
                    )}
                  </>
                )}
              </div>
            )}

            {section === "trash" && (
              <div className="xr-flow__grid-panel">
                <p className="xr-flow__panel-empty">Rejected takes aren't tracked in a dedicated view yet.</p>
              </div>
            )}
          </QueryState>
        </main>
      </div>

      <div className="xr-flow__prompt-bar">
        <div className="xr-flow__prompt-input-row">
          <input
            readOnly
            value={active ? active.shot.action || active.shot.narrative_function : ""}
            placeholder="What do you want to create?"
          />
        </div>
        <div className="xr-flow__prompt-actions-row">
          <button className="xr-flow__icon-btn" disabled title="Attach">
            <IconPlus />
          </button>
          <button
            className="xr-flow__mode-pill"
            onClick={() => setMode((m) => (m === "image" ? "video" : "image"))}
            disabled={!active}
          >
            {mode === "image" ? "Image" : "Video"}
          </button>
          <div className="xr-flow__prompt-spacer" />
          <button className="xr-flow__icon-btn" disabled title="Edit">
            <IconWand />
          </button>
          <button className="xr-flow__icon-btn" disabled title="Adjust">
            <IconSliders />
          </button>
          <button
            className="xr-flow__send"
            disabled={!active || busy}
            onClick={handleSend}
            title="Generate"
          >
            <IconArrowRight />
          </button>
        </div>
      </div>
      <p className="xr-flow__disclaimer">Xerama can make mistakes with generated media - review before approving.</p>
    </div>
  );
}
