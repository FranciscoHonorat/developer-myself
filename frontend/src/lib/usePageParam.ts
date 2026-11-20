import { useCallback } from "react";
import { useSearchParams } from "react-router";

/**
 * Página atual guardada na URL (`?fila=2`): F5 e o botão voltar mantêm a posição.
 * Preserva os outros parâmetros; a página 1 sai da URL para não poluí-la.
 */
export function usePageParam(name: string): [number | null, (page: number) => void] {
  const [params, setParams] = useSearchParams();
  const raw = params.get(name);
  const page = raw === null ? null : Number.parseInt(raw, 10);

  const setPage = useCallback(
    (next: number) =>
      setParams((prev) => {
        const out = new URLSearchParams(prev);
        if (next <= 1) out.delete(name);
        else out.set(name, String(next));
        return out;
      }),
    [name, setParams],
  );
  return [page, setPage];
}
