import { render, screen, waitFor } from "@testing-library/react";
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

const PROJECT = { id: "P1", name: "Trial 01", description: "", status: "active", created_at: "2026-08-25T00:00:00Z" };

const FINISHED_EPISODE = {
  episode_id: "E1",
  series_id: "S1",
  series_title: "Blood Sisters",
  episode_number: 1,
  render_id: "R1",
  version: 2,
  render_asset_id: "A1",
  friendly_path: "finished_videos/S1/episode_01_v2.mp4",
  download_url: "/assets/A1/download",
  duration_seconds: 25,
  size_bytes: 6331588,
  created_at: "2026-08-27T13:00:00Z",
};

function routeFor(url: string): string {
  if (url.includes("/finished-episodes")) return "finished";
  if (url.endsWith(`/projects/P1`)) return "project";
  return "unknown";
}

function mockFetch(overrides: Partial<Record<string, unknown>> = {}) {
  return vi.fn().mockImplementation((url: string) => {
    const kind = routeFor(url);
    if (kind in overrides) return Promise.resolve(jsonResponse(overrides[kind]));
    switch (kind) {
      case "finished":
        return Promise.resolve(jsonResponse([FINISHED_EPISODE]));
      case "project":
        return Promise.resolve(jsonResponse(PROJECT));
      default:
        return Promise.resolve(jsonResponse({}));
    }
  });
}

describe("Library page", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists a finished episode with a player and download link", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/library/P1");

    await waitFor(() => expect(screen.getByText(/Blood Sisters - Episode 1/)).toBeInTheDocument());
    expect(screen.getByText("finished_videos/S1/episode_01_v2.mp4")).toBeInTheDocument();
    expect(document.querySelector(".xr-library__submeta")?.textContent).toContain("v2");
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      expect.stringContaining("/assets/A1/download"),
    );
  });

  it("shows an empty state when nothing has been approved yet", async () => {
    vi.stubGlobal("fetch", mockFetch({ finished: [] }));

    renderAt("/library/P1");

    await waitFor(() => expect(screen.getByText(/No finished episodes yet/)).toBeInTheDocument());
  });
});
