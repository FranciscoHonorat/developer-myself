import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RecallQuestion } from "@/api/types";
import { RecallTest } from "./RecallTest";

const questions: RecallQuestion[] = [
  { id: "q1", text: "Explique sem consultar: CQS", source: "TO_REVIEW" },
  {
    id: "q2",
    text: "O que você lembra de nomes? Explique com um exemplo seu.",
    source: "SPACED_TOPIC",
  },
  { id: "q3", text: "Explique funções para quem está começando.", source: "TOPIC" },
];
const KEY = "recall:2026-11-01T10:00:00Z";
const FIRST = "Explique sem consultar: CQS";

function group(i: number): HTMLElement {
  const found = screen.getAllByRole("radiogroup")[i];
  if (!found) throw new Error(`radiogroup ${i} não existe`);
  return found;
}

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

async function answerAndCheck(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(FIRST), "comando muda, consulta lê");
  await user.click(screen.getByRole("button", { name: "Conferir respostas" }));
}

describe("RecallTest", () => {
  it("esconde as correções até conferir", async () => {
    const onChange = vi.fn();
    render(<RecallTest questions={questions} storageKey={KEY} onChange={onChange} />);
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    expect(onChange).toHaveBeenLastCalledWith(null, false);

    const user = userEvent.setup();
    await answerAndCheck(user);
    expect(screen.getAllByRole("radiogroup")).toHaveLength(3);
    expect(screen.getByText("comando muda, consulta lê")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(onChange).toHaveBeenLastCalledWith(null, true);
  });

  it("só libera quando as 3 têm correção", async () => {
    const onChange = vi.fn();
    render(<RecallTest questions={questions} storageKey={KEY} onChange={onChange} />);
    const user = userEvent.setup();
    await answerAndCheck(user);
    await user.click(within(group(0)).getByRole("radio", { name: "Acertei" }));
    await user.click(within(group(1)).getByRole("radio", { name: "Parcial" }));
    expect(onChange).toHaveBeenLastCalledWith(null, true);
    await user.click(within(group(2)).getByRole("radio", { name: "Errei" }));
    expect(onChange).toHaveBeenLastCalledWith(
      [
        { question_id: "q1", answer: "comando muda, consulta lê", grade: "RECALLED", useful: null },
        { question_id: "q2", answer: "", grade: "PARTIAL", useful: null },
        { question_id: "q3", answer: "", grade: "MISSED", useful: null },
      ],
      true,
    );
  });

  it("guarda o rascunho e o passo ao recarregar", async () => {
    const { unmount } = render(
      <RecallTest questions={questions} storageKey={KEY} onChange={vi.fn()} />,
    );
    const user = userEvent.setup();
    await answerAndCheck(user);
    await user.click(within(group(0)).getByRole("radio", { name: "Acertei" }));
    unmount();

    render(<RecallTest questions={questions} storageKey={KEY} onChange={vi.fn()} />);
    expect(screen.getByText("comando muda, consulta lê")).toBeInTheDocument();
    expect(
      within(group(0)).getByRole("radio", {
        name: "Acertei",
      }),
    ).toBeChecked();
  });

  it("útil/ruim é opcional", async () => {
    const onChange = vi.fn();
    render(<RecallTest questions={questions} storageKey={KEY} onChange={onChange} />);
    const user = userEvent.setup();
    await answerAndCheck(user);
    for (const group of screen.getAllByRole("radiogroup")) {
      await user.click(within(group).getByRole("radio", { name: "Acertei" }));
    }
    expect(onChange.mock.lastCall?.[0]).toHaveLength(3);
    const useful = screen.getAllByRole("button", { name: "Pergunta útil" })[1] as HTMLElement;
    expect(useful).toHaveAttribute("aria-pressed", "false");
    await user.click(useful);
    expect(useful).toHaveAttribute("aria-pressed", "true");
    expect(onChange.mock.lastCall?.[0][1].useful).toBe(true);
  });
});
