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

const PENDING_ASSET = {
  id: "A1",
  type: "image",
  status: "pending",
  storage_path: "",
  content_hash: "",
  mime_type: "",
  size_bytes: 1,
  width: null,
  height: null,
  duration_seconds: null,
  take_number: 2,
  rejection_reason: "",
  created_at: "2026-08-25T00:00:00Z",
};

const PROJECT_STATUS = {
  project: { id: "P1", name: "Trial 01", description: "", status: "active", created_at: "2026-08-25T00:00:00Z" },
  series: [
    {
      id: "S1",
      title: "Blood Sisters",
      status: "draft",
      episodes: [{ id: "E1", episode_number: 1, status: "canon_committed", current_render_version: 1 }],
    },
  ],
};

function routeFor(url: string): string {
  if (url.includes("status=pending")) return "pending";
  if (url.includes("/qc")) return "qc";
  if (url.includes("/status")) return "status";
  if (url.includes("/renders")) return "renders";
  if (url.includes("/accept")) return "accept";
  if (url.includes("/reject")) return "reject";
  return "unknown";
}

function mockFetch(overrides: Partial<Record<string, unknown>> = {}) {
  return vi.fn().mockImplementation((url: string) => {
    const kind = routeFor(url);
    if (kind in overrides) return Promise.resolve(jsonResponse(overrides[kind]));
    switch (kind) {
      case "pending":
        return Promise.resolve(jsonResponse([PENDING_ASSET]));
      case "status":
        return Promise.resolve(jsonResponse(PROJECT_STATUS));
      case "renders":
        return Promise.resolve(
          jsonResponse([{ id: "R1", episode_id: "E1", version: 1, status: "draft", render_asset_id: "RA1", parent_render_id: null, source_script_version: 1 }]),
        );
      case "qc":
        return Promise.resolve(
          jsonResponse([{ id: "QC1", asset_id: "A1", dimension: "composition", status: "warn", score: 6, evidence: {}, reasons: ["crowded frame"], repair_recommendation: "reframe", created_at: "2026-08-25T00:00:00Z" }]),
        );
      default:
        return Promise.resolve(jsonResponse({}));
    }
  });
}

describe("Review & Approval Studio (MODULE-060)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the pending-review queue and the episode publish panel", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/review/P1");

    await waitFor(() => expect(screen.getByText(/Awaiting review \(1\)/)).toBeInTheDocument());
    expect(screen.getByText(/image take 2/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Blood Sisters - Episode 1/)).toBeInTheDocument());
    expect(screen.getByText(/v1 - draft/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve for publish" })).toBeInTheDocument();
  });

  it("expands to show QC evidence and a repair recommendation", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/review/P1");
    await waitFor(() => expect(screen.getByRole("button", { name: "Show QC" })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Show QC" }));

    await waitFor(() => expect(screen.getByText(/composition: warn/)).toBeInTheDocument());
    expect(screen.getByText(/crowded frame/)).toBeInTheDocument();
    expect(screen.getByText(/reframe/)).toBeInTheDocument();
  });

  it("requires a reason before rejecting an asset", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/review/P1");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Reject / request retake" })).toBeDisabled(),
    );

    await userEvent.type(screen.getByLabelText("Rejection reason for A1"), "blurry face");
    expect(screen.getByRole("button", { name: "Reject / request retake" })).toBeEnabled();
  });

  it("approves an episode render for publish with an explicit action", async () => {
    const fetchMock = mockFetch();
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/review/P1");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Approve for publish" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Approve for publish" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/episode-renders/R1/approve"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
