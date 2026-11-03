import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeContent, renderWithClient } from "../test/render";
import { ContentCard } from "./ContentCard";

describe("ContentCard", () => {
  it("mostra pontos e o progresso até o próximo nível", () => {
    renderWithClient(<ContentCard content={makeContent()} hasActiveSession={false} />);
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
    const locked = makeContent({
      status: "LOCKED",
      queue_position: 1,
      lock_reason: "Refactoring está bloqueado: conclua Clean Code ou chegue a Intermediário nele.",
      title: "Refactoring",
    });
    renderWithClient(<ContentCard content={locked} hasActiveSession={false} />);
    expect(screen.getByText(/conclua Clean Code/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Estudar|Revisar/ })).not.toBeInTheDocument();
  });

  it("conteúdo consolidado oferece revisão", () => {
    renderWithClient(
      <ContentCard content={makeContent({ status: "CONSOLIDATED" })} hasActiveSession={false} />,
    );
    expect(screen.getByRole("button", { name: /Revisar/ })).toBeInTheDocument();
  });

  it("desabilita iniciar quando já há uma sessão ativa", () => {
    renderWithClient(<ContentCard content={makeContent()} hasActiveSession />);
    expect(screen.getByRole("button", { name: /Estudar/ })).toBeDisabled();
  });

  it("só deixa concluir no nível Avançado", () => {
    renderWithClient(
      <ContentCard
        content={makeContent({ status: "CONSOLIDATED", level: "INTERMEDIATE" })}
        hasActiveSession={false}
      />,
    );
    expect(screen.getByRole("button", { name: /Concluir/ })).toBeDisabled();
    expect(screen.getByText(/Chegue a Avançado para concluir/)).toBeInTheDocument();
  });

  it("no nível Avançado o botão Concluir fica disponível", () => {
    renderWithClient(
      <ContentCard
        content={makeContent({ status: "CONSOLIDATED", level: "ADVANCED", next_level: null })}
        hasActiveSession={false}
      />,
    );
    expect(screen.getByRole("button", { name: /Concluir/ })).toBeEnabled();
    expect(screen.queryByText(/Chegue a Avançado/)).not.toBeInTheDocument();
  });

  it("só oferece remover conteúdo sem progresso", () => {
    const { unmount } = renderWithClient(
      <ContentCard content={makeContent({ points: 0 })} hasActiveSession={false} />,
    );
    expect(screen.getByRole("button", { name: /Remover/ })).toBeInTheDocument();
    unmount();
    renderWithClient(<ContentCard content={makeContent({ points: 2 })} hasActiveSession={false} />);
    expect(screen.queryByRole("button", { name: /Remover/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Cronograma/ })).toBeInTheDocument();
  });
});
