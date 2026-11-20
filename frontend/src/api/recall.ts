import type { ActiveSession } from "./types";

/**
 * Revisão com teste de memória em andamento neste conteúdo: o caderno dele só abre pelo
 * painel da sessão, que o libera depois de conferir as respostas.
 */
export const recallTestOn = (session: ActiveSession | null, contentId: string): boolean =>
  session?.kind === "REVIEW" && session.questions.length > 0 && session.content_id === contentId;
