import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
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

/** Área de admin: quem não é admin volta para o Hoje. A API confere de novo (403). */
export function RequireAdmin() {
  const me = useMe();
  if (me.isPending) return null;
  if (!me.data?.is_admin) return <Navigate to="/hoje" replace />;
  return <Outlet />;
}
