import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Pagination } from "./Pagination";

describe("Pagination", () => {
  it("some quando tudo cabe numa página", () => {
    const { container } = render(
      <Pagination page={1} totalPages={1} onChange={() => {}} label="Fila" />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("mostra a posição e navega entre páginas", async () => {
    const onChange = vi.fn();
    render(<Pagination page={2} totalPages={3} onChange={onChange} label="Fila" />);
    expect(screen.getByRole("navigation", { name: "Páginas de Fila" })).toHaveTextContent(
      "Página 2 de 3",
    );
    await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await userEvent.click(screen.getByRole("button", { name: "Anterior" }));
    expect(onChange.mock.calls).toEqual([[3], [1]]);
  });

  it("desabilita Anterior na primeira e Próxima na última", () => {
    const { rerender } = render(
      <Pagination page={1} totalPages={2} onChange={() => {}} label="Fila" />,
    );
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    rerender(<Pagination page={2} totalPages={2} onChange={() => {}} label="Fila" />);
    expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
  });
});
