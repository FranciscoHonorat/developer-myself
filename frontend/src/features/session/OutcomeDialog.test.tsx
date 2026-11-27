import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithClient } from "@/test/render";
import { OutcomeDialog } from "./OutcomeDialog";

describe("OutcomeDialog", () => {
  it("explica por que a sessão não pontuou (resposta do servidor)", () => {
    renderWithClient(
      <OutcomeDialog
        onClose={vi.fn()}
        outcome={{
          content_id: "c1",
          kind: "STUDY",
          duration_seconds: 1800,
          awarded: false,
          reason: "NO_REVIEW",
          total_points: 0,
          level: "BEGINNER",
          unlocked_content_id: null,
        }}
      />,
    );
    expect(screen.getByRole("dialog", { name: "Sessão sem ponto." })).toBeInTheDocument();
    expect(screen.getByText(/não revisou nada hoje/)).toBeInTheDocument();
  });

  it("comemora o ponto e o desbloqueio", () => {
    renderWithClient(
      <OutcomeDialog
        onClose={vi.fn()}
        outcome={{
          content_id: "c1",
          kind: "REVIEW",
          duration_seconds: 1500,
          awarded: true,
          reason: null,
          total_points: 10,
          level: "INTERMEDIATE",
          unlocked_content_id: "c2",
        }}
      />,
    );
    expect(screen.getByText(/\+1 ponto/)).toBeInTheDocument();
    expect(screen.getByText(/próximo conteúdo da fila foi liberado/)).toBeInTheDocument();
  });

  it("fechar chama onClose; sem resultado não há diálogo", async () => {
    const onClose = vi.fn();
    const { rerender } = renderWithClient(<OutcomeDialog onClose={onClose} outcome={null} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    rerender(
      <OutcomeDialog
        onClose={onClose}
        outcome={{
          content_id: "c1",
          kind: "STUDY",
          duration_seconds: 300,
          awarded: false,
          reason: "TOO_SHORT",
          total_points: 0,
          level: "BEGINNER",
          unlocked_content_id: null,
        }}
      />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Continuar" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("SDT: exibe evolução de maestria, desempenho no teste e dica de zona de desafio", () => {
    renderWithClient(
      <OutcomeDialog
        onClose={vi.fn()}
        outcome={{
          content_id: "c1",
          kind: "REVIEW",
          duration_seconds: 1500,
          awarded: true,
          reason: null,
          total_points: 16,
          level: "INTERMEDIATE",
          level_before: "BEGINNER",
          next_level: "ADVANCED",
          points_for_next_level: 30,
          challenges_solved: 1,
          challenges_for_next_level: 3,
          recall_recalled: 2,
          recall_total: 3,
          unlocked_content_id: null,
        }}
      />,
    );
    expect(screen.getByText(/Novo nível alcançado: Intermediário/)).toBeInTheDocument();
    expect(screen.getByText(/Teste de memória: 2\/3 acertadas sem consultar/)).toBeInTheDocument();
    expect(screen.getByText(/16\/30 pts/)).toBeInTheDocument();
    expect(screen.getByText(/Zona de desafio/)).toBeInTheDocument();
  });
});
