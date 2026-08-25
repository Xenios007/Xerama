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

const CHARACTER = {
  id: "CHAR_001",
  name: "Mara",
  role: "protagonist",
  age: "29",
  description: "A woman uncovering the truth.",
  personality: "determined",
  character_dna: { eyes: "brown", hair: "dark", build: "", distinguishing_features: "" },
  visual_identity_id: null,
  voice_identity_id: null,
  reference_pack: { front: "A1" },
  identity_provenance: { identity_type: "synthetic_original", consent_reference: "", notes: "" },
  locked: false,
  version: 1,
};

function routeFor(url: string): string {
  if (url.includes("/voice-profile")) return "voice";
  if (url.includes("/wardrobe")) return "wardrobe";
  if (url.includes("/physical-states")) return "physical";
  if (url.includes("/characters/")) return "character";
  if (url.includes("/assets")) return "assets";
  if (url.includes("/series/")) return "series-characters";
  return "unknown";
}

function mockFetch(character = CHARACTER) {
  return vi.fn().mockImplementation((url: string) => {
    switch (routeFor(url)) {
      case "series-characters":
        return Promise.resolve(jsonResponse({ characters: [character] }));
      case "character":
        return Promise.resolve(jsonResponse(character));
      case "voice":
        return Promise.resolve(
          jsonResponse({ id: "V1", character_id: character.id, provider: "fake_voice", provider_voice_id: "", language: "en", style: "", locked: false, version: 1, provenance: character.identity_provenance }),
        );
      case "wardrobe":
        return Promise.resolve(jsonResponse([]));
      case "physical":
        return Promise.resolve(jsonResponse([]));
      case "assets":
        return Promise.resolve(jsonResponse([]));
      default:
        return Promise.resolve(jsonResponse({}));
    }
  });
}

describe("Character Studio (MODULE-058)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the cast roster with a link into each character", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/characters/S1");

    await waitFor(() => expect(screen.getByRole("link", { name: "Mara" })).toBeInTheDocument());
    expect(screen.getByText("protagonist")).toBeInTheDocument();
  });

  it("renders character detail: DNA, provenance, voice, and lock control", async () => {
    vi.stubGlobal("fetch", mockFetch());

    renderAt("/characters/S1/CHAR_001");

    await waitFor(() => expect(screen.getByRole("heading", { name: "Mara" })).toBeInTheDocument());
    expect(screen.getByText("Eyes: brown")).toBeInTheDocument();
    expect(screen.getByText(/Type: synthetic_original/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Provider: fake_voice/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Lock identity" })).toBeInTheDocument();
  });

  it("flags an unlicensed identity's missing consent reference", async () => {
    const unlicensed = {
      ...CHARACTER,
      identity_provenance: { identity_type: "licensed_authorized", consent_reference: "", notes: "" },
    };
    vi.stubGlobal("fetch", mockFetch(unlicensed));

    renderAt("/characters/S1/CHAR_001");

    await waitFor(() => expect(screen.getByText(/Type: licensed_authorized/)).toBeInTheDocument());
    expect(screen.getByText(/Type: licensed_authorized/)).toHaveClass("xr-detail__provenance--unknown");
  });

  it("shows a stale-asset warning before confirming a recast on a locked character", async () => {
    const locked = { ...CHARACTER, locked: true, version: 2 };
    vi.stubGlobal("fetch", mockFetch(locked));

    renderAt("/characters/S1/CHAR_001");

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Unlock for recast" })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/may become visually inconsistent/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Unlock for recast" }));

    expect(screen.getByText(/may become visually inconsistent/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm recast" })).toBeInTheDocument();
  });
});
