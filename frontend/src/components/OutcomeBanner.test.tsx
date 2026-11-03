import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithClient } from "../test/render";
import { OutcomeBanner } from "./OutcomeBanner";

describe("OutcomeBanner", () => {
  it("explica por que a sessão não pontuou (resposta do servidor)", () => {
    renderWithClient(
      <OutcomeBanner
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
    expect(screen.getByText(/Sessão sem ponto/)).toBeInTheDocument();
    expect(screen.getByText(/não revisou nada hoje/)).toBeInTheDocument();
  });

  it("comemora o ponto e o desbloqueio", () => {
    renderWithClient(
      <OutcomeBanner
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
});
