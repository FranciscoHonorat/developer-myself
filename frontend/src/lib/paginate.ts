/** Paginação no cliente: a lista já veio inteira (a trilha é um agregado só, em `/plan`). */
export interface PageOf<T> {
  items: T[];
  page: number;
  totalPages: number;
}

export function paginate<T>(all: readonly T[], page: number, size: number): PageOf<T> {
  const totalPages = Math.max(1, Math.ceil(all.length / size));
  // Página fora do intervalo (URL antiga, item removido) cai na mais próxima válida.
  const safe = Number.isFinite(page) ? Math.min(Math.max(1, Math.trunc(page)), totalPages) : 1;
  return { items: all.slice((safe - 1) * size, safe * size), page: safe, totalPages };
}

export function pageContaining<T>(
  all: readonly T[],
  match: (item: T) => boolean,
  size: number,
): number | null {
  const index = all.findIndex(match);
  return index < 0 ? null : Math.floor(index / size) + 1;
}
