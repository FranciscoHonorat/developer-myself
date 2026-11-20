import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Competency, CompetencySheet } from "@/api/types";
import { jsonResponse, renderWithClient } from "@/test/render";
import { Competencies } from "./Competencies";

afterEach(() => vi.restoreAllMocks());

const comp = (overrides: Partial<Competency>): Competency => ({
  key: "go",
  name: "Go",
  area: "Fundamentos",
  score: 40,
  peak: 40,
  rust_lost: 0,
  tier: "Praticante",
  title: "Praticante em Go",
  target: "Especialista",
  target_score: 75,
  points: 12,
  status: "em dia",
  rust_in_days: 15,
  contents: [{ title: "Learning Go", progress: 0.4, freshness: 1, rust_in_days: 15 }],
  ...overrides,
});

const sheet: CompetencySheet = {
  xp: 175,
  level: 2,
  next_level_xp: 200,
  total_points: 20,
  competencies: [
    comp({}),
    comp({
      key: "appsec",
      name: "AppSec",
      area: "AppSec",
      score: 54,
      peak: 60,
      rust_lost: 6,
      tier: "Proficiente",
      status: "enferrujando",
      rust_in_days: 0,
    }),
    comp({ key: "ingles", name: "Inglês", score: 0, peak: 0, status: "sem progresso", points: 0 }),
  ],
  effort: [
    { area: "Fundamentos", points: 12 },
    { area: "AppSec", points: 8 },
  ],
  rules: { grace_days: 21, decay_per_day: 0.01, floor: 0.5 },
};

describe("Competencies", () => {
  it("ranqueia as competências e mostra faixa, meta e ferrugem com ícone e texto", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(sheet));
    renderWithClient(<Competencies />);

    const meters = await screen.findAllByRole("meter", { name: /de 100/ });
    expect(meters.map((m) => m.getAttribute("aria-label"))).toEqual([
      "AppSec: 54 de 100, meta Especialista",
      "Go: 40 de 100, meta Especialista",
      "Inglês: 0 de 100, meta Especialista",
    ]);
    expect(screen.getByText(/enferrujando: −6.0/)).toBeInTheDocument();
    expect(screen.getByText("competência enferrujando").parentElement).toHaveTextContent("1");
    expect(screen.getByText("Nível 2")).toBeInTheDocument();
  });

  it("mostra o esforço por área em barras ranqueadas e os conteúdos de cada competência", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(sheet));
    renderWithClient(<Competencies />);

    const effort = await screen.findByRole("region", { name: "Para onde foi seu esforço" });
    const rows = within(effort).getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("Fundamentos12 pts · 60%");
    expect(rows[1]).toHaveTextContent("AppSec8 pts · 40%");

    await userEvent
      .setup()
      .click(screen.getAllByRole("button", { name: /Ver 1 conteúdo/ })[0] as HTMLElement);
    expect(screen.getByRole("cell", { name: "Learning Go" })).toBeInTheDocument();
  });

  it("orienta quando a trilha está vazia", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ ...sheet, competencies: [], effort: [], total_points: 0 }),
    );
    renderWithClient(<Competencies />);
    expect(await screen.findByText(/Adicione conteúdos/)).toBeInTheDocument();
  });
});
