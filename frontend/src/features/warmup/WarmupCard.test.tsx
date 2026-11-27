import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { WarmupStatus } from "@/api/types";
import { callTo, jsonResponse, renderWithClient, routeFetch } from "@/test/render";
import { WarmupCard } from "./WarmupCard";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const available: WarmupStatus = {
  available: true,
  done_today: false,
  content: { id: "c1", title: "Clean Code" },
  active: null,
};

const active = {
  started_at: "2026-11-02T11:00:00Z",
  questions: [
    {
      id: "q1",
      text: "O que é CQS?",
      source: "LEARNER" as const,
      expected_answer: "Separar comando de consulta",
    },
    { id: "q2", text: "O que você lembra de nomes?", source: "SPACED_TOPIC" as const },
  ],
};

async function answerAndGrade() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("O que é CQS?"), "não lembro");
  await user.click(screen.getByRole("button", { name: "Conferir respostas" }));
  for (const group of screen.getAllByRole("radiogroup", { name: /Correção/ })) {
    await user.click(within(group).getByRole("radio", { name: "Acertei" }));
  }
  return user;
}

describe("WarmupCard", () => {
  it("convida para o aquecimento quando está disponível", async () => {
    routeFetch({ "/warmup": available });
    renderWithClient(<WarmupCard />);
    expect(await screen.findByText("🔥 Aquecimento · 2 perguntas · ~2 min")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Começar" })).toBeInTheDocument();
  });

  it("não aparece quando não há o que aquecer", async () => {
    const fetchMock = routeFetch({
      "/warmup": { ...available, available: false, content: null },
    });
    const { container } = renderWithClient(<WarmupCard />);
    await waitFor(() => expect(callTo(fetchMock, "/warmup")).toBeDefined());
    expect(container).toBeEmptyDOMElement();
  });

  it("mostra uma linha discreta quando o aquecimento de hoje já foi feito", async () => {
    routeFetch({ "/warmup": { ...available, available: false, done_today: true } });
    renderWithClient(<WarmupCard />);
    expect(await screen.findByText("✅ Aquecimento feito hoje")).toBeInTheDocument();
  });

  it("esconde a resposta esperada até conferir e só conclui com tudo corrigido", async () => {
    routeFetch({ "/warmup": { ...available, active } });
    renderWithClient(<WarmupCard />);
    await screen.findByLabelText("O que é CQS?");
    expect(screen.queryByText("Separar comando de consulta")).not.toBeInTheDocument();
    const finish = screen.getByRole("button", { name: "Concluir aquecimento" });
    expect(finish).toBeDisabled();

    await answerAndGrade();
    expect(screen.getByText("Sua resposta esperada")).toBeInTheDocument();
    expect(screen.getByText("Separar comando de consulta")).toBeInTheDocument();
    expect(finish).toBeEnabled();
  });

  it("depois de concluir sugere revisar quando a revisão está pendente", async () => {
    const fetchMock = routeFetch({
      "/warmup": { ...available, active },
      "/warmup/finish": { next: { content_id: "c2", title: "DDD", kind: "REVIEW" } },
    });
    renderWithClient(<WarmupCard />);
    await screen.findByLabelText("O que é CQS?");
    const user = await answerAndGrade();
    await user.click(screen.getByRole("button", { name: "Concluir aquecimento" }));

    expect(
      await screen.findByText('✅ Aquecimento feito. Bora revisar "DDD"?'),
    ).toBeInTheDocument();
    const body = JSON.parse(String(callTo(fetchMock, "/warmup/finish")?.[1]?.body));
    expect(body.answers).toHaveLength(2);
    expect(localStorage.getItem(`warmup:${active.started_at}`)).toBeNull();

    await user.click(screen.getByRole("button", { name: "Iniciar sessão" }));
    const start = JSON.parse(String(callTo(fetchMock, "/sessions")?.[1]?.body));
    expect(start).toEqual({ content_id: "c2" });
  });

  it("sem próximo passo, só agradece e não oferece sessão", async () => {
    routeFetch({ "/warmup": { ...available, active }, "/warmup/finish": { next: null } });
    renderWithClient(<WarmupCard />);
    await screen.findByLabelText("O que é CQS?");
    const user = await answerAndGrade();
    await user.click(screen.getByRole("button", { name: "Concluir aquecimento" }));
    expect(await screen.findByText("✅ Aquecimento feito.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Iniciar sessão" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Por hoje é só" }));
    expect(screen.queryByText("✅ Aquecimento feito.")).not.toBeInTheDocument();
  });

  it("aquecimento expirado apaga o rascunho e convida para um novo", async () => {
    let expiredOnServer = false; // o servidor descarta o aquecimento vencido ao responder 409
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.endsWith("/warmup/finish")) {
        expiredOnServer = true;
        return jsonResponse({ detail: "Não há aquecimento.", code: "NoActiveWarmupError" }, 409);
      }
      if (path.endsWith("/warmup"))
        return jsonResponse({ ...available, active: expiredOnServer ? null : active });
      return jsonResponse([]);
    });
    renderWithClient(<WarmupCard />);
    await screen.findByLabelText("O que é CQS?");
    const user = await answerAndGrade();
    await user.click(screen.getByRole("button", { name: "Concluir aquecimento" }));
    expect(
      await screen.findByText("Esse aquecimento expirou — que tal um novo?"),
    ).toBeInTheDocument();
    expect(localStorage.getItem(`warmup:${active.started_at}`)).toBeNull();
  });
});

describe("WarmupCard — conflito de abas", () => {
  it("409 de concorrência mantém o rascunho e pede para tentar de novo", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.endsWith("/warmup/finish"))
        return jsonResponse(
          { detail: "A trilha mudou em outra aba. Tente de novo.", code: "ConcurrencyError" },
          409,
        );
      if (path.endsWith("/warmup")) return jsonResponse({ ...available, active });
      return jsonResponse([]);
    });
    renderWithClient(<WarmupCard />);
    await screen.findByLabelText("O que é CQS?");
    const user = await answerAndGrade();
    await user.click(screen.getByRole("button", { name: "Concluir aquecimento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tente de novo");
    expect(screen.queryByText(/expirou/)).not.toBeInTheDocument();
    expect(localStorage.getItem(`warmup:${active.started_at}`)).not.toBeNull();
  });
});
