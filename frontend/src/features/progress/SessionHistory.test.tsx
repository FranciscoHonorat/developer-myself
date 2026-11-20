import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SessionRecord } from "@/api/types";
import { callTo, renderWithClient, routeFetch } from "@/test/render";
import { SessionHistory } from "./SessionHistory";

afterEach(() => vi.restoreAllMocks());

const stats = {
  total_sessions: 1,
  total_points: 1,
  total_minutes: 30,
  current_streak_days: 1,
  withheld_by_reason: {},
  daily: [],
};

const review: SessionRecord = {
  event_id: "e1",
  type: "study_session_finished",
  content_id: "c1",
  content_title: "Clean Code",
  kind: "REVIEW",
  started_at: "2026-11-01T10:00:00Z",
  finished_at: "2026-11-01T10:30:00Z",
  duration_seconds: 1800,
  awarded: true,
  reason: null,
  notes_studied: "a",
  notes_understood: "b",
  notes_to_review: "c",
  level_after: "INTERMEDIATE",
  recall_rating: 2,
  recall_test: [
    {
      text: "Explique sem consultar: CQS",
      source: "TO_REVIEW",
      answer: "comando muda, consulta lê",
      grade: "PARTIAL",
      useful: true,
    },
  ],
};

describe("SessionHistory", () => {
  it("mostra o teste de memória da revisão", async () => {
    routeFetch({
      "/history?limit=20": { items: [review], next_cursor: null },
      "/stats?days=30": stats,
    });
    renderWithClient(<SessionHistory />);
    expect(await screen.findByText("Explique sem consultar: CQS")).toBeInTheDocument();
    expect(screen.getByText("comando muda, consulta lê")).toBeInTheDocument();
    expect(screen.getByText("Parcial")).toBeInTheDocument();
  });

  it("sessão sem teste não mostra a seção", async () => {
    routeFetch({
      "/history?limit=20": { items: [{ ...review, recall_test: [] }], next_cursor: null },
      "/stats?days=30": stats,
    });
    renderWithClient(<SessionHistory />);
    expect(await screen.findByText(/Clean Code/)).toBeInTheDocument();
    expect(screen.queryByText("Teste de memória")).not.toBeInTheDocument();
  });

  it("topo mostra sequência, pontos, sessões e horas dos 30 dias", async () => {
    routeFetch({
      "/stats?days=30": {
        ...stats,
        total_sessions: 12,
        total_points: 9,
        total_minutes: 600,
        current_streak_days: 6,
      },
    });
    renderWithClient(<SessionHistory />);
    const summary = await screen.findByRole("region", { name: "Estatísticas dos últimos 30 dias" });
    expect(summary).toHaveTextContent("6 dias");
    expect(summary).toHaveTextContent("9");
    expect(summary).toHaveTextContent("12");
    expect(summary).toHaveTextContent("10.0");
    expect(await screen.findByText("Nenhuma sessão ainda.")).toBeInTheDocument();
  });

  it("carrega a página seguinte do histórico pelo cursor", async () => {
    const older = { ...review, event_id: "e0", content_title: "Refactoring", recall_test: [] };
    const fetchMock = routeFetch({
      "/history?limit=20": { items: [review], next_cursor: "abc" },
      "/history?limit=20&cursor=abc": { items: [older], next_cursor: null },
      "/stats?days=30": stats,
    });
    renderWithClient(<SessionHistory />);
    await userEvent.click(await screen.findByRole("button", { name: "Carregar mais" }));
    expect(await screen.findByText("Refactoring")).toBeInTheDocument();
    expect(screen.getByText("Clean Code")).toBeInTheDocument();
    expect(callTo(fetchMock, "/history?limit=20&cursor=abc")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Carregar mais" })).not.toBeInTheDocument();
  });
});
