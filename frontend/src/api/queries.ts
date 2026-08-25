/**
 * TanStack Query hooks - the state/query strategy for every page. Pages
 * call these instead of `api.*` directly, so caching/invalidation stays
 * consistent and each page doesn't reinvent loading/error handling.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  CostSummaryResponse,
  JobRecord,
  ObservabilitySnapshot,
  ProjectRecord,
  ProjectStatusResponse,
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
