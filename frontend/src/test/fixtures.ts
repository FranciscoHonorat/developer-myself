import type { DayPlan, Plan, Today, TodayItem, WeekBlock } from "../api/types";
import { makeContent } from "./render";

export function makePlan(overrides: Partial<Plan> = {}): Plan {
  return {
    timezone: "America/Sao_Paulo",
    preferences: { minutes_per_day: 210, rest_days: [] },
    max_in_progress: 3,
    server_time: "2026-11-20T13:00:00Z",
    last_review_on: null,
    reviewed_today: false,
    needs_review_today: false,
    active_session: null,
    contents: [makeContent()],
    ...overrides,
  };
}

export function makeDayPlan(overrides: Partial<DayPlan> = {}): DayPlan {
  return {
    day: 4,
    phase: "Fundamentos (rumo a Intermediário)",
    kind: "STUDY",
    focus: "nomes e funções",
    activity: "Estude nomes e funções.",
    warmup: [],
    target_level: null,
    done: false,
    ...overrides,
  };
}

export function makeTodayItem(overrides: Partial<TodayItem> = {}): TodayItem {
  return {
    content_id: "c1",
    title: "Clean Code",
    day: 4,
    total_days: 30,
    plan: makeDayPlan(),
    ...overrides,
  };
}

export function makeBlock(overrides: Partial<WeekBlock> = {}): WeekBlock {
  return {
    kind: "STUDY",
    content_id: "c1",
    title: "Clean Code",
    competency: "fundamentos",
    competency_name: "Fundamentos",
    pomodoros: 2,
    minutes: 50,
    first_day: 4,
    last_day: 4,
    focus: "nomes e funções",
    ...overrides,
  };
}

export function makeToday(overrides: Partial<Today> = {}): Today {
  return { studies: [], reviews: [], blocks: [], ...overrides };
}
