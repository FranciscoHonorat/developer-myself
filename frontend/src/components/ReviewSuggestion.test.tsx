import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, renderWithClient } from "../test/render";
import { ReviewSuggestion } from "./ReviewSuggestion";

afterEach(() => vi.restoreAllMocks());

describe("ReviewSuggestion", () => {
  it("mostra a chance de lembrar estimada pela rede, na ordem do servidor", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        model: "rede-neural",
        model_info: { trained_on: "synthetic+real", trained_at: null, real_samples: 7 },
        items: [
          { content_id: "a", title: "DDD", recall_probability: 0.27 },
          { content_id: "b", title: "Clean Code", recall_probability: 0.95 },
        ],
      }),
    );
    renderWithClient(<ReviewSuggestion />);
    expect(await screen.findByText(/rede neural/)).toBeInTheDocument();
    expect(screen.getByText("Treinada com 7 autoavaliações suas.")).toBeInTheDocument();
    const meters = screen.getAllByRole("meter");
    expect(meters[0]).toHaveAccessibleName("Chance de lembrar DDD");
    expect(meters[0]).toHaveAttribute("value", "27");
    expect(meters[1]).toHaveAttribute("value", "95");
  });

  it("não aparece quando não há nada para revisar", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        model: "regra",
        model_info: { trained_on: null, trained_at: null, real_samples: 0 },
        items: [],
      }),
    );
    const { container } = renderWithClient(<ReviewSuggestion />);
    await new Promise((r) => setTimeout(r, 0));
    expect(container).toBeEmptyDOMElement();
  });
});
