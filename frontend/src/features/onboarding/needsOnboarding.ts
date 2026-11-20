import type { Plan } from "@/api/types";

/** Primeira vez: trilha sem nenhum conteúdo. */
export const needsOnboarding = (plan: Plan): boolean => plan.contents.length === 0;
