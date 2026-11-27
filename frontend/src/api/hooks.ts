// TanStack Query: o estado global é o servidor. Cada comando invalida o que mudou.
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clearAllRecallDrafts } from "@/features/session/RecallTest";
import { api } from "./client";
import type { ContentKind, MasteryLevel, NotesInput, RecallAnswer } from "./types";

export const keys = {
  me: ["me"] as const,
  plan: ["plan"] as const,
  history: ["history"] as const,
  stats: ["stats"] as const,
  recommendations: ["recommendations"] as const,
  today: ["today"] as const,
  warmup: ["warmup"] as const,
  week: ["week"] as const,
  competencies: ["competencies"] as const,
  schedule: (id: string) => ["schedule", id] as const,
  notebook: (id: string) => ["notebook", id] as const,
  notebooks: ["notebooks"] as const,
  adminAccounts: ["admin", "accounts"] as const,
  adminRegistration: ["admin", "registration"] as const,
  registration: ["registration"] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: api.me, retry: false });
export const usePlan = () => useQuery({ queryKey: keys.plan, queryFn: api.plan });
// Histórico paginado por cursor: cada página pede a seguinte com o `next_cursor` da anterior.
export const useHistory = () =>
  useInfiniteQuery({
    queryKey: keys.history,
    queryFn: ({ pageParam }) => api.history(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  });
export const useRecommendations = () =>
  useQuery({ queryKey: keys.recommendations, queryFn: api.recommendations });
export const useToday = () => useQuery({ queryKey: keys.today, queryFn: api.today });
export const useWarmup = () => useQuery({ queryKey: keys.warmup, queryFn: api.warmup });
export const useSchedule = (contentId: string, enabled: boolean) =>
  useQuery({ queryKey: keys.schedule(contentId), queryFn: () => api.schedule(contentId), enabled });
export const useCompetencies = () =>
  useQuery({ queryKey: keys.competencies, queryFn: api.competencies });
export const useWeek = () => useQuery({ queryKey: keys.week, queryFn: api.week });
// Caderno: o autosave do editor grava direto (sem `useCommand`, que invalidaria a trilha a cada tecla).
export const useNotebook = (contentId: string) =>
  useQuery({ queryKey: keys.notebook(contentId), queryFn: () => api.notebook(contentId) });
export const useNotebooks = () => useQuery({ queryKey: keys.notebooks, queryFn: api.notebooks });
export const useStats = () => useQuery({ queryKey: keys.stats, queryFn: () => api.stats() });

type InvalidateKey = readonly unknown[];

const ALL_STUDY_KEYS: readonly InvalidateKey[] = [
  keys.plan,
  keys.history,
  keys.stats,
  keys.recommendations,
  keys.today,
  keys.warmup,
  keys.week,
  keys.competencies,
  ["schedule"],
];

function useCommand<TArgs, TResult>(
  fn: (args: TArgs) => Promise<TResult>,
  invalidates: readonly InvalidateKey[] = ALL_STUDY_KEYS,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => Promise.all(invalidates.map((queryKey) => qc.invalidateQueries({ queryKey }))),
  });
}

export const useAddContent = () =>
  useCommand(
    (a: { title: string; kind: ContentKind; purpose?: string }) =>
      api.addContent(a.title, a.kind, a.purpose),
    [keys.plan, keys.today, keys.week, keys.competencies, keys.recommendations, keys.warmup],
  );
export const useChangePurpose = () =>
  useCommand((purpose: string | null) => api.changePurpose(purpose), [keys.plan]);
export const useChangeContentPurpose = () =>
  useCommand(
    (a: { contentId: string; purpose: string | null }) =>
      api.changeContentPurpose(a.contentId, a.purpose),
    [keys.plan],
  );
export const useReorderQueue = () =>
  useCommand(
    (contentIds: string[]) => api.reorderQueue(contentIds),
    [keys.plan, keys.today, keys.week],
  );
export const useFinishContent = () => useCommand((id: string) => api.finishContent(id));
export const useStartSession = () =>
  useCommand((id: string) => api.startSession(id), [keys.plan, keys.warmup]);
export const useFinishSession = () => useCommand((n: NotesInput) => api.finishSession(n));
export const useCancelSession = () =>
  useCommand(() => api.cancelSession(), [keys.plan, keys.warmup, keys.history, keys.stats]);
export const useStartWarmup = () => useCommand(() => api.startWarmup(), [keys.warmup, keys.plan]);
export const useFinishWarmup = () =>
  useCommand(
    (a: RecallAnswer[]) => api.finishWarmup(a),
    [keys.warmup, keys.plan, keys.today, keys.history, keys.stats],
  );
export const useCancelWarmup = () => useCommand(() => api.cancelWarmup(), [keys.warmup, keys.plan]);
export const useAddChallenge = () =>
  useCommand(
    (a: { contentId: string; description: string; level: MasteryLevel }) =>
      api.addChallenge(a.contentId, a.description, a.level),
    [keys.plan],
  );
export const useSolveChallenge = () =>
  useCommand((a: { contentId: string; challengeId: string; evidence: string }) =>
    api.solveChallenge(a.contentId, a.challengeId, a.evidence),
  );
export const useChangeTimezone = () =>
  useCommand(
    (tz: string) => api.changeTimezone(tz),
    [keys.plan, keys.today, keys.week, keys.stats, keys.warmup],
  );

export function useAuthCommand<TArgs>(fn: (args: TArgs) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      clearAllRecallDrafts();
      return qc.resetQueries();
    },
  });
}
export const useRenameContent = () =>
  useCommand(
    (a: { contentId: string; title: string }) => api.renameContent(a.contentId, a.title),
    [
      keys.plan,
      keys.today,
      keys.week,
      keys.competencies,
      keys.recommendations,
      keys.warmup,
      ["schedule"],
    ],
  );
export const useRemoveContent = () =>
  useCommand(
    (id: string) => api.removeContent(id),
    [
      keys.plan,
      keys.today,
      keys.week,
      keys.competencies,
      keys.recommendations,
      keys.warmup,
      keys.notebooks,
      ["schedule"],
    ],
  );
export const useChangePreferences = () =>
  useCommand(
    (p: { minutes: number; restDays: number[]; maxInProgress?: number }) =>
      api.changePreferences(p.minutes, p.restDays, p.maxInProgress),
    [keys.plan, keys.today, keys.week],
  );

// ------------------------------------------------------------------ admin
export const useRegistrationStatus = (enabled = true) =>
  useQuery({ queryKey: keys.registration, queryFn: api.registrationStatus, enabled });

export const useAdminAccounts = () =>
  useInfiniteQuery({
    queryKey: keys.adminAccounts,
    queryFn: ({ pageParam }) => api.adminAccounts(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  });

export const useAdminRegistration = () =>
  useQuery({ queryKey: keys.adminRegistration, queryFn: api.adminRegistration });

export function useSetRegistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (open: boolean) => api.setRegistration(open),
    onSuccess: (data) => qc.setQueryData(keys.adminRegistration, data),
  });
}

export function useAdminDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.adminDeleteAccount(id),
    onSettled: () => qc.invalidateQueries({ queryKey: keys.adminAccounts }),
  });
}

/** Troca o username: a sessão continua, só o `me` em cache é atualizado. */
export function useChangeUsername() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (a: { username: string; password: string }) =>
      api.changeUsername(a.username, a.password),
    onSuccess: (me) => qc.setQueryData(keys.me, me),
  });
}
