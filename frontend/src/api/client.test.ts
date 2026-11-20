import { afterEach, describe, expect, it, vi } from "vitest";
import { jsonResponse } from "../test/render";
import { ApiError, api } from "./client";

afterEach(() => vi.restoreAllMocks());

describe("api (port HTTP)", () => {
  it("envia o cabeçalho CSRF e credentials same-origin em comandos", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ kind: "STUDY" }, 201));
    await api.startSession("abc");
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/sessions");
    expect(init?.credentials).toBe("same-origin");
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-Requested-With"]).toBe("fetch");
    expect(init?.body).toBe(JSON.stringify({ content_id: "abc" }));
  });

  it("salva o caderno com keepalive (sobrevive a recarregar a página) quando cabe", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => jsonResponse({ version: 1 }));
    await api.saveNotebook("c1", "curto", 0);
    await api.saveNotebook("c1", "a".repeat(70_000), 1);
    expect(fetchMock.mock.calls[0]?.[1]?.keepalive).toBe(true);
    expect(fetchMock.mock.calls[1]?.[1]?.keepalive).toBeFalsy(); // limite de 64 KiB do navegador
  });

  it("não envia o cabeçalho CSRF em leituras", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse([]));
    await api.history();
    const init = fetchMock.mock.calls[0]?.[1];
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-Requested-With"]).toBeUndefined();
  });

  it("transforma erro do servidor em ApiError com a mensagem do domínio", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Refactoring está bloqueado", code: "ContentLockedError" }, 409),
    );
    const error = await api.startSession("x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "ContentLockedError" });
    expect((error as ApiError).message).toBe("Refactoring está bloqueado");
  });
});
