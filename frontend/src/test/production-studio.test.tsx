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
          production_priority: "high",
          character_ids: ["CHAR_001"],
          dialogue: "This can't be real.",
          action: "Mira stares at the letter.",
          duration_seconds: 5,
          camera: { shot_size: "close", angle: "eye-level", lens: "standard", movement: "static" },
          visual: { composition: "centered", lighting: "dim", emotion: "shock" },
          audio_mode: "native",
          continuity_group: null,
        },
      ],
    },
  ],
};

const CAST = {
  characters: [
    { id: "CHAR_001", name: "Mira", role: "protagonist", age: "28", description: "", personality: "", character_dna: {}, visual_identity_id: null, voice_identity_id: null, reference_pack: {}, identity_provenance: {}, locked: false, version: 1 },
  ],
};

function routeFor(url: string): string {
  if (url.includes("/shots")) return "shots";
  if (url.includes("/storyboards")) return "storyboards";
  if (url.includes("/video-productions")) return "video";
  if (url.includes("/audio-productions")) return "audio";
  if (url.includes("/characters")) return "characters";
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
        return Promise.resolve(jsonResponse({ id: "S1", project_id: "P1", title: "Blood Sisters", logline: "", genre: [], target_audience: "general", episode_count_target: 3, episode_duration_target_seconds: 75, status: "draft" }));
      case "shots":
        return Promise.resolve(jsonResponse(SHOT_PLAN));
      case "storyboards":
        return Promise.resolve(jsonResponse([]));
      case "video":
        return Promise.resolve(jsonResponse([]));
      case "audio":
        return Promise.resolve(jsonResponse([]));
      case "characters":
        return Promise.resolve(jsonResponse(CAST));
      case "jobs":
        return Promise.resolve(jsonResponse([]));
      default:
        return Promise.resolve(jsonResponse({}));
    }
  });
}

describe("Production Studio (Flow-style redesign)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the episode title, character ingredients, and the shot inspector", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/production/E1");

    await waitFor(() => expect(screen.getByText(/Blood Sisters/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Characters" }));
    expect(screen.getByText("Mira")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tools" }));
    expect(screen.getByText("hook")).toBeInTheDocument(); // narrative_function
    expect(screen.getByText("close")).toBeInTheDocument(); // camera.shot_size
  });

  it("shows a pending keyframe with Accept/Reject after generating, not auto-accepted", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.endsWith("/storyboard")) {
        return Promise.resolve(jsonResponse({ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "draft", approved_keyframe_asset_id: null }));
      }
      if (init?.method === "POST" && url.includes("/keyframes/generate")) {
        return Promise.resolve(
          jsonResponse({ id: "A1", type: "image", status: "pending", storage_path: "", content_hash: "", mime_type: "", size_bytes: 1, width: null, height: null, duration_seconds: null, take_number: 1, rejection_reason: "", created_at: "" }),
        );
      }
      const kind = routeFor(url);
      switch (kind) {
        case "episode":
          return Promise.resolve(jsonResponse({ id: "E1", series_id: "S1", episode_number: 1, status: "shot_planned", version: 1 }));
        case "series":
          return Promise.resolve(jsonResponse({ id: "S1", project_id: "P1", title: "Blood Sisters", logline: "", genre: [], target_audience: "general", episode_count_target: 3, episode_duration_target_seconds: 75, status: "draft" }));
        case "shots":
          return Promise.resolve(jsonResponse(SHOT_PLAN));
        case "characters":
          return Promise.resolve(jsonResponse(CAST));
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
    await waitFor(() => expect(screen.getByTitle("Generate")).toBeEnabled());

    await userEvent.click(screen.getByTitle("Generate"));

    // The generate call happens, but accept is NOT called automatically -
    // the canvas shows Accept/Reject for the user to decide.
    await waitFor(() => expect(screen.getByRole("button", { name: "Accept" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/keyframes/A1/accept"), expect.anything());
  });

  it("clicking Accept on a pending keyframe calls the accept endpoint with the right ids", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.endsWith("/storyboard")) {
        return Promise.resolve(jsonResponse({ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "draft", approved_keyframe_asset_id: null }));
      }
      if (init?.method === "POST" && url.includes("/keyframes/generate")) {
        return Promise.resolve(
          jsonResponse({ id: "A1", type: "image", status: "pending", storage_path: "", content_hash: "", mime_type: "", size_bytes: 1, width: null, height: null, duration_seconds: null, take_number: 1, rejection_reason: "", created_at: "" }),
        );
      }
      if (init?.method === "POST" && url.includes("/keyframes/A1/accept")) {
        return Promise.resolve(jsonResponse({ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "approved", approved_keyframe_asset_id: "A1" }));
      }
      const kind = routeFor(url);
      switch (kind) {
        case "episode":
          return Promise.resolve(jsonResponse({ id: "E1", series_id: "S1", episode_number: 1, status: "shot_planned", version: 1 }));
        case "series":
          return Promise.resolve(jsonResponse({ id: "S1", project_id: "P1", title: "Blood Sisters", logline: "", genre: [], target_audience: "general", episode_count_target: 3, episode_duration_target_seconds: 75, status: "draft" }));
        case "shots":
          return Promise.resolve(jsonResponse(SHOT_PLAN));
        case "characters":
          return Promise.resolve(jsonResponse(CAST));
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
    await waitFor(() => expect(screen.getByTitle("Generate")).toBeEnabled());
    await userEvent.click(screen.getByTitle("Generate"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Accept" })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/keyframes/A1/accept"), expect.objectContaining({ method: "POST" })),
    );
  });

  it("shows the approved keyframe (no Accept/Reject overlay) once accepted", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        storyboards: [{ id: "SB1", episode_id: "E1", scene_number: 1, shot_number: 1, status: "approved", approved_keyframe_asset_id: "A1" }],
      }),
    );

    renderAt("/production/E1");

    await waitFor(() => expect(screen.getByAltText("Approved keyframe")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
  });
});
