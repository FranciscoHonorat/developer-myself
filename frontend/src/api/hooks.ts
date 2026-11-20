// TanStack Query: o estado global é o servidor. Cada comando invalida o que mudou.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { ContentKind, MasteryLevel, NotesInput } from "./types";

export const keys = {
  me: ["me"] as const,
  plan: ["plan"] as const,
  history: ["history"] as const,
  stats: ["stats"] as const,
  recommendations: ["recommendations"] as const,
  today: ["today"] as const,
  week: ["week"] as const,
  competencies: ["competencies"] as const,
  schedule: (id: string) => ["schedule", id] as const,
  notebook: (id: string) => ["notebook", id] as const,
  notebooks: ["notebooks"] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: api.me, retry: false });
export const usePlan = () => useQuery({ queryKey: keys.plan, queryFn: api.plan });
export const useHistory = () => useQuery({ queryKey: keys.history, queryFn: () => api.history() });
export const useRecommendations = () =>
  useQuery({ queryKey: keys.recommendations, queryFn: api.recommendations });
export const useToday = () => useQuery({ queryKey: keys.today, queryFn: api.today });
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

function useCommand<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: keys.plan }),
        qc.invalidateQueries({ queryKey: keys.history }),
        qc.invalidateQueries({ queryKey: keys.stats }),
        qc.invalidateQueries({ queryKey: keys.recommendations }),
        qc.invalidateQueries({ queryKey: keys.today }),
        qc.invalidateQueries({ queryKey: keys.week }),
        qc.invalidateQueries({ queryKey: keys.competencies }),
        qc.invalidateQueries({ queryKey: ["schedule"] }),
      ]),
  });
}

export const useAddContent = () =>
  useCommand((a: { title: string; kind: ContentKind }) => api.addContent(a.title, a.kind));
export const useFinishContent = () => useCommand((id: string) => api.finishContent(id));
export const useStartSession = () => useCommand((id: string) => api.startSession(id));
export const useFinishSession = () => useCommand((n: NotesInput) => api.finishSession(n));
export const useCancelSession = () => useCommand(() => api.cancelSession());
export const useAddChallenge = () =>
  useCommand((a: { contentId: string; description: string; level: MasteryLevel }) =>
    api.addChallenge(a.contentId, a.description, a.level),
  );
export const useSolveChallenge = () =>
  useCommand((a: { contentId: string; challengeId: string; evidence: string }) =>
    api.solveChallenge(a.contentId, a.challengeId, a.evidence),
  );
export const useChangeTimezone = () => useCommand((tz: string) => api.changeTimezone(tz));

export function useAuthCommand<TArgs>(fn: (args: TArgs) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.resetQueries(),
  });
}
export const useRenameContent = () =>
  useCommand((a: { contentId: string; title: string }) => api.renameContent(a.contentId, a.title));
export const useRemoveContent = () => useCommand((id: string) => api.removeContent(id));
export const useChangePreferences = () =>
  useCommand((p: { minutes: number; restDays: number[] }) =>
    api.changePreferences(p.minutes, p.restDays),
  );
