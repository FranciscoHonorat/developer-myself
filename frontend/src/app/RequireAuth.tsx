import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { useMe } from "@/api/hooks";
import { Skeleton } from "@/components/ui/skeleton";

/** Sem sessão: vai para /entrar lembrando de onde veio, para voltar depois do login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();
  const location = useLocation();
  if (me.isPending) {
    return (
      <div className="mx-auto flex max-w-5xl flex-col gap-4 p-4" aria-busy="true">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (me.isError) return <Navigate to="/entrar" replace state={{ from: location }} />;
  return children;
}
