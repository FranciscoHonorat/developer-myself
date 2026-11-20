import type { DayPlan } from "./types";

export const DAY_KIND_LABEL: Record<DayPlan["kind"], string> = {
  STUDY: "Estudo",
  PRACTICE: "Prática",
  CHALLENGE: "Desafio",
  TEACH: "Ensinar",
  REVIEW: "Revisão geral",
};
