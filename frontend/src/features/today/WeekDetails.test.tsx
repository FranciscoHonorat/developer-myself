import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Week, WeekBlock } from "@/api/types";
import { jsonResponse, renderWithClient } from "@/test/render";
import { WeekDetails } from "./WeekDetails";

afterEach(() => vi.restoreAllMocks());

const block = (
  title: string,
  competency: string,
  minutes: number,
  kind: WeekBlock["kind"] = "STUDY",
): WeekBlock => ({
  kind,
  content_id: title,
  title,
  competency,
  competency_name: competency,
  pomodoros: minutes / 30,
  minutes,
  first_day: 1,
  last_day: minutes / 30,
  focus: "foco",
});

const week: Week = {
  minutes_per_day: 210,
  rest_days: [6],
  pomodoro_minutes: 30,
  study_minutes: 25,
  days: Array.from({ length: 7 }, (_, i) => ({
    date: `2026-11-0${i + 2}`,
    weekday: i,
    name: ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"][i] as string,
    is_rest: i === 6,
    minutes: i === 6 ? 0 : 210,
    competencies: i === 6 ? [] : ["DevOps", "Go", "AppSec"],
    blocks:
      i === 6
        ? []
        : [
            block("Docker", "DevOps", 60, "REVIEW"),
            block("Learning Go", "Go", 90),
            block("SAST", "AppSec", 60),
          ],
  })),
};

describe("WeekDetails", () => {
  it("mostra a grade dia × competência com minutos e totais", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(week));
    renderWithClient(<WeekDetails />);

    const grid = await screen.findByRole("table");
    const goRow = within(grid).getByRole("row", { name: /^Go/ });
    expect(goRow).toHaveTextContent("90");
    expect(goRow).toHaveTextContent("9h");
    expect(within(grid).getByRole("row", { name: /^Total/ })).toHaveTextContent("folga");
    expect(screen.getByText("Folga")).toBeInTheDocument();
    expect(screen.getAllByText(/3h30 · 3 competências/)).toHaveLength(6);
  });

  it("salva o ritmo escolhido", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (_url, init) =>
        init?.method === "PUT" ? new Response(null, { status: 204 }) : jsonResponse(week),
      );
    renderWithClient(<WeekDetails />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("radio", { name: "4h" }));
    await user.click(screen.getByRole("checkbox", { name: "sáb" }));
    await user.click(screen.getByRole("button", { name: "Salvar ritmo" }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(true),
    );
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({ minutes_per_day: 240, rest_days: [5, 6] });
  });

  it("oferece de 3h a 8h por dia", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (_url, init) =>
        init?.method === "PUT" ? new Response(null, { status: 204 }) : jsonResponse(week),
      );
    renderWithClient(<WeekDetails />);
    const user = userEvent.setup();
    const ritmo = await screen.findByRole("group", { name: "Tempo de estudo por dia" });
    expect(
      within(ritmo)
        .getAllByRole("radio")
        .map((r) => r.closest("label")?.textContent),
    ).toEqual(["3h", "3h30", "4h", "4h30", "5h", "5h30", "6h", "7h", "8h"]);
    await user.click(screen.getByRole("radio", { name: "8h" }));
    await user.click(screen.getByRole("button", { name: "Salvar ritmo" }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(true),
    );
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(String(put?.[1]?.body)).minutes_per_day).toBe(480);
  });
});
