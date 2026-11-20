import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Notebook } from "@/api/types";
import { NotebookEditor } from "@/features/notebook/NotebookEditor";
import { jsonResponse, renderWithClient } from "@/test/render";

const LABEL = "Caderno de Clean Code";
const URL = "/api/contents/c1/notebook";

function notebook(overrides: Partial<Notebook> = {}): Notebook {
  return { content_id: "c1", text: "antes", version: 3, updated_at: null, ...overrides };
}

type PutHandler = (body: { text: string; version: number }) => Promise<Response>;

/** Roteia o fetch: GET devolve o caderno; PUT chama o handler do teste. */
function mockApi(put: PutHandler, get: () => Notebook = () => notebook()) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const method = init?.method ?? "GET";
    if (String(input) === URL && method === "GET") return jsonResponse(get());
    if (String(input) === URL && method === "PUT") return put(JSON.parse(String(init?.body)));
    return jsonResponse([]);
  });
}

const puts = (fetchMock: ReturnType<typeof mockApi>) =>
  fetchMock.mock.calls
    .filter(([, init]) => init?.method === "PUT")
    .map(([, init]) => JSON.parse(String(init?.body)));

const okPut: PutHandler = async (body) =>
  jsonResponse(notebook({ text: body.text, version: body.version + 1 }));

/** Carrega com timers reais e só então congela o relógio do debounce. */
async function renderLoaded() {
  const view = renderWithClient(<NotebookEditor contentId="c1" title="Clean Code" />);
  const field = await screen.findByLabelText(LABEL);
  await screen.findByDisplayValue("antes");
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  return { ...view, field };
}

async function tick(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
  });
  // deixa as promises do fetch e do React assentarem
  for (let i = 0; i < 5; i++) await act(async () => {});
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("NotebookEditor", () => {
  it("carrega o texto do caderno", async () => {
    mockApi(okPut);
    const { field } = await renderLoaded();
    expect(field).toHaveValue("antes");
  });

  it("salva 1 s depois de parar de digitar, uma vez só", async () => {
    const fetchMock = mockApi(okPut);
    const { field } = await renderLoaded();

    fireEvent.change(field, { target: { value: "antesa" } });
    fireEvent.change(field, { target: { value: "antesab" } });
    fireEvent.change(field, { target: { value: "antesabc" } });
    expect(screen.getByRole("status")).toHaveTextContent("Alterações não salvas");

    await tick(999);
    expect(puts(fetchMock)).toEqual([]);

    await tick(1);
    expect(puts(fetchMock)).toEqual([{ text: "antesabc", version: 3 }]);
    expect(screen.getByRole("status")).toHaveTextContent(/Salvo às \d\d:\d\d/);
  });

  it("usa a versão nova se editar durante o salvamento", async () => {
    let release: (r: Response) => void = () => {};
    const first = new Promise<Response>((resolve) => {
      release = resolve;
    });
    let calls = 0;
    const fetchMock = mockApi(async (body) => {
      calls += 1;
      return calls === 1 ? first : okPut(body);
    });
    const { field } = await renderLoaded();

    fireEvent.change(field, { target: { value: "um" } });
    await tick(1000);
    expect(screen.getByRole("status")).toHaveTextContent("Salvando…");

    fireEvent.change(field, { target: { value: "um dois" } });
    await tick(1000); // o 1º ainda está em voo: não dispara um segundo em paralelo
    expect(puts(fetchMock)).toHaveLength(1);

    await act(async () => release(jsonResponse(notebook({ text: "um", version: 4 }))));
    await tick(0);
    expect(puts(fetchMock)).toEqual([
      { text: "um", version: 3 },
      { text: "um dois", version: 4 },
    ]);
  });

  it("em conflito para de salvar e oferece recarregar", async () => {
    let getCalls = 0;
    const fetchMock = mockApi(
      async () => jsonResponse({ detail: "mudou", code: "NotebookConflictError" }, 409),
      () => {
        getCalls += 1;
        return getCalls === 1 ? notebook() : notebook({ text: "da outra aba", version: 5 });
      },
    );
    const { field } = await renderLoaded();

    fireEvent.change(field, { target: { value: "minha versão" } });
    await tick(1000);
    expect(screen.getByRole("status")).toHaveTextContent("Editado em outro lugar.");

    expect(field).toHaveAttribute("readonly"); // nada digitado depois do conflito se perde
    await tick(2000);
    expect(puts(fetchMock)).toHaveLength(1);
  });

  it("ao recarregar depois do conflito, guarda o rascunho e volta a salvar", async () => {
    let getCalls = 0;
    let putCalls = 0;
    const fetchMock = mockApi(
      async (body) => {
        putCalls += 1;
        return putCalls === 1
          ? jsonResponse({ detail: "mudou", code: "NotebookConflictError" }, 409)
          : okPut(body);
      },
      () => {
        getCalls += 1;
        return getCalls === 1 ? notebook() : notebook({ text: "da outra aba", version: 5 });
      },
    );
    const { field } = await renderLoaded();
    fireEvent.change(field, { target: { value: "minha versão" } });
    await tick(1000);

    vi.useRealTimers();
    fireEvent.click(screen.getByRole("button", { name: "Recarregar" }));
    const merged = "da outra aba\n\n— rascunho não salvo —\nminha versão";
    expect(await screen.findByDisplayValue(merged, { normalizer: (t) => t })).toBeInTheDocument();
    expect(field).not.toHaveAttribute("readonly");
    await waitFor(() => expect(puts(fetchMock)).toHaveLength(2), { timeout: 3000 });
    expect(puts(fetchMock)[1]).toEqual({ text: merged, version: 5 });
  });

  it("duas cópias do mesmo caderno na tela se acompanham sem conflito", async () => {
    const fetchMock = mockApi(okPut);
    renderWithClient(
      <>
        <NotebookEditor contentId="c1" title="Clean Code" />
        <NotebookEditor contentId="c1" title="Clean Code" />
      </>,
    );
    await waitFor(() => expect(screen.getAllByDisplayValue("antes")).toHaveLength(2));
    const [a, b] = screen.getAllByLabelText(LABEL);
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });

    fireEvent.change(a as HTMLElement, { target: { value: "escrito no painel" } });
    await tick(1000);
    await tick(0); // o TanStack Query avisa os observadores num setTimeout(0)
    expect(b).toHaveValue("escrito no painel");

    fireEvent.change(b as HTMLElement, { target: { value: "continuado no card" } });
    await tick(1000);
    expect(puts(fetchMock)).toEqual([
      { text: "escrito no painel", version: 3 },
      { text: "continuado no card", version: 4 },
    ]);
  });

  it("avisa antes de sair da página com alteração não salva", async () => {
    mockApi(okPut);
    const { field } = await renderLoaded();
    const clean = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(clean);
    expect(clean.defaultPrevented).toBe(false);

    fireEvent.change(field, { target: { value: "pendente" } });
    const dirty = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(dirty);
    expect(dirty.defaultPrevented).toBe(true);
  });

  it("salva na hora ao desmontar com alteração pendente", async () => {
    const fetchMock = mockApi(okPut);
    const { field, unmount } = await renderLoaded();

    fireEvent.change(field, { target: { value: "escrevi e finalizei" } });
    unmount();
    await tick(0);
    expect(puts(fetchMock)).toEqual([{ text: "escrevi e finalizei", version: 3 }]);
  });
});
