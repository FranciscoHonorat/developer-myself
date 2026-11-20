import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, renderWithClient } from "@/test/render";
import { AuthPage } from "./AuthPage";

afterEach(() => vi.restoreAllMocks());

function renderAt(path: "/entrar" | "/cadastro", registrationOpen = true) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const p = String(input);
    if (p.endsWith("/auth/registration")) return jsonResponse({ open: registrationOpen });
    if (p.endsWith("/auth/login"))
      return jsonResponse(
        { detail: "E-mail ou senha incorretos.", code: "InvalidCredentialsError" },
        401,
      );
    return jsonResponse({ detail: "Faça login.", code: "NotAuthenticatedError" }, 401);
  });
  const router = createMemoryRouter(
    [
      { path: "/entrar", element: <AuthPage mode="login" /> },
      { path: "/cadastro", element: <AuthPage mode="register" /> },
    ],
    { initialEntries: [path] },
  );
  renderWithClient(<RouterProvider router={router} />);
  return router;
}

describe("AuthPage", () => {
  it("/cadastro mostra Criar conta e o painel do método", async () => {
    renderAt("/cadastro");
    expect(await screen.findByRole("button", { name: "Criar conta" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Como funciona" })).toHaveTextContent(
      /repetição espaçada/i,
    );
    expect(screen.getByText(/Mínimo de 10 caracteres/)).toBeInTheDocument();
  });

  it("alternar leva para a outra rota", async () => {
    const router = renderAt("/entrar");
    await userEvent
      .setup()
      .click(await screen.findByRole("link", { name: "Não tem conta? Cadastre-se" }));
    expect(router.state.location.pathname).toBe("/cadastro");
  });

  it("erro de credencial aparece no formulário", async () => {
    renderAt("/entrar");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("E-mail"), "eu@exemplo.com");
    await user.type(screen.getByLabelText("Senha"), "errada-123456");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha incorretos.");
  });

  it("/cadastro avisa quando o cadastro está fechado, sem esconder o formulário", async () => {
    renderAt("/cadastro", false);
    expect(
      await screen.findByText("Novos cadastros estão fechados no momento."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar conta" })).toBeInTheDocument();
  });

  it("/cadastro aberto não mostra aviso", async () => {
    renderAt("/cadastro", true);
    await screen.findByRole("button", { name: "Criar conta" });
    expect(screen.queryByText(/cadastros estão fechados/)).not.toBeInTheDocument();
  });
});
