import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makePlan } from "@/test/fixtures";
import { callTo, makeContent, renderWithClient, routeFetch } from "@/test/render";
import { TrailPage } from "./TrailPage";

afterEach(() => vi.restoreAllMocks());

const plan = makePlan({
  contents: [
    makeContent({ id: "c1", title: "Clean Code" }),
    makeContent({ id: "c2", title: "Redes", status: "CONSOLIDATED" }),
    makeContent({
      id: "c3",
      title: "Refactoring",
      status: "LOCKED",
      queue_position: 1,
      lock_reason: "conclua Clean Code ou chegue a Intermediário nele.",
    }),
  ],
});

function renderTrail() {
  const fetchMock = routeFetch({ "/plan": plan, "/contents": makeContent({ id: "c9" }) });
  renderWithClient(
    <MemoryRouter>
      <TrailPage />
    </MemoryRouter>,
  );
  return fetchMock;
}

describe("TrailPage", () => {
  it("seções Em andamento (com vagas), Para revisar e Fila", async () => {
    renderTrail();
    const current = await screen.findByRole("region", { name: /Em andamento/ });
    expect(within(current).getByText("1/3 vagas")).toBeInTheDocument();
    expect(within(current).getByRole("article", { name: "Clean Code" })).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Para revisar" })).getByRole("article", {
        name: "Redes",
      }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Fila" })).getByText(/conclua Clean Code/),
    ).toBeInTheDocument();
  });

  it("Adicionar conteúdo abre diálogo e cria", async () => {
    const fetchMock = renderTrail();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Adicionar conteúdo" }));
    const dialog = await screen.findByRole("dialog", { name: "Adicionar conteúdo" });
    await user.type(within(dialog).getByLabelText("Título"), "Docker");
    await user.click(within(dialog).getByRole("button", { name: "Adicionar" }));
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([input, init]) => String(input).endsWith("/contents") && init?.method === "POST",
      );
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ title: "Docker", kind: "BOOK" });
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("título em branco não envia", async () => {
    const fetchMock = renderTrail();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Adicionar conteúdo" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Adicionar" }));
    expect(callTo(fetchMock, "/contents")).toBeUndefined();
  });

  describe("paginação", () => {
    const longQueue = makePlan({
      contents: [
        makeContent({ id: "c1", title: "Clean Code" }),
        ...Array.from({ length: 8 }, (_, i) =>
          makeContent({
            id: `q${i + 1}`,
            title: `Fila ${i + 1}`,
            status: "LOCKED",
            queue_position: i + 1,
          }),
        ),
      ],
    });

    function renderQueue(path = "/trilha") {
      routeFetch({ "/plan": longQueue });
      const router = createMemoryRouter([{ path: "/trilha", element: <TrailPage /> }], {
        initialEntries: [path],
      });
      renderWithClient(<RouterProvider router={router} />);
      return router;
    }

    const queueTitles = () =>
      within(screen.getByRole("region", { name: "Fila" }))
        .getAllByRole("article")
        .map((a) => a.getAttribute("aria-label"));

    it("mostra 6 por página e avança pela fila na ordem", async () => {
      const router = renderQueue();
      await screen.findByRole("region", { name: "Fila" });
      expect(queueTitles()).toEqual(["Fila 1", "Fila 2", "Fila 3", "Fila 4", "Fila 5", "Fila 6"]);
      await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
      expect(queueTitles()).toEqual(["Fila 7", "Fila 8"]);
      expect(router.state.location.search).toBe("?fila=2");
    });

    it("abre direto na página da URL (F5)", async () => {
      renderQueue("/trilha?fila=2");
      await screen.findByRole("region", { name: "Fila" });
      expect(queueTitles()).toEqual(["Fila 7", "Fila 8"]);
      expect(screen.getByRole("navigation", { name: "Páginas de Fila" })).toHaveTextContent(
        "Página 2 de 2",
      );
    });

    it("seção que cabe numa página não mostra controles", async () => {
      renderTrail();
      await screen.findByRole("region", { name: "Fila" });
      expect(screen.queryByRole("navigation", { name: /Páginas de/ })).not.toBeInTheDocument();
    });
  });
});
