import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CompetencySheet, Plan, Stats, Today } from "../api/types";
import { makeBlock, makePlan, makeToday, makeTodayItem } from "../test/fixtures";
import { callTo, jsonResponse, makeContent, renderWithClient, routeFetch } from "../test/render";
import { TodayPage } from "./TodayPage";

afterEach(() => vi.restoreAllMocks());

const stats: Stats = {
  total_sessions: 12,
  total_points: 9,
  total_minutes: 600,
  current_streak_days: 6,
  withheld_by_reason: {},
  daily: [],
};

const sheet = (overrides: Partial<CompetencySheet> = {}): CompetencySheet => ({
  xp: 620,
  level: 4,
  next_level_xp: 1000,
  total_points: 9,
  competencies: [],
  effort: [],
  rules: { grace_days: 21, decay_per_day: 1, floor: 0 },
  ...overrides,
});

const review = makeTodayItem({ content_id: "c1", title: "Clean Code", day: 12 });
const study = makeTodayItem({ content_id: "c2", title: "Go", day: 3 });
const today = makeToday({
  reviews: [review],
  studies: [study],
  blocks: [makeBlock({ kind: "REVIEW", content_id: "c1", pomodoros: 2, minutes: 50 })],
});
const contents = [
  makeContent({ id: "c1", title: "Clean Code", status: "CONSOLIDATED" }),
  makeContent({ id: "c2", title: "Go" }),
];

function renderToday(opts: { plan?: Plan; today?: Today; sheet?: CompetencySheet } = {}) {
  const fetchMock = routeFetch({
    "/plan": opts.plan ?? makePlan({ contents, needs_review_today: true }),
    "/today": opts.today ?? today,
    "/stats?days=30": stats,
    "/competencies": opts.sheet ?? sheet(),
    "/sessions": { kind: "REVIEW" },
    "/week": {
      minutes_per_day: 210,
      rest_days: [6],
      pomodoro_minutes: 30,
      study_minutes: 25,
      days: [],
    },
  });
  renderWithClient(
    <MemoryRouter>
      <TodayPage />
    </MemoryRouter>,
  );
  return fetchMock;
}

describe("TodayPage", () => {
  it("mostra a sequência, o nível e o XP em destaque", async () => {
    renderToday();
    expect(await screen.findByText("6 dias seguidos")).toBeInTheDocument();
    expect(await screen.findByText("Nível 4")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "XP até o nível 5" })).toHaveAttribute(
      "aria-valuenow",
      "31", // nível 4 começa em 450 XP: (620−450)/(1000−450)
    );
  });

  it("alerta de skill enferrujando leva ao Progresso", async () => {
    renderToday({
      sheet: sheet({
        competencies: [
          {
            key: "go",
            name: "Go",
            area: "Backend",
            score: 40,
            peak: 50,
            rust_lost: 10,
            tier: "Praticante",
            title: "Praticante",
            target: null,
            target_score: null,
            points: 4,
            status: "enferrujando",
            rust_in_days: null,
            contents: [],
          },
        ],
      }),
    });
    const link = await screen.findByRole("link", { name: /Go está enferrujando/ });
    expect(link).toHaveAttribute("href", "/progresso?aba=competencias");
  });

  it("cartão Próximo passo tem o título e o botão Iniciar revisão", async () => {
    const fetchMock = renderToday();
    const start = await screen.findByRole("button", { name: "Iniciar revisão" });
    expect(screen.getByRole("heading", { name: "Clean Code" })).toBeInTheDocument();
    expect(screen.getByText(/Revise antes de estudar/)).toBeInTheDocument();
    await userEvent.setup().click(start);
    await waitFor(() => expect(callTo(fetchMock, "/sessions")).toBeDefined());
    const body = JSON.parse(String(callTo(fetchMock, "/sessions")?.[1]?.body));
    expect(body).toEqual({ content_id: "c1" });
  });

  it("o resto do dia lista os blocos com estado", async () => {
    renderToday();
    const list = await screen.findByRole("list", { name: "Resto do dia" });
    expect(list).toHaveTextContent("Go");
  });

  it("com sessão ativa o cartão dá lugar ao painel da sessão", async () => {
    renderToday({
      plan: makePlan({
        contents,
        active_session: {
          content_id: "c1",
          content_title: "Clean Code",
          kind: "REVIEW",
          started_at: "2026-11-20T12:50:00Z",
          expires_at: "2026-11-20T16:50:00Z",
          questions: [],
          last_to_review: null,
        },
      }),
    });
    expect(await screen.findByRole("heading", { name: /Revisão: Clean Code/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Iniciar revisão" })).not.toBeInTheDocument();
  });

  it("dia concluído mostra o resumo e mantém a sequência", async () => {
    renderToday({
      plan: makePlan({
        contents: [
          makeContent({
            id: "c1",
            status: "CONSOLIDATED",
            last_session_at: "2026-11-20T12:00:00Z",
          }),
          makeContent({ id: "c2", title: "Go", last_session_at: "2026-11-20T13:00:00Z" }),
        ],
        reviewed_today: true,
      }),
    });
    expect(await screen.findByText("Dia concluído")).toBeInTheDocument();
    expect(await screen.findByText("6 dias seguidos")).toBeInTheDocument();
  });

  it("Ver semana abre a grade e as preferências", async () => {
    renderToday();
    await userEvent.setup().click(await screen.findByRole("button", { name: "Ver semana" }));
    expect(await screen.findByRole("button", { name: "Salvar ritmo" })).toBeInTheDocument();
  });

  it("trilha vazia mostra o guia no lugar do Próximo passo", async () => {
    renderToday({ plan: makePlan({ contents: [] }), today: makeToday() });
    expect(
      await screen.findByRole("heading", { name: "Adicione seu primeiro conteúdo" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Iniciar/ })).not.toBeInTheDocument();
  });

  it("concluir os 2 passos mostra o Próximo passo com Iniciar", async () => {
    let contents: ReturnType<typeof makeContent>[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith("/contents") && init?.method === "POST") {
        contents = [makeContent({ id: "c1", title: "Docker" })];
        return jsonResponse(contents[0]);
      }
      if (path.endsWith("/plan")) return jsonResponse(makePlan({ contents }));
      if (path.endsWith("/today"))
        return jsonResponse(
          contents.length
            ? makeToday({ studies: [makeTodayItem({ content_id: "c1", title: "Docker" })] })
            : makeToday(),
        );
      if (path.endsWith("/plan/preferences")) return jsonResponse(null, 204);
      if (path.includes("/stats")) return jsonResponse(stats);
      if (path.endsWith("/competencies")) return jsonResponse(sheet());
      return jsonResponse({
        minutes_per_day: 210,
        rest_days: [],
        pomodoro_minutes: 30,
        study_minutes: 25,
        days: [],
      });
    });
    renderWithClient(
      <MemoryRouter>
        <TodayPage />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Título"), "Docker");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(
      await screen.findByRole("heading", { name: "Quanto tempo por dia?" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Começar" }));
    expect(await screen.findByRole("button", { name: "Iniciar estudo" })).toBeInTheDocument();
  });

  it("Pular esconde o guia nesta visita", async () => {
    renderToday({ plan: makePlan({ contents: [] }), today: makeToday() });
    await userEvent.setup().click(await screen.findByRole("button", { name: "Pular" }));
    expect(
      screen.queryByRole("heading", { name: "Adicione seu primeiro conteúdo" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Nada planejado para hoje")).toBeInTheDocument();
  });
});
