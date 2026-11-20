import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Content } from "@/api/types";
import { callTo, makeContent, renderWithClient, routeFetch } from "@/test/render";
import { ContentCard } from "./ContentCard";

afterEach(() => vi.restoreAllMocks());

function renderCard(content: Content, opts: { active?: boolean; notebookLocked?: boolean } = {}) {
  const router = createMemoryRouter(
    [
      {
        path: "/trilha",
        element: (
          <ContentCard
            content={content}
            hasActiveSession={opts.active ?? false}
            notebookLocked={opts.notebookLocked ?? false}
          />
        ),
      },
      { path: "*", element: <p>outra página</p> },
    ],
    { initialEntries: ["/trilha"] },
  );
  renderWithClient(<RouterProvider router={router} />);
  return router;
}

async function openMenu(title = "Clean Code") {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: `Mais ações para ${title}` }));
  return { user, menu: await screen.findByRole("menu") };
}

describe("ContentCard", () => {
  it("é um article com o título como nome", () => {
    renderCard(makeContent());
    expect(screen.getByRole("article", { name: "Clean Code" })).toBeInTheDocument();
  });

  it("o caderno abre pela rota da matéria", async () => {
    renderCard(makeContent());
    const { menu } = await openMenu();
    expect(within(menu).getByRole("menuitem", { name: /Caderno/ })).toHaveAttribute(
      "href",
      "/caderno/c1",
    );
  });

  it("durante o teste de memória deste conteúdo não oferece o caderno", async () => {
    renderCard(makeContent(), { active: true, notebookLocked: true });
    const { menu } = await openMenu();
    expect(within(menu).queryByRole("menuitem", { name: /Caderno/ })).not.toBeInTheDocument();
  });

  it("mostra pontos e o progresso até o próximo nível", () => {
    renderCard(makeContent());
    expect(screen.getByRole("heading", { name: "Clean Code" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Pontos" })).toHaveAttribute(
      "aria-valuenow",
      "3",
    );
    expect(screen.getByRole("progressbar", { name: "Desafios" })).toHaveAttribute(
      "aria-valuemax",
      "3",
    );
    expect(screen.getByRole("button", { name: /Estudar/ })).toBeEnabled();
  });

  it("conteúdo bloqueado mostra o motivo e não deixa iniciar sessão", () => {
    renderCard(
      makeContent({
        status: "LOCKED",
        queue_position: 1,
        lock_reason:
          "Refactoring está bloqueado: conclua Clean Code ou chegue a Intermediário nele.",
        title: "Refactoring",
      }),
    );
    expect(screen.getByText(/conclua Clean Code/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Estudar|Revisar/ })).not.toBeInTheDocument();
  });

  it("conteúdo consolidado oferece revisão", () => {
    renderCard(makeContent({ status: "CONSOLIDATED" }));
    expect(screen.getByRole("button", { name: /Revisar/ })).toBeInTheDocument();
  });

  it("desabilita iniciar quando já há uma sessão ativa", () => {
    renderCard(makeContent(), { active: true });
    expect(screen.getByRole("button", { name: /Estudar/ })).toBeDisabled();
  });

  it("iniciar leva ao Hoje, onde fica o painel da sessão", async () => {
    const fetchMock = routeFetch({ "/sessions": { kind: "STUDY" } });
    const router = renderCard(makeContent());
    await userEvent.setup().click(screen.getByRole("button", { name: /Estudar/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/hoje"));
    expect(callTo(fetchMock, "/sessions")).toBeDefined();
  });

  it("só deixa concluir no nível Avançado", async () => {
    renderCard(makeContent({ status: "CONSOLIDATED", level: "INTERMEDIATE" }));
    expect(screen.getByText(/Chegue a Avançado para concluir/)).toBeInTheDocument();
    const { menu } = await openMenu();
    expect(within(menu).getByRole("menuitem", { name: /Concluir/ })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("no nível Avançado concluir pede confirmação", async () => {
    const fetchMock = routeFetch();
    renderCard(makeContent({ status: "CONSOLIDATED", level: "ADVANCED", next_level: null }));
    expect(screen.queryByText(/Chegue a Avançado/)).not.toBeInTheDocument();
    const { user, menu } = await openMenu();
    await user.click(within(menu).getByRole("menuitem", { name: /Concluir/ }));
    const dialog = await screen.findByRole("alertdialog", {
      name: /Marcar .*Clean Code.* como concluído/,
    });
    await user.click(within(dialog).getByRole("button", { name: "Concluir" }));
    await waitFor(() => expect(callTo(fetchMock, "/contents/c1/finish")).toBeDefined());
  });

  it("só oferece remover conteúdo sem progresso, com confirmação", async () => {
    const fetchMock = routeFetch();
    renderCard(makeContent({ points: 0 }));
    const { user, menu } = await openMenu();
    expect(within(menu).getByRole("menuitem", { name: /Cronograma/ })).toBeInTheDocument();
    await user.click(within(menu).getByRole("menuitem", { name: /Remover/ }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Remover" }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(true),
    );
  });

  it("conteúdo com progresso não oferece remover", async () => {
    renderCard(makeContent({ points: 2 }));
    const { menu } = await openMenu();
    expect(within(menu).queryByRole("menuitem", { name: /Remover/ })).not.toBeInTheDocument();
  });
});
