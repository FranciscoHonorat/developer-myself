import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Outcome } from "@/api/types";
import { callTo, jsonResponse, renderWithClient, routeFetch } from "@/test/render";
import { SessionPanel } from "./SessionPanel";

afterEach(() => vi.restoreAllMocks());

const session = {
  content_id: "c1",
  content_title: "Clean Code",
  kind: "STUDY" as const,
  started_at: "2026-11-01T10:00:00Z",
  expires_at: "2026-11-01T14:00:00Z",
  questions: [],
  last_to_review: null,
};

const review = {
  ...session,
  kind: "REVIEW" as const,
  last_to_review: "CQS",
  questions: [
    { id: "q1", text: "Explique sem consultar: CQS", source: "TO_REVIEW" as const },
    { id: "q2", text: "O que você lembra de nomes?", source: "SPACED_TOPIC" as const },
    { id: "q3", text: "Quando usar funções e quando não usar?", source: "TOPIC" as const },
  ],
};

afterEach(() => localStorage.clear());

/** Painel que some quando `register` é chamado — simula a tela vendo a sessão encerrada. */
function HidingHost(props: {
  onFinished: (o: Outcome) => void;
  register: (hide: () => void) => void;
}) {
  const [shown, setShown] = useState(true);
  props.register(() => setShown(false));
  return shown ? (
    <SessionPanel
      session={session}
      serverTime="2026-11-01T10:05:00Z"
      onFinished={props.onFinished}
    />
  ) : null;
}

describe("SessionPanel", () => {
  it('mostra o último "preciso revisar"', () => {
    renderWithClient(
      <SessionPanel
        session={{ ...session, last_to_review: "goroutines" }}
        serverTime="2026-11-01T10:30:00Z"
        onFinished={vi.fn()}
      />,
    );
    expect(screen.getByText("Da última vez você anotou para revisar:")).toBeInTheDocument();
    expect(screen.getByText("goroutines")).toBeInTheDocument();
  });

  it("outra sessão no lugar da atual começa do zero, sem herdar o rascunho", async () => {
    routeFetch();
    const { rerender } = renderWithClient(
      <SessionPanel session={review} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Conferir respostas" }));
    expect(await screen.findByLabelText("Caderno de Clean Code")).toBeInTheDocument();

    rerender(
      <SessionPanel
        session={{ ...review, started_at: "2026-11-01T11:00:00Z" }}
        serverTime="2026-11-01T11:05:00Z"
        onFinished={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Conferir respostas" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Caderno de Clean Code")).not.toBeInTheDocument();
  });

  it("na revisão o caderno só aparece depois de conferir", async () => {
    routeFetch();
    renderWithClient(
      <SessionPanel session={review} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Caderno de Clean Code")).not.toBeInTheDocument();
    expect(screen.queryByText("CQS")).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Conferir respostas" }));
    expect(await screen.findByLabelText("Caderno de Clean Code")).toBeInTheDocument();
    expect(screen.getByText("CQS")).toBeInTheDocument();
  });

  it("avisa o resultado mesmo quando o painel some antes da resposta chegar", async () => {
    let hide = () => {};
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.endsWith("/sessions/current/finish")) {
        hide(); // outra parte da tela já viu a sessão encerrada e desmontou o painel
        await new Promise((r) => setTimeout(r, 20));
        return jsonResponse({
          content_id: "c1",
          kind: "STUDY",
          duration_seconds: 300,
          awarded: false,
          reason: "TOO_SHORT",
          total_points: 0,
          level: "BEGINNER",
          unlocked_content_id: null,
        });
      }
      if (path.endsWith("/notebook"))
        return jsonResponse({ content_id: "c1", text: "", version: 0, updated_at: null });
      return jsonResponse([]);
    });
    const onFinished = vi.fn();
    renderWithClient(
      <HidingHost
        onFinished={onFinished}
        register={(h) => {
          hide = h;
        }}
      />,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("O que estudei"), "a".repeat(20));
    await user.type(screen.getByLabelText("O que entendi"), "b".repeat(20));
    await user.type(screen.getByLabelText("O que preciso revisar"), "c".repeat(20));
    await user.click(screen.getByRole("button", { name: "Finalizar sessão" }));

    await waitFor(() => expect(screen.queryByRole("timer")).not.toBeInTheDocument());
    await waitFor(() =>
      expect(onFinished).toHaveBeenCalledWith(expect.objectContaining({ reason: "TOO_SHORT" })),
    );
  });

  it("finalizar envia as respostas do teste", async () => {
    const fetchMock = routeFetch({
      "/sessions/current/finish": {
        content_id: "c1",
        kind: "REVIEW",
        duration_seconds: 1500,
        awarded: true,
        reason: null,
        total_points: 11,
        level: "INTERMEDIATE",
        unlocked_content_id: null,
      },
    });
    const onFinished = vi.fn();
    renderWithClient(
      <SessionPanel session={review} serverTime="2026-11-01T10:30:00Z" onFinished={onFinished} />,
    );
    const user = userEvent.setup();
    const finish = screen.getByRole("button", { name: "Finalizar sessão" });
    await user.type(screen.getByLabelText("Explique sem consultar: CQS"), "lembrei");
    await user.click(screen.getByRole("button", { name: "Conferir respostas" }));
    expect(screen.getByRole("radio", { name: /Difícil/ })).toBeDisabled();
    for (const group of screen.getAllByRole("radiogroup", { name: /Correção/ })) {
      await user.click(within(group).getByRole("radio", { name: "Errei" }));
    }
    await user.click(screen.getByRole("radio", { name: /Difícil/ }));
    expect(finish).toBeEnabled();
    await user.click(finish);

    await waitFor(() => expect(onFinished).toHaveBeenCalled());
    const body = JSON.parse(String(callTo(fetchMock, "/sessions/current/finish")?.[1]?.body));
    expect(body.recall_rating).toBe(2);
    expect(body.answers).toHaveLength(3);
    expect(body.answers[0]).toEqual({
      question_id: "q1",
      answer: "lembrei",
      grade: "MISSED",
      useful: null,
    });
    expect(localStorage.getItem(`recall:${review.started_at}`)).toBeNull();
  });

  it("sessão de estudo não mostra teste", () => {
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Conferir respostas" })).not.toBeInTheDocument();
  });

  it("conta caracteres sem espaços e envia as três anotações", async () => {
    const outcome: Outcome = {
      content_id: "c1",
      kind: "STUDY",
      duration_seconds: 1500,
      awarded: true,
      reason: null,
      total_points: 4,
      level: "BEGINNER",
      unlocked_content_id: null,
    };
    const fetchMock = routeFetch({ "/sessions/current/finish": outcome });
    const onFinished = vi.fn();
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:30:00Z" onFinished={onFinished} />,
    );
    expect(screen.getByRole("heading", { name: /Estudo: Clean Code/ })).toBeInTheDocument();
    expect(screen.getByText(/Tempo mínimo atingido/)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("O que estudei"), "a b c");
    expect(screen.getByText(/3\/50 caracteres/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("O que entendi"), "entendi");
    await user.type(screen.getByLabelText("O que preciso revisar"), "revisar");
    await user.click(screen.getByRole("button", { name: "Finalizar sessão" }));

    await waitFor(() => expect(onFinished).toHaveBeenCalledWith(outcome));
    const body = JSON.parse(String(callTo(fetchMock, "/sessions/current/finish")?.[1]?.body));
    expect(body).toEqual({ studied: "a b c", understood: "entendi", to_review: "revisar" });
  });

  it("mostra os passos e marca Responder como atual", async () => {
    routeFetch();
    renderWithClient(
      <SessionPanel session={review} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    const steps = screen.getByRole("list", { name: "Etapas do teste" });
    expect(within(steps).getByText("Responder").closest("li")).toHaveAttribute(
      "aria-current",
      "step",
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Conferir respostas" }));
    expect(within(steps).getByText("Conferir").closest("li")).toHaveAttribute(
      "aria-current",
      "step",
    );
  });

  it("timer usa role timer e mostra a expiração", () => {
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:10:00Z" onFinished={vi.fn()} />,
    );
    expect(screen.getByRole("timer", { name: "Tempo decorrido" })).toHaveTextContent("10:0");
    expect(screen.getByText(/expira/i)).toBeInTheDocument();
  });

  it("no celular o caderno abre em painel deslizante só depois de conferir", async () => {
    routeFetch();
    vi.spyOn(window, "matchMedia").mockImplementation(
      (q: string) =>
        ({
          matches: q.includes("max-width"),
          media: q,
          addEventListener: () => {},
          removeEventListener: () => {},
        }) as unknown as MediaQueryList,
    );
    renderWithClient(
      <SessionPanel session={review} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    const user = userEvent.setup();
    expect(screen.queryByRole("button", { name: "Abrir caderno" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Conferir respostas" }));
    expect(screen.queryByLabelText("Caderno de Clean Code")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Abrir caderno" }));
    const sheet = await screen.findByRole("dialog");
    expect(await within(sheet).findByLabelText("Caderno de Clean Code")).toBeInTheDocument();
  });

  it("cancelar pede confirmação em diálogo", async () => {
    const fetchMock = routeFetch();
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:10:00Z" onFinished={vi.fn()} />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Cancelar a sessão?" });
    expect(callTo(fetchMock, "/sessions/current/cancel")).toBeUndefined();
    await user.click(within(dialog).getByRole("button", { name: "Cancelar sessão" }));
    await waitFor(() => expect(callTo(fetchMock, "/sessions/current/cancel")).toBeDefined());
  });

  it("avisa quanto falta para os 25 minutos", () => {
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:10:00Z" onFinished={vi.fn()} />,
    );
    expect(screen.getByText(/Faltam 15:0\d para a sessão valer ponto/)).toBeInTheDocument();
  });

  it("numa revisão, exige dizer quanto lembrava e envia a nota", async () => {
    const fetchMock = routeFetch({
      "/sessions/current/finish": {
        content_id: "c1",
        kind: "REVIEW",
        duration_seconds: 1500,
        awarded: true,
        reason: null,
        total_points: 11,
        level: "INTERMEDIATE",
        unlocked_content_id: null,
      },
    });
    renderWithClient(
      <SessionPanel
        session={{ ...session, kind: "REVIEW" }}
        serverTime="2026-11-01T10:30:00Z"
        onFinished={vi.fn()}
      />,
    );
    const user = userEvent.setup();
    const finish = screen.getByRole("button", { name: "Finalizar sessão" });
    expect(screen.getByRole("radiogroup", { name: /quanto você lembrava/ })).toBeInTheDocument();
    expect(finish).toBeDisabled();

    await user.click(screen.getByRole("radio", { name: /Difícil/ }));
    expect(finish).toBeEnabled();
    await user.click(finish);

    await waitFor(() => expect(callTo(fetchMock, "/sessions/current/finish")).toBeDefined());
    const body = JSON.parse(String(callTo(fetchMock, "/sessions/current/finish")?.[1]?.body));
    expect(body.recall_rating).toBe(2);
  });

  it("mostra o caderno da matéria durante a sessão", async () => {
    routeFetch();
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    expect(await screen.findByLabelText("Caderno de Clean Code")).toBeInTheDocument();
  });

  it("numa sessão de estudo não pergunta a autoavaliação", () => {
    renderWithClient(
      <SessionPanel session={session} serverTime="2026-11-01T10:30:00Z" onFinished={vi.fn()} />,
    );
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });
});
