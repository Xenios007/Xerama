/**
 * TanStack Query hooks - the state/query strategy for every page. Pages
 * call these instead of `api.*` directly, so caching/invalidation stays
 * consistent and each page doesn't reinvent loading/error handling.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  Asset,
  CanonEvent,
  Character,
  CharacterCast,
  CharacterDNA,
  CharacterProvenance,
  ConceptCandidateRecord,
  CostSummaryResponse,
  CreativeBrief,
  EpisodeGenerationResult,
  EpisodeRecord,
  EpisodeRender,
  EpisodeShotPlan,
  GenerateSeriesResult,
  JobRecord,
  JudgeDecisionRecord,
  MediaQCAttempt,
  ObservabilitySnapshot,
  PhysicalStateVariant,
  ProjectRecord,
  ProjectStatusResponse,
  QCResult,
  SeasonPlanRecord,
  SeriesBible,
  SeriesRecord,
  ShotAudioProduction,
  ShotVideoProduction,
  Storyboard,
  VoiceProfile,
  WardrobeVariant,
} from "./types";

export const queryKeys = {
  projects: ["projects"] as const,
  project: (id: string) => ["projects", id] as const,
  projectStatus: (id: string) => ["projects", id, "status"] as const,
  projectCosts: (id: string) => ["projects", id, "costs", "summary"] as const,
  projectObservability: (id: string) => ["projects", id, "observability"] as const,
  jobs: (projectId: string) => ["jobs", { projectId }] as const,
};

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => api.get<ProjectRecord[]>("/projects"),
  });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: projectId ? queryKeys.project(projectId) : ["projects", "none"],
    queryFn: () => api.get<ProjectRecord>(`/projects/${projectId}`),
    enabled: Boolean(projectId),
  });
}

export function useProjectStatus(projectId: string | undefined) {
  return useQuery({
    queryKey: projectId ? queryKeys.projectStatus(projectId) : ["projects", "none", "status"],
    queryFn: () => api.get<ProjectStatusResponse>(`/projects/${projectId}/status`),
    enabled: Boolean(projectId),
  });
}

export function useProjectCostSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: projectId ? queryKeys.projectCosts(projectId) : ["projects", "none", "costs"],
    queryFn: () => api.get<CostSummaryResponse>(`/projects/${projectId}/costs/summary`),
    enabled: Boolean(projectId),
  });
}

export function useProjectObservability(projectId: string | undefined) {
  return useQuery({
    queryKey: projectId ? queryKeys.projectObservability(projectId) : ["projects", "none", "observability"],
    queryFn: () => api.get<ObservabilitySnapshot>(`/projects/${projectId}/observability`),
    enabled: Boolean(projectId),
    refetchInterval: 5000, // polling, per MODULE-054 "support polling first"
  });
}

export function useJobs(projectId: string | undefined) {
  return useQuery({
    queryKey: projectId ? queryKeys.jobs(projectId) : ["jobs", "none"],
    queryFn: () => api.get<JobRecord[]>(`/jobs?project_id=${projectId}`),
    enabled: Boolean(projectId),
    refetchInterval: 5000,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      api.post<ProjectRecord>("/projects", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

export function useArchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.post<ProjectRecord>(`/projects/${projectId}/archive`),
    onSuccess: (_data, projectId) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

export function useSeries(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId],
    queryFn: () => api.get<SeriesRecord>(`/series/${seriesId}`),
    enabled: Boolean(seriesId),
  });
}

export function useSeriesBible(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId, "bible"],
    queryFn: () => api.get<SeriesBible>(`/series/${seriesId}/bible`),
    enabled: Boolean(seriesId),
  });
}

export function useSeasonPlan(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId, "season-plan"],
    queryFn: () => api.get<SeasonPlanRecord>(`/series/${seriesId}/season-plan`),
    enabled: Boolean(seriesId),
    retry: false,
  });
}

export function useSeriesEpisodes(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId, "episodes"],
    queryFn: () => api.get<EpisodeRecord[]>(`/series/${seriesId}/episodes`),
    enabled: Boolean(seriesId),
  });
}

export function useConceptCandidates(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "concept-candidates"],
    queryFn: () => api.get<ConceptCandidateRecord[]>(`/projects/${projectId}/concept-candidates`),
    enabled: Boolean(projectId),
  });
}

export function useJudgeDecisions(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "judge-decisions"],
    queryFn: () => api.get<JudgeDecisionRecord[]>(`/projects/${projectId}/judge-decisions`),
    enabled: Boolean(projectId),
  });
}

export function useEpisodeQualityReports(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId, "quality-reports"],
    queryFn: () => api.get<QCResult[]>(`/episodes/${episodeId}/quality-reports`),
    enabled: Boolean(episodeId),
  });
}

export function useCanonEvents(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId, "canon-events"],
    queryFn: () => api.get<CanonEvent[]>(`/series/${seriesId}/canon-events`),
    enabled: Boolean(seriesId),
  });
}

export function useApproveSeasonPlan(seriesId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (version: number) =>
      api.post<SeasonPlanRecord>(`/series/${seriesId}/season-plan/${version}/approve`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["series", seriesId, "season-plan"] });
    },
  });
}

export function useGenerateNextEpisode(projectId: string | undefined, seriesId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<EpisodeGenerationResult>(
        `/series/${seriesId}/episodes/generate-next?project_id=${projectId}`,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episodes"] });
      if (projectId) void queryClient.invalidateQueries({ queryKey: queryKeys.projectStatus(projectId) });
    },
  });
}

export function useRegenerateEpisode(projectId: string | undefined, seriesId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (episodeNumber: number) =>
      api.post<EpisodeGenerationResult>(
        `/series/${seriesId}/episodes/${episodeNumber}/generate?project_id=${projectId}`,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episodes"] });
    },
  });
}

export function useGenerateSeries(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (brief: CreativeBrief) =>
      api.post<GenerateSeriesResult>(`/projects/${projectId}/generate-series`, brief),
    onSuccess: () => {
      if (projectId) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.projectStatus(projectId) });
      }
    },
  });
}

export function useCharacterCast(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId, "characters"],
    queryFn: () => api.get<CharacterCast>(`/series/${seriesId}/characters`),
    enabled: Boolean(seriesId),
  });
}

export function useCharacter(characterId: string | undefined) {
  return useQuery({
    queryKey: ["characters", characterId],
    queryFn: () => api.get<Character>(`/characters/${characterId}`),
    enabled: Boolean(characterId),
  });
}

export function useVoiceProfile(characterId: string | undefined) {
  return useQuery({
    queryKey: ["characters", characterId, "voice-profile"],
    queryFn: () => api.get<VoiceProfile>(`/characters/${characterId}/voice-profile`),
    enabled: Boolean(characterId),
  });
}

export function useWardrobeVariants(characterId: string | undefined) {
  return useQuery({
    queryKey: ["characters", characterId, "wardrobe"],
    queryFn: () => api.get<WardrobeVariant[]>(`/characters/${characterId}/wardrobe`),
    enabled: Boolean(characterId),
  });
}

export function usePhysicalStateVariants(characterId: string | undefined) {
  return useQuery({
    queryKey: ["characters", characterId, "physical-states"],
    queryFn: () => api.get<PhysicalStateVariant[]>(`/characters/${characterId}/physical-states`),
    enabled: Boolean(characterId),
  });
}

export function useCharacterAssets(projectId: string | undefined, characterId: string | undefined) {
  return useQuery({
    queryKey: ["assets", { projectId, characterId }],
    queryFn: () => api.get<Asset[]>(`/assets?project_id=${projectId}&character_id=${characterId}`),
    enabled: Boolean(projectId) && Boolean(characterId),
  });
}

export function useLockCharacter(characterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Character>(`/characters/${characterId}/lock`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["characters", characterId] }),
  });
}

export function useUnlockCharacterForRecast(characterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Character>(`/characters/${characterId}/unlock`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["characters", characterId] }),
  });
}

export function useSetCharacterProvenance(characterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provenance: CharacterProvenance) =>
      api.post<Character>(`/characters/${characterId}/provenance`, provenance),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["characters", characterId] }),
  });
}

export function useUpdateCharacterDna(characterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (character_dna: CharacterDNA) =>
      api.patch<Character>(`/characters/${characterId}/identity`, { character_dna }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["characters", characterId] }),
  });
}

export function useAcceptAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assetId: string) => api.post<Asset>(`/assets/${assetId}/accept`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["assets"] }),
  });
}

export function useRejectAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ assetId, reason }: { assetId: string; reason: string }) =>
      api.post<Asset>(`/assets/${assetId}/reject?reason=${encodeURIComponent(reason)}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["assets"] }),
  });
}

export function useEpisode(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId],
    queryFn: () => api.get<EpisodeRecord>(`/episodes/${episodeId}`),
    enabled: Boolean(episodeId),
  });
}

export function useEpisodeShotPlan(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId, "shots"],
    queryFn: () => api.get<EpisodeShotPlan>(`/episodes/${episodeId}/shots`),
    enabled: Boolean(episodeId),
  });
}

export function useStoryboards(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId, "storyboards"],
    queryFn: () => api.get<Storyboard[]>(`/episodes/${episodeId}/storyboards`),
    enabled: Boolean(episodeId),
  });
}

export function useVideoProductions(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId, "video-productions"],
    queryFn: () => api.get<ShotVideoProduction[]>(`/episodes/${episodeId}/video-productions`),
    enabled: Boolean(episodeId),
  });
}

export function useAudioProductions(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId, "audio-productions"],
    queryFn: () => api.get<ShotAudioProduction[]>(`/episodes/${episodeId}/audio-productions`),
    enabled: Boolean(episodeId),
  });
}

function invalidateEpisodeProduction(queryClient: ReturnType<typeof useQueryClient>, episodeId: string) {
  void queryClient.invalidateQueries({ queryKey: ["episodes", episodeId, "storyboards"] });
  void queryClient.invalidateQueries({ queryKey: ["episodes", episodeId, "video-productions"] });
  void queryClient.invalidateQueries({ queryKey: ["episodes", episodeId, "audio-productions"] });
}

export function useGenerateKeyframe(episodeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sceneNumber, shotNumber }: { sceneNumber: number; shotNumber: number }) => {
      const storyboard = await api.post<Storyboard>(
        `/episodes/${episodeId}/scenes/${sceneNumber}/shots/${shotNumber}/storyboard`,
      );
      const asset = await api.post<Asset>(`/storyboards/${storyboard.id}/keyframes/generate`);
      await api.post<Storyboard>(`/storyboards/${storyboard.id}/keyframes/${asset.id}/accept`);
    },
    onSuccess: () => invalidateEpisodeProduction(queryClient, episodeId),
  });
}

export function useGenerateVideoTake(episodeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sceneNumber, shotNumber }: { sceneNumber: number; shotNumber: number }) => {
      const production = await api.post<ShotVideoProduction>(
        `/episodes/${episodeId}/scenes/${sceneNumber}/shots/${shotNumber}/video-production`,
      );
      const asset = await api.post<Asset>(`/video-productions/${production.id}/takes/generate`);
      await api.post<ShotVideoProduction>(`/video-productions/${production.id}/takes/${asset.id}/accept`);
    },
    onSuccess: () => invalidateEpisodeProduction(queryClient, episodeId),
  });
}

export function useGenerateAudioTake(episodeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sceneNumber,
      shotNumber,
      characterId,
    }: {
      sceneNumber: number;
      shotNumber: number;
      characterId: string;
    }) => {
      const production = await api.post<ShotAudioProduction>(
        `/episodes/${episodeId}/scenes/${sceneNumber}/shots/${shotNumber}/audio-production`,
      );
      const asset = await api.post<Asset>(`/audio-productions/${production.id}/takes/generate`, {
        character_id: characterId,
      });
      await api.post<ShotAudioProduction>(`/audio-productions/${production.id}/takes/${asset.id}/accept`);
    },
    onSuccess: () => invalidateEpisodeProduction(queryClient, episodeId),
  });
}

export function usePendingAssets(projectId: string | undefined) {
  return useQuery({
    queryKey: ["assets", { projectId, status: "pending" }],
    queryFn: () => api.get<Asset[]>(`/assets?project_id=${projectId}&status=pending`),
    enabled: Boolean(projectId),
  });
}

export function useAssetQc(assetId: string | undefined) {
  return useQuery({
    queryKey: ["assets", assetId, "qc"],
    queryFn: () => api.get<MediaQCAttempt[]>(`/assets/${assetId}/qc`),
    enabled: Boolean(assetId),
  });
}

export function useEpisodeRenders(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId, "renders"],
    queryFn: () => api.get<EpisodeRender[]>(`/episodes/${episodeId}/renders`),
    enabled: Boolean(episodeId),
  });
}

export function useApproveEpisodeRender() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (renderId: string) => api.post<EpisodeRender>(`/episode-renders/${renderId}/approve`),
    onSuccess: (render) => {
      void queryClient.invalidateQueries({ queryKey: ["episodes", render.episode_id, "renders"] });
    },
  });
}
