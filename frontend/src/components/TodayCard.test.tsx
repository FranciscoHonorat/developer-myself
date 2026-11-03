import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DayPlan, Today } from "../api/types";
import { jsonResponse, renderWithClient } from "../test/render";
import { TodayCard } from "./TodayCard";

afterEach(() => vi.restoreAllMocks());

const day = (overrides: Partial<DayPlan>): DayPlan => ({
  day: 4,
  phase: "Fundamentos (rumo a Intermediário)",
  kind: "STUDY",
  focus: "pacotes, disco e LVM",
  activity: "Estude pacotes, disco e LVM.",
  warmup: ["processos e serviços (1 dia atrás)"],
  target_level: null,
  done: false,
  ...overrides,
});

describe("TodayCard", () => {
  it("mostra as revisões antes do estudo, com o dia e o aquecimento", async () => {
    const today: Today = {
      reviews: [
        {
          content_id: "r",
          title: "Redes",
          day: 11,
          total_days: 30,
          plan: day({ day: 11, focus: "TLS", warmup: [] }),
        },
      ],
      studies: [{ content_id: "s", title: "Linux", day: 4, total_days: 30, plan: day({}) }],
      blocks: [
        {
          kind: "REVIEW",
          content_id: "r",
          title: "Redes",
          competency: "fundamentos",
          competency_name: "Fundamentos",
          pomodoros: 2,
          minutes: 60,
          first_day: 11,
          last_day: 12,
          focus: "TLS",
        },
        {
          kind: "STUDY",
          content_id: "s",
          title: "Linux",
          competency: "fundamentos",
          competency_name: "Fundamentos",
          pomodoros: 5,
          minutes: 150,
          first_day: 4,
          last_day: 8,
          focus: "pacotes",
        },
      ],
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(today));
    renderWithClient(<TodayCard />);

    expect(await screen.findByRole("heading", { name: /Hoje · 3h30/ })).toBeInTheDocument();
    const blocks = screen.getByRole("list", { name: "Blocos de hoje" });
    expect(blocks.firstElementChild).toHaveTextContent("Revisão Redes");
    expect(screen.getByText("Estudar: Linux")).toBeInTheDocument();
    expect(screen.getAllByText(/dia 4 de 30/)).toHaveLength(1);
    expect(screen.getByText("processos e serviços (1 dia atrás)")).toBeInTheDocument();
  });

  it("some quando não há nada para hoje", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ studies: [], reviews: [], blocks: [] }),
    );
    const { container } = renderWithClient(<TodayCard />);
    await new Promise((r) => setTimeout(r, 0));
    expect(container).toBeEmptyDOMElement();
  });
});
