import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Outcome } from "../api/types";
import { jsonResponse, renderWithClient } from "../test/render";
import { ActiveSessionPanel } from "./ActiveSessionPanel";

afterEach(() => vi.restoreAllMocks());

const session = {
  content_id: "c1",
  content_title: "Clean Code",
  kind: "STUDY" as const,
  started_at: "2026-11-01T10:00:00Z",
  expires_at: "2026-11-01T14:00:00Z",
};

describe("ActiveSessionPanel", () => {
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
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(outcome));
    const onFinished = vi.fn();
    renderWithClient(
      <ActiveSessionPanel
        session={session}
        serverTime="2026-11-01T10:30:00Z"
        onFinished={onFinished}
      />,
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
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body).toEqual({ studied: "a b c", understood: "entendi", to_review: "revisar" });
  });

  it("avisa quanto falta para os 25 minutos", () => {
    renderWithClient(
      <ActiveSessionPanel
        session={session}
        serverTime="2026-11-01T10:10:00Z"
        onFinished={vi.fn()}
      />,
    );
    expect(screen.getByText(/Faltam 15:0\d para a sessão valer ponto/)).toBeInTheDocument();
  });

  it("numa revisão, exige dizer quanto lembrava e envia a nota", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        content_id: "c1",
        kind: "REVIEW",
        duration_seconds: 1500,
        awarded: true,
        reason: null,
        total_points: 11,
        level: "INTERMEDIATE",
        unlocked_content_id: null,
      }),
    );
    renderWithClient(
      <ActiveSessionPanel
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

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body.recall_rating).toBe(2);
  });

  it("numa sessão de estudo não pergunta a autoavaliação", () => {
    renderWithClient(
      <ActiveSessionPanel
        session={session}
        serverTime="2026-11-01T10:30:00Z"
        onFinished={vi.fn()}
      />,
    );
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });
});
