import { Flame, TriangleAlert, Zap } from "lucide-react";
import { Link } from "react-router";
import { useCompetencies, useStats } from "@/api/hooks";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { levelProgress } from "@/features/progress/xp";
import { cn } from "@/lib/utils";

/** Sequência, nível/XP e skills enferrujando: o motor de motivação, no topo do Hoje. */
export function GamificationStrip() {
  const stats = useStats();
  const sheet = useCompetencies();

  if (stats.isPending || sheet.isPending) {
    return (
      <div className="grid grid-cols-2 gap-3" aria-busy="true">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    );
  }

  const streak = stats.data?.current_streak_days ?? 0;
  const s = sheet.data;
  const pct = s ? levelProgress(s) : 0;
  const rusting = (s?.competencies ?? []).filter((c) => c.status === "enferrujando");

  return (
    <section aria-label="Seu progresso" className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <div
          className={cn(
            "flex items-center gap-2.5 rounded-xl border bg-card p-3 sm:gap-3 sm:p-4",
            streak > 0 && "border-primary/40",
          )}
        >
          <Flame
            aria-hidden
            className={cn(
              "size-6 shrink-0 sm:size-8",
              streak > 0 ? "text-primary" : "text-muted-foreground",
            )}
          />
          <div className="min-w-0">
            <p className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
              streak
            </p>
            <p className="font-semibold leading-tight sm:text-lg">
              {streak} {streak === 1 ? "dia seguido" : "dias seguidos"}
            </p>
          </div>
        </div>
        {s && (
          <div className="flex flex-col justify-center gap-2 rounded-xl border bg-card p-3 sm:p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5">
              <p className="flex items-center gap-1.5 whitespace-nowrap font-semibold leading-tight sm:text-lg">
                <Zap aria-hidden className="size-4 text-primary" />
                Nível {s.level}
              </p>
              <p className="font-mono text-xs text-muted-foreground tabular-nums">
                {s.xp}/{s.next_level_xp} xp
              </p>
            </div>
            <Progress value={pct} aria-label={`XP até o nível ${s.level + 1}`} />
          </div>
        )}
      </div>
      {rusting.map((c) => (
        <Link
          key={c.key}
          to="/progresso?aba=competencias"
          className="flex items-center gap-2 rounded-lg border border-rust/50 bg-card px-4 py-2.5 text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        >
          <TriangleAlert aria-hidden className="size-4 shrink-0 text-rust-text" />
          <span>
            <strong>{c.name}</strong> está enferrujando: revise ou resolva um desafio.
          </span>
        </Link>
      ))}
    </section>
  );
}
