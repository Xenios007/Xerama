import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { routes } from "../router";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

const SHOT_PLAN = {
  episode_number: 1,
  scenes: [
    {
      scene_number: 1,
      location: "apartment",
      shots: [
        {
          shot_number: 1,
          scene_number: 1,
          narrative_function: "hook",
          character_ids: ["CHAR_001"],
          dialogue: "This can't be real.",
          duration_seconds: 5,
          audio_mode: "native",
          continuity_group: null,
        },
      ],
    },
  ],
};

function routeFor(url: string): string {
  if (url.includes("/shots")) return "shots";
  if (url.includes("/storyboards")) return "storyboards";
  if (url.includes("/video-productions")) return "video";
  if (url.includes("/audio-productions")) return "audio";
  if (url.includes("/jobs")) return "jobs";
  if (url.includes("/episodes/")) return "episode";
  if (url.includes("/series/")) return "series";
  return "unknown";
}

function mockFetch(overrides: Partial<Record<string, unknown>> = {}) {
  return vi.fn().mockImplementation((url: string) => {
    const kind = routeFor(url);
    if (kind in overrides) return Promise.resolve(jsonResponse(overrides[kind]));
    switch (kind) {
      case "episode":
        return Promise.resolve(jsonResponse({ id: "E1", series_id: "S1", episode_number: 1, status: "shot_planned", version: 1 }));
      case "series":
        return Promise.resolve(jsonResponse({ id: "S1", project_id: "P1", title: "T", logline: "", genre: [], target_audience: "general", episode_count_target: 3, episode_duration_target_seconds: 75, status: "draft" }));
      case "shots":
        return Promise.resolve(jsonResponse(SHOT_PLAN));
      case "storyboards":
        return Promise.resolve(jsonResponse([]));
      case "video":
        return Promise.resolve(jsonResponse([]));
      case "audio":
        return Promise.resolve(jsonResponse([]));
      case "jobs":
        return Promise.resolve(jsonResponse([]));
      default:
        return Promise.resolve(jsonResponse({}));
    }
  });
}

describe("Production Studio (MODULE-059)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the shot grid with not-started status badges", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/production/E1");

    await waitFor(() => expect(screen.getByText(/Scene 1 \/ Shot 1/)).toBeInTheDocument());
    expect(screen.getByText(/Storyboard: not started/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate keyframe" })).toBeInTheDocument();
    // Native audio_mode shots don't need a separate audio take.
    expect(screen.queryByRole("button", { name: "Generate audio" })).not.toBeInTheDocument();
  });

  it("disables video generation until the storyboard is approved", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/production/E1");

    await waitFor(() => expect(screen.getByRole("button", { name: "Generate video" })).toBeDisabled());
  });

  it("shows approved status and enables video once the storyboard is approved", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ storyboards: [{ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "approved", approved_keyframe_asset_id: "A1" }] }),
    );

    renderAt("/production/E1");

    await waitFor(() => expect(screen.getByText(/Storyboard: approved/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Generate video" })).toBeEnabled();
  });

  it("filters to shots waiting on production", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        storyboards: [{ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "approved", approved_keyframe_asset_id: "A1" }],
        video: [{ id: "VP1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "approved", approved_take_asset_id: "A2" }],
      }),
    );

    renderAt("/production/E1");
    await waitFor(() => expect(screen.getByText(/Storyboard: approved/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Complete" }));
    expect(screen.getByText(/Scene 1 \/ Shot 1/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Waiting" }));
    expect(screen.getByText(/No shots match this filter/)).toBeInTheDocument();
  });

  it("generating a keyframe creates the storyboard, generates, and accepts the take", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.includes("/keyframes/generate")) {
        return Promise.resolve(jsonResponse({ id: "A1", type: "image", status: "pending", storage_path: "", content_hash: "", mime_type: "", size_bytes: 1, width: null, height: null, duration_seconds: null, take_number: 1, rejection_reason: "", created_at: "" }));
      }
      if (init?.method === "POST" && url.includes("/accept")) {
        return Promise.resolve(jsonResponse({ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "approved", approved_keyframe_asset_id: "A1" }));
      }
      if (init?.method === "POST" && url.endsWith("/storyboard")) {
        return Promise.resolve(jsonResponse({ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "draft", approved_keyframe_asset_id: null }));
      }
      const kind = routeFor(url);
      switch (kind) {
        case "episode":
          return Promise.resolve(jsonResponse({ id: "E1", series_id: "S1", episode_number: 1, status: "shot_planned", version: 1 }));
        case "series":
          return Promise.resolve(jsonResponse({ id: "S1", project_id: "P1", title: "T", logline: "", genre: [], target_audience: "general", episode_count_target: 3, episode_duration_target_seconds: 75, status: "draft" }));
        case "shots":
          return Promise.resolve(jsonResponse(SHOT_PLAN));
        case "storyboards":
        case "video":
        case "audio":
        case "jobs":
          return Promise.resolve(jsonResponse([]));
        default:
          return Promise.resolve(jsonResponse({}));
      }
    });
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/production/E1");
    await waitFor(() => expect(screen.getByRole("button", { name: "Generate keyframe" })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Generate keyframe" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/keyframes/generate"), expect.objectContaining({ method: "POST" })),
    );
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/keyframes/A1/accept"), expect.objectContaining({ method: "POST" })),
    );
  });
});
