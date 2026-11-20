import type { Plan, Today, TodayItem } from "@/api/types";

export type DayItemState = "done" | "next" | "later";

export interface DayItem {
  contentId: string;
  title: string;
  kind: "REVIEW" | "STUDY";
  day: number;
  totalDays: number;
  focus: string;
  pomodoros: number;
  minutes: number;
  state: DayItemState;
}

/** Data local (YYYY-MM-DD) de um instante no fuso dado. */
export function localDate(instant: string | Date, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(instant));
}

/**
 * O dia em ordem de execução: revisões antes de estudos. "Feito" sai dos dados que a API já
 * tem (sessão hoje no conteúdo; revisão do dia feita); o primeiro não-feito é o próximo passo.
 */
export function dayItems(today: Today, plan: Plan, date: string): DayItem[] {
  const studiedToday = new Set(
    plan.contents
      .filter((c) => c.last_session_at && localDate(c.last_session_at, plan.timezone) === date)
      .map((c) => c.id),
  );
  const block = (id: string) => today.blocks.find((b) => b.content_id === id);
  const toItem = (item: TodayItem, kind: DayItem["kind"]) => {
    const b = block(item.content_id);
    const done = studiedToday.has(item.content_id) || (kind === "REVIEW" && plan.reviewed_today);
    return {
      contentId: item.content_id,
      title: item.title,
      kind,
      day: item.day,
      totalDays: item.total_days,
      focus: item.plan.focus,
      pomodoros: b?.pomodoros ?? 0,
      minutes: b?.minutes ?? 0,
      done,
    };
  };
  const ordered = [
    ...today.reviews.map((i) => toItem(i, "REVIEW")),
    ...today.studies.map((i) => toItem(i, "STUDY")),
  ];
  let nextTaken = false;
  return ordered.map(({ done, ...item }) => {
    if (done) return { ...item, state: "done" };
    if (nextTaken) return { ...item, state: "later" };
    nextTaken = true;
    return { ...item, state: "next" };
  });
}

export function nextStep(items: DayItem[]): DayItem | null {
  return items.find((i) => i.state === "next") ?? null;
}
