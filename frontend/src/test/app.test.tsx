import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { routes } from "../router";

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("studio shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the nav and an empty-state dashboard", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));

    renderAt("/");

    expect(screen.getByText("Xerama Studio")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Story Studio" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/No projects yet/)).toBeInTheDocument());
  });

  it("renders a placeholder studio page naming its owning module", async () => {
    vi.stubGlobal("fetch", vi.fn());
    renderAt("/story");
    expect(screen.getByRole("heading", { name: "Story Studio" })).toBeInTheDocument();
    expect(screen.getByText(/MODULE-057/)).toBeInTheDocument();
  });

  it("surfaces an API error via the shared error banner", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 500 })),
    );

    renderAt("/");
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("boom"));
  });
});
