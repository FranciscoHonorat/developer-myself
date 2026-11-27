import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makePlan } from "@/test/fixtures";
import { callTo, jsonResponse, renderWithClient, routeFetch } from "@/test/render";
import { AccountPage } from "./AccountPage";

afterEach(() => vi.restoreAllMocks());

const PASSWORD = "senha-forte-123"; // gitleaks:allow (senha de teste)

function renderAccount() {
  const fetchMock = routeFetch({
    "/auth/me": {
      id: "u1",
      email: "eu@exemplo.com",
      created_at: "2026-11-01T10:00:00Z",
      username: "eu-1",
    },
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
    await user.type(await screen.findByLabelText("Confirme sua senha"), PASSWORD);
    await user.click(screen.getByRole("button", { name: "Excluir definitivamente" }));
    const dialog = await screen.findByRole("alertdialog", { name: /Excluir a conta/ });
    expect(callTo(fetchMock, "/auth/delete-account")).toBeUndefined();
    await user.click(within(dialog).getByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(callTo(fetchMock, "/auth/delete-account")).toBeDefined());
  });

  it("sair limpa rascunhos locais de teste de memória e aquecimento", async () => {
    localStorage.setItem("recall:2026-11-20T10:00:00Z", '{"step":"answer"}');
    localStorage.setItem("warmup:2026-11-20T10:00:00Z", '{"step":"answer"}');
    localStorage.setItem("dm-theme", "dark");
    renderAccount();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Sair/ }));
    await waitFor(() => {
      expect(localStorage.getItem("recall:2026-11-20T10:00:00Z")).toBeNull();
      expect(localStorage.getItem("warmup:2026-11-20T10:00:00Z")).toBeNull();
    });
    expect(localStorage.getItem("dm-theme")).toBe("dark");
  });

  describe("username", () => {
    it("mostra o atual e troca pedindo a senha", async () => {
      const fetchMock = renderAccount();
      const user = userEvent.setup();
      const card = await screen.findByRole("region", { name: "Username" });
      expect(await within(card).findByText("eu-1")).toBeInTheDocument();
      await user.type(within(card).getByLabelText("Novo username"), "jose");
      await user.type(within(card).getByLabelText("Senha atual"), PASSWORD);
      await user.click(within(card).getByRole("button", { name: "Trocar username" }));
      await waitFor(() => {
        const call = callTo(fetchMock, "/auth/username");
        expect(call?.[1]?.method).toBe("PUT");
        expect(call?.[1]?.body).toBe(JSON.stringify({ username: "jose", password: PASSWORD }));
      });
    });

    it("username em uso mostra a mensagem da API", async () => {
      const fetchMock = renderAccount();
      const base = fetchMock.getMockImplementation();
      fetchMock.mockImplementation(async (input, init) =>
        String(input).endsWith("/auth/username")
          ? jsonResponse({ detail: "Este username já está em uso.", code: "USERNAME_TAKEN" }, 409)
          : // biome-ignore lint/style/noNonNullAssertion: definido pelo routeFetch
            base!(input, init),
      );
      const user = userEvent.setup();
      const card = await screen.findByRole("region", { name: "Username" });
      await user.type(within(card).getByLabelText("Novo username"), "ana");
      await user.type(within(card).getByLabelText("Senha atual"), PASSWORD);
      await user.click(within(card).getByRole("button", { name: "Trocar username" }));
      expect(await within(card).findByText("Este username já está em uso.")).toBeInTheDocument();
    });
  });

  it("salva propósito geral de estudo via PUT /plan/purpose", async () => {
    const fetchMock = renderAccount();
    const user = userEvent.setup();
    const card = await screen.findByRole("region", { name: "Propósito de estudo" });
    await user.type(within(card).getByLabelText("Seu propósito"), "Construir sistemas seguros");
    await user.click(within(card).getByRole("button", { name: "Salvar propósito" }));
    await waitFor(() => {
      const call = callTo(fetchMock, "/plan/purpose");
      expect(call?.[1]?.method).toBe("PUT");
      expect(call?.[1]?.body).toBe(JSON.stringify({ purpose: "Construir sistemas seguros" }));
    });
  });
});
