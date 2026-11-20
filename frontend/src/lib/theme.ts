/** Tema da interface: escuro por padrão; a escolha fica só neste navegador. */
export type ThemeChoice = "dark" | "light" | "system";

const KEY = "dm-theme";
const CHOICES: readonly ThemeChoice[] = ["dark", "light", "system"];

export function readTheme(): ThemeChoice {
  try {
    const saved = localStorage.getItem(KEY);
    return CHOICES.find((c) => c === saved) ?? "dark";
  } catch {
    return "dark";
  }
}

export function saveTheme(theme: ThemeChoice): void {
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // sem storage (aba privada, bloqueio): vale só nesta visita
  }
}

export function isDark(theme: ThemeChoice): boolean {
  return theme === "system"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
    : theme === "dark";
}

export function applyTheme(theme: ThemeChoice): void {
  document.documentElement.classList.toggle("dark", isDark(theme));
}
