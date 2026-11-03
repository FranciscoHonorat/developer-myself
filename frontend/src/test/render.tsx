import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import type { Content } from "../api/types";

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
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
    ...overrides,
  };
}
