// `api/` é o port do frontend: componentes NUNCA chamam fetch direto (ADR-0011).
import type {
  Challenge,
  CompetencySheet,
  Content,
  ContentKind,
  ContentSchedule,
  MasteryLevel,
  Me,
  NotesInput,
  Outcome,
  Plan,
  Recommendations,
  SessionKind,
  SessionRecord,
  Stats,
  Today,
  Week,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-Requested-With"] = "fetch"; // CSRF (ADR-0009)
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const init: RequestInit = { method, headers, credentials: "same-origin" };
  if (body !== undefined) init.body = JSON.stringify(body);
  const response = await fetch(`/api${path}`, init);

  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const err = (data ?? {}) as { detail?: unknown; code?: string };
    const message =
      typeof err.detail === "string"
        ? err.detail
        : Array.isArray(err.detail)
          ? "Dados inválidos."
          : `Erro ${response.status}`;
    throw new ApiError(response.status, err.code ?? "HTTP", message);
  }
  return data as T;
}

export const api = {
  register: (email: string, password: string, timezone: string) =>
    request<Me>("POST", "/auth/register", { email, password, timezone }),
  login: (email: string, password: string) =>
    request<void>("POST", "/auth/login", { email, password }),
  logout: () => request<void>("POST", "/auth/logout"),
  me: () => request<Me>("GET", "/auth/me"),
  deleteAccount: (password: string) => request<void>("POST", "/auth/delete-account", { password }),

  plan: () => request<Plan>("GET", "/plan"),
  changeTimezone: (timezone: string) => request<void>("PUT", "/plan/timezone", { timezone }),
  addContent: (title: string, kind: ContentKind) =>
    request<Content>("POST", "/contents", { title, kind }),
  finishContent: (contentId: string) =>
    request<{ unlocked_content_id: string | null }>("POST", `/contents/${contentId}/finish`),
  addChallenge: (contentId: string, description: string, target_level: MasteryLevel) =>
    request<Challenge>("POST", `/contents/${contentId}/challenges`, { description, target_level }),
  solveChallenge: (contentId: string, challengeId: string, evidence: string) =>
    request<{ level: MasteryLevel }>(
      "POST",
      `/contents/${contentId}/challenges/${challengeId}/solve`,
      { evidence },
    ),

  startSession: (contentId: string) =>
    request<{ kind: SessionKind }>("POST", "/sessions", { content_id: contentId }),
  finishSession: (notes: NotesInput) => request<Outcome>("POST", "/sessions/current/finish", notes),
  cancelSession: () => request<void>("POST", "/sessions/current/cancel"),

  history: (limit = 50) => request<SessionRecord[]>("GET", `/history?limit=${limit}`),
  stats: (days = 30) => request<Stats>("GET", `/stats?days=${days}`),
  exportData: () => request<unknown>("GET", "/export"),
  recommendations: () => request<Recommendations>("GET", "/recommendations"),
  today: () => request<Today>("GET", "/today"),
  week: () => request<Week>("GET", "/week"),
  changePreferences: (minutes_per_day: number, rest_days: number[]) =>
    request<void>("PUT", "/plan/preferences", { minutes_per_day, rest_days }),
  competencies: () => request<CompetencySheet>("GET", "/competencies"),
  schedule: (contentId: string) =>
    request<ContentSchedule>("GET", `/contents/${contentId}/schedule`),
  renameContent: (contentId: string, title: string) =>
    request<void>("PATCH", `/contents/${contentId}`, { title }),
  removeContent: (contentId: string) =>
    request<{ unlocked_content_id: string | null }>("DELETE", `/contents/${contentId}`),
};
