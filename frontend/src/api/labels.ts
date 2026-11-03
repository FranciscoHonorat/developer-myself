import type { ContentKind, ContentStatus, MasteryLevel, SessionKind } from "./types";

export const LEVEL_LABEL: Record<MasteryLevel, string> = {
  BEGINNER: "Iniciante",
  INTERMEDIATE: "Intermediário",
  ADVANCED: "Avançado",
};

export const STATUS_LABEL: Record<ContentStatus, string> = {
  LOCKED: "Bloqueado",
  IN_PROGRESS: "Em andamento",
  CONSOLIDATED: "Consolidado",
  FINISHED: "Concluído",
};

export const KIND_LABEL: Record<ContentKind, string> = {
  BOOK: "Livro",
  COURSE: "Curso",
  ARTICLE: "Artigo",
  VIDEO: "Vídeo",
  OTHER: "Outro",
};

export const SESSION_LABEL: Record<SessionKind, string> = {
  STUDY: "Estudo",
  REVIEW: "Revisão",
};

/** Escala de autoavaliação (Anki/FSRS): o rótulo real da rede neural. */
export const RECALL_LABEL: Record<number, string> = {
  1: "Esqueci",
  2: "Difícil",
  3: "Bem",
  4: "Fácil",
};

export const REASON_LABEL: Record<string, string> = {
  TOO_SHORT: "Sessão curta: são precisos pelo menos 25 minutos.",
  NO_NOTES:
    "Anotações insuficientes: preencha os três campos com pelo menos 50 caracteres (sem contar espaços).",
  NO_REVIEW: "Você não revisou nada hoje antes de estudar conteúdo novo.",
  EXPIRED: "A sessão passou de 4 horas e foi considerada abandonada.",
  CANCELLED: "Sessão cancelada.",
};

/** Contagem só para feedback visual; quem decide é o servidor. */
export function charsWithoutSpaces(...fields: string[]): number {
  return fields.reduce((sum, f) => sum + f.replace(/\s/g, "").length, 0);
}

export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}
