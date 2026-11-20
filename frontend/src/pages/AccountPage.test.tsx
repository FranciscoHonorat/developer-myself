import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makePlan } from "@/test/fixtures";
import { callTo, renderWithClient, routeFetch } from "@/test/render";
import { AccountPage } from "./AccountPage";

afterEach(() => vi.restoreAllMocks());

function renderAccount() {
  const fetchMock = routeFetch({
    "/auth/me": { id: "u1", email: "eu@exemplo.com", created_at: "2026-11-01T10:00:00Z" },
    "/plan": makePlan(),
  });
  renderWithClient(
    <MemoryRouter>
      <AccountPage />
    </MemoryRouter>,
  );
  return fetchMock;
}

describe("AccountPage", () => {
  it("mostra o e-mail e as seções da conta", async () => {
    renderAccount();
    expect(await screen.findByText("eu@exemplo.com")).toBeInTheDocument();
    for (const name of [
      "Aparência",
      "Ritmo de estudo",
      "Fuso horário",
      "Seus dados (LGPD)",
      "Excluir conta",
    ]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
  });

  it("apagar conta pede confirmação em diálogo", async () => {
    const fetchMock = renderAccount();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Confirme sua senha"), "senha-forte-123");
    await user.click(screen.getByRole("button", { name: "Excluir definitivamente" }));
    const dialog = await screen.findByRole("alertdialog", { name: /Excluir a conta/ });
    expect(callTo(fetchMock, "/auth/delete-account")).toBeUndefined();
    await user.click(within(dialog).getByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(callTo(fetchMock, "/auth/delete-account")).toBeDefined());
  });
});
