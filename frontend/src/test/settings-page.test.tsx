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

const SETTINGS = {
  runtime: {
    id: "default",
    llm_provider: "openrouter",
    ollama_model: "qwen2.5:7b",
    ollama_base_url: "http://localhost:11434/v1",
    media_provider: "fal",
    chat_model: "anthropic/claude-sonnet-5",
    updated_at: null,
  },
  openrouter_key_configured: true,
  fal_key_configured: true,
  ollama_reachable: true,
};

describe("Settings page", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the current provider configuration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(SETTINGS)));

    renderAt("/settings");

    await waitFor(() => expect(screen.getByRole("radio", { name: /OpenRouter/ })).toBeChecked());
    expect(screen.getAllByText(/API key: configured/).length).toBeGreaterThan(0);
  });

  it("switches to the local Ollama provider and saves", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SETTINGS));
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/settings");
    await waitFor(() => expect(screen.getByRole("radio", { name: /Local \(Ollama\)/ })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("radio", { name: /Local \(Ollama\)/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/settings"),
        expect.objectContaining({ method: "PATCH" }),
      ),
    );
  });

  it("keeps the Image & Video section hidden until its nav button is clicked", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(SETTINGS)));

    renderAt("/settings");
    await waitFor(() => expect(screen.getByRole("radio", { name: /OpenRouter/ })).toBeInTheDocument());
    expect(screen.queryByText(/fal.ai/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Image & Video" }));

    expect(screen.getByText(/fal.ai/)).toBeInTheDocument();
  });

  it("shows the assistant's configured status in its own section", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/chat/status"))
          return Promise.resolve(jsonResponse({ configured: true, model: "anthropic/claude-sonnet-5" }));
        return Promise.resolve(jsonResponse(SETTINGS));
      }),
    );

    renderAt("/settings");
    await waitFor(() => expect(screen.getByRole("button", { name: "Assistant" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Assistant" }));

    await waitFor(() => expect(screen.getByText(/OpenRouter key: configured/)).toBeInTheDocument());
  });
});
