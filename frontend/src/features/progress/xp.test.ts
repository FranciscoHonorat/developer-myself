import { describe, expect, it } from "vitest";
import { levelProgress } from "./xp";

describe("levelProgress", () => {
  it("é a fração do caminho entre o XP do nível atual e o do próximo", () => {
    // nível 4 começa em 50·3² = 450; o 5 em 1000 → (620−450)/(1000−450) ≈ 31%
    expect(levelProgress({ xp: 620, level: 4, next_level_xp: 1000 })).toBe(31);
  });

  it("no começo do nível 1 é 0 e nunca passa de 100", () => {
    expect(levelProgress({ xp: 0, level: 1, next_level_xp: 50 })).toBe(0);
    expect(levelProgress({ xp: 80, level: 1, next_level_xp: 50 })).toBe(100);
  });
});
