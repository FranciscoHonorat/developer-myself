import { Timer } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { usePlan } from "@/api/hooks";
import { cn } from "@/lib/utils";

function elapsed(startedAt: string, now: number): string {
  const minutes = Math.max(0, Math.floor((now - Date.parse(startedAt)) / 60_000));
  return minutes < 60
    ? `${minutes}m`
    : `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`;
}

/** Sessão em andamento vista de qualquer seção: um toque leva de volta ao Hoje. */
export function SessionIndicator({ className }: { className?: string }) {
  const session = usePlan().data?.active_session ?? null;
  const { pathname } = useLocation();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => window.clearInterval(id);
  }, []);

  if (!session || pathname === "/hoje") return null;
  return (
    <Link
      to="/hoje"
      aria-label={`Sessão em andamento: ${session.content_title}`}
      className={cn(
        "flex items-center gap-2 rounded-md border border-primary/40 bg-accent px-3 py-2 text-xs text-accent-foreground",
        "outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Timer aria-hidden className="size-4 shrink-0 motion-safe:animate-pulse" />
      <span className="truncate">{session.content_title}</span>
      <span className="ml-auto font-mono tabular-nums">{elapsed(session.started_at, now)}</span>
    </Link>
  );
}
