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

const SAMPLE_PROJECT = {
  id: "P1",
  name: "Trial 01",
  description: "",
  status: "active",
  created_at: "2026-08-25T00:00:00Z",
};

describe("Project Dashboard (MODULE-056)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders a project card with status badge and a link into the project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([SAMPLE_PROJECT])));

    renderAt("/");

    await waitFor(() => expect(screen.getByText("Trial 01")).toBeInTheDocument());
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Trial 01" })).toHaveAttribute("href", "/projects/P1");
  });

  it("separates archived projects into a collapsed section", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse([SAMPLE_PROJECT, { ...SAMPLE_PROJECT, id: "P2", name: "Old One", status: "archived" }]),
      ),
    );

    renderAt("/");

    await waitFor(() => expect(screen.getByText("1 archived project(s)")).toBeInTheDocument());
    // Active projects render as cards; the archived one only appears inside
    // the collapsed <details> summary list, not as its own card.
    expect(screen.getAllByText("Old One")).toHaveLength(1);
  });

  it("creates a project via the form and refreshes the list", async () => {
    // URL-dispatching (not positional) so unrelated background calls - e.g.
    // the global ChatPanel's GET /chat/status - can't desync a fixed
    // once()-chain sequence.
    let projectCreated = false;
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.includes("/projects")) {
        projectCreated = true;
        return Promise.resolve(jsonResponse(SAMPLE_PROJECT));
      }
      if (url.includes("/projects")) {
        return Promise.resolve(jsonResponse(projectCreated ? [SAMPLE_PROJECT] : []));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/");
    await waitFor(() => expect(screen.getByText(/No projects yet/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText("Project name"), "Trial 01");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(screen.getByText("Trial 01")).toBeInTheDocument());
    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(postCall).toBeDefined();
    expect(JSON.parse((postCall as [string, RequestInit])[1].body as string)).toEqual({ name: "Trial 01" });
  });

  it("shows a start-series form when a project has no series yet", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ project: SAMPLE_PROJECT, series: [] }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/projects/P1");

    await waitFor(() => expect(screen.getByRole("button", { name: "Generate series" })).toBeInTheDocument());
  });
});
