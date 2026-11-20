import type { CompetencySheet } from "@/api/types";

/** XP em que o nível `level` começa (mesma curva do servidor: 50·(n−1)²). */
export const levelStartXp = (level: number): number => 50 * (level - 1) ** 2;

/** Progresso (0–100, inteiro) dentro do nível atual. */
export function levelProgress(s: Pick<CompetencySheet, "xp" | "level" | "next_level_xp">): number {
  const start = levelStartXp(s.level);
  const span = s.next_level_xp - start;
  if (span <= 0) return 100;
  return Math.max(0, Math.min(100, Math.round(((s.xp - start) / span) * 100)));
}
