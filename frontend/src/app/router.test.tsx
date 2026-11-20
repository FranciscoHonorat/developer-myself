import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Plan } from "../api/types";
import { jsonResponse, makeContent, renderWithClient } from "../test/render";
import { createAppRouter } from "./router";

afterEach(() => vi.restoreAllMocks());

const ME = { id: "u1", email: "eu@exemplo.com", created_at: "2026-11-01T10:00:00Z" };

function plan(overrides: Partial<Plan> = {}): Plan {
  return {
    timezone: "America/Sao_Paulo",
    preferences: { minutes_per_day: 210, rest_days: [] },
    max_in_progress: 3,
    server_time: "2026-11-20T10:00:00Z",
    last_review_on: null,
    reviewed_today: false,
    needs_review_today: false,
    active_session: null,
    contents: [makeContent()],
    ...overrides,
  };
}

/** API falsa: `/auth/me` responde conforme `loggedIn`; login liga a sessão. */
function fakeApi(opts: { loggedIn: boolean; plan?: Plan }) {
  let loggedIn = opts.loggedIn;
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path.endsWith("/auth/me"))
      return loggedIn
        ? jsonResponse(ME)
        : jsonResponse({ detail: "Faça login.", code: "NotAuthenticatedError" }, 401);
    if (path.endsWith("/auth/login") && init?.method === "POST") {
      loggedIn = true;
      return jsonResponse(null, 204);
    }
    if (path.endsWith("/plan")) return jsonResponse(opts.plan ?? plan());
    if (path.endsWith("/today")) return jsonResponse({ studies: [], reviews: [], blocks: [] });
    if (path.endsWith("/week"))
      return jsonResponse({
        minutes_per_day: 210,
        rest_days: [],
        pomodoro_minutes: 30,
        study_minutes: 25,
        days: [],
      });
    if (path.endsWith("/notebook")) {
      return jsonResponse({ content_id: "c1", text: "", version: 0, updated_at: null });
    }
    if (path.includes("/stats"))
      return jsonResponse({
        total_sessions: 0,
        total_points: 0,
        total_minutes: 0,
        current_streak_days: 0,
        withheld_by_reason: {},
        daily: [],
      });
    return jsonResponse([]);
  });
}

function renderAt(path: string) {
  const router = createAppRouter({ initialEntries: [path] });
  renderWithClient(<RouterProvider router={router} />);
  return router;
}

const nav = () => screen.findByRole("navigation", { name: "Seções" });

describe("rotas e casca", () => {
  it("/ logado redireciona para /hoje e marca Hoje como atual", async () => {
    fakeApi({ loggedIn: true });
    const router = renderAt("/");
    const navigation = await nav();
    await waitFor(() =>
      expect(within(navigation).getByRole("link", { name: "Hoje" })).toHaveAttribute(
        "aria-current",
        "page",
      ),
    );
    expect(router.state.location.pathname).toBe("/hoje");
  });

  it("a navegação tem as 4 seções e a conta", async () => {
    fakeApi({ loggedIn: true });
    renderAt("/hoje");
    const links = within(await nav()).getAllByRole("link");
    const names = links.map((l) => l.getAttribute("aria-label") ?? l.textContent);
    expect(names).toEqual(
      expect.arrayContaining(["Hoje", "Trilha", "Caderno", "Progresso", "Conta"]),
    );
  });

  it("deslogado em /caderno/c1 vai para /entrar e volta para /caderno/c1 após login", async () => {
    fakeApi({ loggedIn: false });
    const router = renderAt("/caderno/c1");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("E-mail"), "eu@exemplo.com");
    expect(router.state.location.pathname).toBe("/entrar");
    await user.type(screen.getByLabelText("Senha"), "senha-forte-123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/caderno/c1"));
    expect(await screen.findByLabelText("Caderno de Clean Code")).toBeInTheDocument();
  });

  it("logado em /entrar vai para /hoje", async () => {
    fakeApi({ loggedIn: true });
    const router = renderAt("/entrar");
    await nav();
    expect(router.state.location.pathname).toBe("/hoje");
  });

  it("F5 em /progresso?aba=historico abre o histórico", async () => {
    fakeApi({ loggedIn: true });
    renderAt("/progresso?aba=historico");
    expect(
      await screen.findByRole("tab", { name: "Histórico", selected: true }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Sessões" })).toBeInTheDocument();
  });

  it("com sessão ativa, fora do Hoje, o indicador mostra o título e leva ao Hoje", async () => {
    fakeApi({
      loggedIn: true,
      plan: plan({
        active_session: {
          content_id: "c1",
          content_title: "Clean Code",
          kind: "STUDY",
          started_at: "2026-11-20T09:50:00Z",
          expires_at: "2026-11-20T13:50:00Z",
          questions: [],
          last_to_review: null,
        },
      }),
    });
    const router = renderAt("/trilha");
    const indicator = await screen.findByRole("link", { name: "Sessão em andamento: Clean Code" });
    await userEvent.setup().click(indicator);
    expect(router.state.location.pathname).toBe("/hoje");
  });
});
