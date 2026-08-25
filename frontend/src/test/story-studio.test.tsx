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

const SERIES = {
  id: "S1",
  project_id: "P1",
  title: "Blood Sisters",
  logline: "Two sisters, one secret.",
  genre: ["thriller"],
  target_audience: "general",
  episode_count_target: 3,
  episode_duration_target_seconds: 75,
  status: "draft",
};

function routeFor(url: string): string {
  if (url.endsWith("/bible")) return "bible";
  if (url.includes("/concept-candidates")) return "candidates";
  if (url.includes("/judge-decisions")) return "judge";
  if (url.includes("/season-plan")) return "season";
  if (url.includes("/episodes")) return "episodes";
  if (url.includes("/canon-events")) return "canon";
  return "series";
}

function mockFetch() {
  return vi.fn().mockImplementation((url: string) => {
    switch (routeFor(url)) {
      case "series":
        return Promise.resolve(jsonResponse(SERIES));
      case "bible":
        return Promise.resolve(
          jsonResponse({
            title: "Blood Sisters",
            logline: "x",
            premise: "A woman uncovers her sister's secret.",
            central_dramatic_question: "Will the truth destroy them?",
          }),
        );
      case "candidates":
        return Promise.resolve(
          jsonResponse([
            { id: "C1", batch_id: "B1", slot: "A", provider: "p", model: "m", accepted: false, candidate: { title: "A title", logline: "" }, created_at: "2026-08-25T00:00:00Z" },
            { id: "C2", batch_id: "B1", slot: "B", provider: "p", model: "m", accepted: true, candidate: { title: "B title", logline: "" }, created_at: "2026-08-25T00:00:00Z" },
          ]),
        );
      case "judge":
        return Promise.resolve(
          jsonResponse([
            { id: "D1", batch_id: "B1", decision: "B", provider: "p", model: "m", approved_concept: { title: "B title" }, created_at: "2026-08-25T00:00:00Z" },
          ]),
        );
      case "season":
        return Promise.resolve(
          jsonResponse({ id: "SP1", series_id: "S1", version: 1, status: "draft", qc_status: "pass", qc_score: 9, qc_reasons: [] }),
        );
      case "episodes":
        return Promise.resolve(
          jsonResponse([{ id: "E1", series_id: "S1", episode_number: 1, status: "canon_committed", version: 1 }]),
        );
      case "canon":
        return Promise.resolve(
          jsonResponse([{ change_type: "secret_exposed", episode_number: 1, description: "Lena is alive", committed: true }]),
        );
      default:
        return Promise.resolve(jsonResponse({}));
    }
  });
}

describe("Story Studio (MODULE-057)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders bible, concept lineage, season plan, episodes and canon panels", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/story/S1");

    await waitFor(() => expect(screen.getByRole("heading", { name: "Blood Sisters" })).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/uncovers her sister's secret/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/A title/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/approved "B title"/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/Version 1 - draft/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("link", { name: /Episode 1/ })).toBeInTheDocument());
    expect(screen.getByText(/canon_committed/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Lena is alive/)).toBeInTheDocument());
  });

  it("approving the season plan calls the approve endpoint with its version", async () => {
    const fetchMock = mockFetch();
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/story/S1");
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/series/S1/season-plan/1/approve"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("generating the next episode shows the returned QC badges", async () => {
    const fetchMock = mockFetch();
    const originalImpl = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.includes("/generate-next")) {
        return Promise.resolve(
          jsonResponse({
            episode_id: "E2",
            episode_number: 2,
            version: 1,
            retention_qc: { gate: "retention", status: "pass", score: 8, reasons: [], repair_recommendation: "" },
            continuity_qc: { gate: "continuity", status: "warn", score: 6, reasons: ["gap"], repair_recommendation: "" },
            canon_committed: true,
          }),
        );
      }
      return originalImpl(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/story/S1");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Generate next episode" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Generate next episode" }));

    await waitFor(() => expect(screen.getByText(/retention: pass/)).toBeInTheDocument());
    expect(screen.getByText(/continuity: warn/)).toBeInTheDocument();
    expect(screen.getByText("Canon committed")).toBeInTheDocument();
  });
});
