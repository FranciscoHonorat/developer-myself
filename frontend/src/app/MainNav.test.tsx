import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderWithClient, routeFetch } from "@/test/render";
import { MainNav } from "./MainNav";

afterEach(() => vi.restoreAllMocks());

const me = (is_admin: boolean) => ({
  id: "u1",
  email: "eu@exemplo.com",
  created_at: "2026-11-01T10:00:00Z",
  is_admin,
});

function renderNav(isAdmin: boolean) {
  routeFetch({ "/auth/me": me(isAdmin) });
  renderWithClient(
    <MemoryRouter>
      <MainNav />
    </MemoryRouter>,
  );
}

describe("MainNav", () => {
  it("admin vê o link Admin", async () => {
    renderNav(true);
    expect(await screen.findByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
  });

  it("quem não é admin não vê o link", async () => {
    renderNav(false);
    expect(await screen.findByRole("link", { name: "Hoje" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
  });
});
