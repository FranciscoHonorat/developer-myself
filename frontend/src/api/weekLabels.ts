import type { WeekBlock } from "./types";

export const BLOCK_LABEL: Record<WeekBlock["kind"], string> = {
  REVIEW: "🔁 Revisão",
  STUDY: "📖 Estudo",
  CHALLENGE: "🎯 Desafio",
};

export const WEEKDAY_SHORT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

export function hours(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h${m.toString().padStart(2, "0")}` : `${h}h`;
}

export function daysLabel(b: WeekBlock): string {
  return b.first_day === b.last_day ? `dia ${b.first_day}` : `dias ${b.first_day}–${b.last_day}`;
}
