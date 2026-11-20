import { CalendarCheck, NotebookPen, Route } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { usePlan, useToday } from "@/api/hooks";
import type { Outcome } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { needsOnboarding } from "@/features/onboarding/needsOnboarding";
import { OnboardingGuide } from "@/features/onboarding/OnboardingGuide";
import { OutcomeDialog } from "@/features/session/OutcomeDialog";
import { SessionPanel } from "@/features/session/SessionPanel";
import { DayList } from "@/features/today/DayList";
import { dayItems, localDate, nextStep } from "@/features/today/day";
import { GamificationStrip } from "@/features/today/GamificationStrip";
import { NextStepCard } from "@/features/today/NextStepCard";
import { ReviewSuggestion } from "@/features/today/ReviewSuggestion";
import { WeekStrip } from "@/features/today/WeekStrip";

function greeting(hour: number): string {
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

/** Abrir → ver o que fazer → Iniciar. Tudo no Hoje gira em torno do próximo passo. */
export function TodayPage() {
  const plan = usePlan();
  const today = useToday();
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [guide, setGuide] = useState<"auto" | "active" | "closed">("auto");

  if (plan.isPending || today.isPending) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }
  if (plan.isError) return <ErrorState error={plan.error} onRetry={() => plan.refetch()} />;
  if (today.isError) return <ErrorState error={today.error} onRetry={() => today.refetch()} />;

  const p = plan.data;
  const now = new Date(p.server_time);
  const hour = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: p.timezone,
      hour: "numeric",
      hour12: false,
    }).format(now),
  );
  const dateLabel = new Intl.DateTimeFormat("pt-BR", {
    timeZone: p.timezone,
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(now);
  const items = dayItems(today.data, p, localDate(now, p.timezone));
  const next = nextStep(items);
  const active = p.active_session;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <p className="font-mono text-xs text-muted-foreground">{dateLabel}</p>
        <h1 className="text-2xl font-semibold tracking-tight">{greeting(hour % 24)}</h1>
      </header>

      <GamificationStrip />

      <OutcomeDialog outcome={outcome} onClose={() => setOutcome(null)} />

      {guide !== "closed" && (guide === "active" || needsOnboarding(p)) ? (
        <OnboardingGuide
          prefs={p.preferences}
          onStarted={() => setGuide("active")}
          onDone={() => setGuide("closed")}
        />
      ) : active ? (
        <SessionPanel session={active} serverTime={p.server_time} onFinished={setOutcome} />
      ) : next ? (
        <NextStepCard item={next} mustReviewFirst={p.needs_review_today} />
      ) : items.length > 0 ? (
        <section className="flex flex-col items-start gap-3 rounded-2xl border bg-card p-6">
          <CalendarCheck aria-hidden className="size-8 text-primary" />
          <h2 className="text-xl font-semibold">Dia concluído</h2>
          <p className="text-sm text-muted-foreground">
            Tudo feito por hoje. Que tal registrar no caderno o que ficou dessa jornada?
          </p>
          <Button asChild variant="outline">
            <Link to="/caderno">
              <NotebookPen aria-hidden /> Abrir caderno
            </Link>
          </Button>
        </section>
      ) : (
        <section className="flex flex-col items-start gap-3 rounded-2xl border border-dashed bg-card p-6">
          <h2 className="text-xl font-semibold">Nada planejado para hoje</h2>
          <p className="text-sm text-muted-foreground">
            Adicione conteúdos na Trilha: o primeiro da fila vira o seu próximo passo.
          </p>
          <Button asChild>
            <Link to="/trilha">
              <Route aria-hidden /> Ir para a Trilha
            </Link>
          </Button>
        </section>
      )}

      <DayList items={items} sessionActive={active !== null} />
      <WeekStrip />
      <ReviewSuggestion />
    </div>
  );
}
