import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Plan } from "@/api/types";
import { makeContent, renderWithClient, routeFetch } from "@/test/render";
import { NotebookPage } from "./NotebookPage";

afterEach(() => vi.restoreAllMocks());

function plan(contents: Plan["contents"]): Plan {
  return {
    timezone: "America/Sao_Paulo",
    preferences: { minutes_per_day: 210, rest_days: [] },
    max_in_progress: 3,
    server_time: "2026-11-17T10:00:00Z",
    last_review_on: null,
    reviewed_today: false,
    needs_review_today: false,
    active_session: null,
    contents,
  };
}

function renderAt(path = "/caderno") {
  const router = createMemoryRouter(
    [
      { path: "/caderno", element: <NotebookPage /> },
      { path: "/caderno/:contentId", element: <NotebookPage /> },
    ],
    { initialEntries: [path] },
  );
  renderWithClient(<RouterProvider router={router} />);
  return router;
}

const mobile = () =>
  vi.spyOn(window, "matchMedia").mockImplementation(
    (q: string) =>
      ({
        matches: q.includes("max-width"),
        media: q,
        addEventListener: () => {},
        removeEventListener: () => {},
      }) as unknown as MediaQueryList,
  );

describe("NotebookPage", () => {
  it("lista as matérias e abre o caderno ao clicar", async () => {
    routeFetch({
      "/plan": plan([
        makeContent(),
        makeContent({ id: "c2", title: "Refactoring", status: "LOCKED" }),
      ]),
      "/notebooks": [{ content_id: "c1", chars: 12, updated_at: "2026-11-16T10:00:00Z" }],
      "/contents/c1/notebook": {
        content_id: "c1",
        text: "Nomes revelam intenção",
        version: 1,
        updated_at: "2026-11-16T10:00:00Z",
      },
    });
    renderAt();

    expect(await screen.findByText(/12 caracteres/)).toBeInTheDocument();
    expect(screen.getByText("Escolha uma matéria.")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("link", { name: /Clean Code/ }));
    expect(await screen.findByDisplayValue("Nomes revelam intenção")).toBeInTheDocument();
    expect(screen.getByLabelText("Caderno de Clean Code")).toBeInTheDocument();
  });

  it("durante o teste de memória o caderno da matéria fica só no painel da sessão", async () => {
    routeFetch({
      "/plan": {
        ...plan([makeContent({ status: "CONSOLIDATED" })]),
        active_session: {
          content_id: "c1",
          content_title: "Clean Code",
          kind: "REVIEW",
          started_at: "2026-11-17T09:50:00Z",
          expires_at: "2026-11-17T13:50:00Z",
          questions: [{ id: "q1", text: "Explique sem consultar", source: "TOPIC" }],
          last_to_review: null,
        },
      },
    });
    renderAt();

    await userEvent.setup().click(await screen.findByRole("link", { name: /Clean Code/ }));
    expect(screen.getByText(/Teste de memória em andamento/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Caderno de Clean Code")).not.toBeInTheDocument();
  });

  it("sem conteúdos mostra o convite", async () => {
    routeFetch({ "/plan": plan([]) });
    renderAt();
    expect(
      await screen.findByText(
        (_, el) =>
          el?.tagName === "P" &&
          el.textContent === "Adicione um conteúdo na Trilha para ter um caderno.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Trilha" })).toHaveAttribute("href", "/trilha");
  });

  it("clicar numa matéria vai para /caderno/<id> e abre o editor", async () => {
    routeFetch({ "/plan": plan([makeContent()]) });
    const router = renderAt();
    await userEvent.setup().click(await screen.findByRole("link", { name: /Clean Code/ }));
    expect(router.state.location.pathname).toBe("/caderno/c1");
    expect(await screen.findByLabelText("Caderno de Clean Code")).toBeInTheDocument();
  });

  it("no celular, com matéria aberta, a lista some e há Voltar", async () => {
    mobile();
    routeFetch({ "/plan": plan([makeContent()]) });
    const router = renderAt("/caderno/c1");
    expect(await screen.findByLabelText("Caderno de Clean Code")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Matérias" })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("link", { name: "Voltar às matérias" }));
    expect(router.state.location.pathname).toBe("/caderno");
    expect(await screen.findByRole("navigation", { name: "Matérias" })).toBeInTheDocument();
  });
});
