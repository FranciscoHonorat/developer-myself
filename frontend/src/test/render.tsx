import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";
import type { Content } from "../api/types";
import { TooltipProvider } from "../components/ui/tooltip";

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  // `wrapper` (e não envolver `ui`) para o `rerender` continuar dentro do provider.
  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>
        <TooltipProvider>{children}</TooltipProvider>
      </QueryClientProvider>
    ),
  });
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function makeContent(overrides: Partial<Content> = {}): Content {
  return {
    id: "c1",
    title: "Clean Code",
    kind: "BOOK",
    status: "IN_PROGRESS",
    points: 3,
    level: "BEGINNER",
    next_level: {
      level: "INTERMEDIATE",
      points_required: 10,
      challenges_required: 3,
      challenges_solved: 1,
    },
    queued_at: "2026-11-01T10:00:00Z",
    finished_at: null,
    last_session_at: null,
    queue_position: null,
    lock_reason: null,
    challenges: [],
    last_to_review: null,
    daily: false,
    ...overrides,
  };
}

/**
 * `fetch` roteado por caminho: cada chamada recebe um Response novo (o corpo só pode ser lido
 * uma vez). Cadernos (`/notebook`) e o histórico paginado respondem vazios por padrão; o
 * resto, `[]`.
 */
export function routeFetch(routes: Record<string, unknown> = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    const match = Object.keys(routes).find((p) => path.endsWith(p));
    if (match !== undefined) return jsonResponse(routes[match]);
    if (path.includes("/history?")) return jsonResponse({ items: [], next_cursor: null });
    if (path.endsWith("/notebook")) {
      const contentId = path.split("/").at(-2) ?? "";
      return jsonResponse({ content_id: contentId, text: "", version: 0, updated_at: null });
    }
    return jsonResponse([]);
  });
}

export const callTo = (fetchMock: ReturnType<typeof routeFetch>, path: string) =>
  fetchMock.mock.calls.find(([input]) => String(input).endsWith(path));
