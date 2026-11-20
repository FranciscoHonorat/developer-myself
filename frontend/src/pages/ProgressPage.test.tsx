import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderWithClient, routeFetch } from "@/test/render";
import { ProgressPage } from "./ProgressPage";

afterEach(() => vi.restoreAllMocks());

function renderAt(path: string) {
  routeFetch({
    "/competencies": {
      xp: 0,
      level: 1,
      next_level_xp: 50,
      total_points: 0,
      competencies: [],
      effort: [],
      rules: { grace_days: 21, decay_per_day: 0.01, floor: 0.5 },
    },
    "/stats?days=30": {
      total_sessions: 0,
      total_points: 0,
      total_minutes: 0,
      current_streak_days: 0,
      withheld_by_reason: {},
      daily: [],
    },
  });
  const router = createMemoryRouter([{ path: "/progresso", element: <ProgressPage /> }], {
    initialEntries: [path],
  });
  renderWithClient(<RouterProvider router={router} />);
  return router;
}

describe("ProgressPage", () => {
  it("sem aba na URL abre Competências", async () => {
    renderAt("/progresso");
    expect(
      await screen.findByRole("tab", { name: "Competências", selected: true }),
    ).toBeInTheDocument();
  });

  it("a aba vem da URL e trocar de aba atualiza a URL", async () => {
    const router = renderAt("/progresso?aba=historico");
    expect(
      await screen.findByRole("tab", { name: "Histórico", selected: true }),
    ).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("tab", { name: "Competências" }));
    await waitFor(() => expect(router.state.location.search).toBe("?aba=competencias"));
  });
});
