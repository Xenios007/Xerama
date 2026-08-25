import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../api/client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on a successful response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "P1", name: "Trial 01" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.get<{ id: string; name: string }>("/projects/P1");
    expect(result).toEqual({ id: "P1", name: "Trial 01" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/P1"),
      expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) }),
    );
  });

  it("throws ApiError with the backend's detail message on failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "project not found" }), { status: 404, statusText: "Not Found" }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.get("/projects/missing")).rejects.toMatchObject(
      new ApiError(404, "project not found"),
    );
  });

  it("falls back to statusText when the error body isn't JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("oops", { status: 500, statusText: "Server Error" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.get("/anything")).rejects.toMatchObject({ status: 500, detail: "Server Error" });
  });

  it("sends a JSON body on post", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await api.post("/projects", { name: "New" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ name: "New" }));
  });
});
