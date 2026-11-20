import { CircleUser } from "lucide-react";
import { Link, Outlet } from "react-router";
import { Brand } from "./Brand";
import { MainNav } from "./MainNav";
import { SessionIndicator } from "./SessionIndicator";

/** Casca do app logado: navegação responsiva + conteúdo da seção. */
export function AppShell() {
  return (
    <div className="min-h-dvh sm:flex">
      <MainNav />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur sm:hidden">
          <Brand />
          <Link
            to="/conta"
            aria-label="Conta"
            className="ml-auto rounded-full p-1 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          >
            <CircleUser aria-hidden className="size-6" />
          </Link>
        </header>
        <main className="mx-auto w-full max-w-5xl px-4 pt-4 pb-24 sm:px-6 sm:pt-8 sm:pb-10">
          <SessionIndicator className="mb-4" />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
