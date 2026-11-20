import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AdminAccount } from "@/api/types";
import { callTo, jsonResponse, renderWithClient, routeFetch } from "@/test/render";
import { AdminPage } from "./AdminPage";

afterEach(() => vi.restoreAllMocks());

const account = (over: Partial<AdminAccount> = {}): AdminAccount => ({
  id: "u2",
  email: "aluno@exemplo.com",
  created_at: "2026-11-10T10:00:00Z",
  last_activity_at: "2026-11-19T21:00:00Z",
  contents: 4,
  sessions: 12,
  ...over,
});

function renderAdmin(routes: Record<string, unknown> = {}) {
  const fetchMock = routeFetch({
    "/admin/registration": { open: true },
    "/admin/accounts?limit=20": { items: [account()], next_cursor: null },
    ...routes,
  });
  renderWithClient(
    <MemoryRouter>
      <AdminPage />
    </MemoryRouter>,
  );
  return fetchMock;
}

describe("AdminPage", () => {
  it("lista as contas com e-mail e contagens", async () => {
    renderAdmin();
    const row = await screen.findByRole("row", { name: /aluno@exemplo.com/ });
    expect(row).toHaveTextContent("4");
    expect(row).toHaveTextContent("12");
  });

  it("Carregar mais busca a página seguinte pelo cursor", async () => {
    const fetchMock = renderAdmin({
      "/admin/accounts?limit=20": { items: [account()], next_cursor: "abc" },
      "/admin/accounts?limit=20&cursor=abc": {
        items: [account({ id: "u3", email: "antiga@exemplo.com" })],
        next_cursor: null,
      },
    });
    await userEvent.click(await screen.findByRole("button", { name: "Carregar mais" }));
    expect(await screen.findByRole("row", { name: /antiga@exemplo.com/ })).toBeInTheDocument();
    expect(callTo(fetchMock, "/admin/accounts?limit=20&cursor=abc")).toBeDefined();
  });

  it("interruptor fecha o cadastro", async () => {
    const fetchMock = renderAdmin();
    const toggle = await screen.findByRole("switch", { name: "Cadastro aberto" });
    expect(toggle).toHaveAttribute("aria-checked", "true");
    await userEvent.click(toggle);
    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([input, init]) => String(input).endsWith("/admin/registration") && init?.method === "PUT",
      );
      expect(put?.[1]?.body).toBe(JSON.stringify({ open: false }));
    });
  });

  it("excluir só confirma depois de digitar o e-mail exato", async () => {
    const fetchMock = renderAdmin();
    const user = userEvent.setup();
    const row = await screen.findByRole("row", { name: /aluno@exemplo.com/ });
    await user.click(within(row).getByRole("button", { name: "Excluir" }));
    const dialog = await screen.findByRole("alertdialog");
    const confirm = within(dialog).getByRole("button", { name: "Excluir conta" });
    expect(confirm).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/Digite o e-mail/), "aluno@exemplo");
    expect(confirm).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/Digite o e-mail/), ".com");
    await user.click(confirm);
    await waitFor(() => {
      const del = fetchMock.mock.calls.find(
        ([input, init]) =>
          String(input).endsWith("/admin/accounts/u2") && init?.method === "DELETE",
      );
      expect(del).toBeDefined();
    });
  });

  it("sem permissão mostra a mensagem da API", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      jsonResponse({ detail: "Você não tem acesso à área de admin.", code: "FORBIDDEN" }, 403),
    );
    renderWithClient(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    expect(
      (await screen.findAllByText("Você não tem acesso à área de admin.")).length,
    ).toBeGreaterThan(0);
  });

  it("falha ao excluir mantém o diálogo aberto com o erro", async () => {
    const fetchMock = renderAdmin();
    const base = fetchMock.getMockImplementation();
    fetchMock.mockImplementation(async (input, init) =>
      init?.method === "DELETE"
        ? jsonResponse({ detail: "Conta não encontrada.", code: "NOT_FOUND" }, 404)
        : // biome-ignore lint/style/noNonNullAssertion: implementação definida pelo routeFetch
          base!(input, init),
    );
    const user = userEvent.setup();
    const row = await screen.findByRole("row", { name: /aluno@exemplo.com/ });
    await user.click(within(row).getByRole("button", { name: "Excluir" }));
    const dialog = await screen.findByRole("alertdialog");
    await user.type(within(dialog).getByLabelText(/Digite o e-mail/), "aluno@exemplo.com");
    await user.click(within(dialog).getByRole("button", { name: "Excluir conta" }));
    expect(await within(dialog).findByText("Conta não encontrada.")).toBeInTheDocument();
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });
});
