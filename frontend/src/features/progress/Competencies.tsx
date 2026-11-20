import { CircleCheck, CircleDashed, Hourglass, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { useCompetencies } from "@/api/hooks";
import type { Competency, CompetencySheet, CompetencyStatus } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { levelProgress } from "./xp";

const STATUS: Record<
  CompetencyStatus,
  { icon: typeof CircleCheck; tone: string; label: (c: Competency) => string }
> = {
  "em dia": { icon: CircleCheck, tone: "text-primary", label: () => "em dia" },
  "enferruja em breve": {
    icon: Hourglass,
    tone: "text-warning",
    label: (c) => `enferruja em ${c.rust_in_days} dia${c.rust_in_days === 1 ? "" : "s"}`,
  },
  enferrujando: {
    icon: TriangleAlert,
    tone: "text-rust-text",
    label: (c) => `enferrujando: −${c.rust_lost.toFixed(1)} (revise ou resolva um desafio)`,
  },
  "sem progresso": {
    icon: CircleDashed,
    tone: "text-muted-foreground",
    label: () => "ainda não iniciada",
  },
};

const card = "rounded-xl border bg-card p-4 sm:p-5";

export function Competencies() {
  const sheet = useCompetencies();
  if (sheet.isPending) return <Skeleton className="h-64 w-full" />;
  if (sheet.isError) return <ErrorState error={sheet.error} onRetry={() => sheet.refetch()} />;
  const s = sheet.data;
  if (s.competencies.length === 0)
    return (
      <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
        Adicione conteúdos à trilha para ver suas competências.
      </p>
    );

  const ranked = [...s.competencies].sort((a, b) => b.score - a.score || b.peak - a.peak);
  const rusting = s.competencies.filter((c) => c.status === "enferrujando").length;

  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Resumo" className="grid gap-3 sm:grid-cols-3">
        <div className={cn(card, "flex flex-col gap-2 border-primary/40")}>
          <div className="text-2xl font-semibold">Nível {s.level}</div>
          <Progress value={levelProgress(s)} aria-label="XP até o próximo nível" />
          <div className="font-mono text-xs text-muted-foreground">
            {s.xp} XP · próximo nível em {s.next_level_xp} XP
          </div>
        </div>
        <div className={card}>
          <div className="font-mono text-2xl font-semibold tabular-nums">{s.total_points}</div>
          <div className="text-sm text-muted-foreground">pontos conquistados</div>
        </div>
        <div className={card}>
          <div
            className={cn(
              "font-mono text-2xl font-semibold tabular-nums",
              rusting > 0 && "text-rust-text",
            )}
          >
            {rusting}
          </div>
          <div className="text-sm text-muted-foreground">
            {rusting === 1 ? "competência enferrujando" : "competências enferrujando"}
          </div>
        </div>
      </section>

      <EffortBar sheet={s} />

      <section aria-labelledby="h-skills" className={cn(card, "flex flex-col gap-4")}>
        <div className="flex flex-col gap-1">
          <h2 id="h-skills" className="text-lg font-semibold">
            Competências
          </h2>
          <p className="text-xs text-muted-foreground">
            Barra = nível atual (0 a 100). Trecho laranja = perdido para a ferrugem. Traço vertical
            = meta do mapa para o perfil DevSecOps. Faixas: Aprendiz · Praticante (25) · Proficiente
            (50) · Especialista (75).
          </p>
        </div>
        <ul className="flex flex-col divide-y">
          {ranked.map((c) => (
            <SkillRow key={c.key} c={c} />
          ))}
        </ul>
        <p className="text-xs text-muted-foreground">
          Ferrugem: sem revisar nem resolver desafios de um conteúdo por mais de{" "}
          {s.rules.grace_days} dias, a contribuição dele cai {s.rules.decay_per_day * 100}% ao dia,
          até {s.rules.floor * 100}%. Seus pontos nunca diminuem; uma revisão tira a ferrugem na
          hora.
        </p>
      </section>
    </div>
  );
}

function SkillRow({ c }: { c: Competency }) {
  const [open, setOpen] = useState(false);
  const status = STATUS[c.status];
  const Icon = status.icon;
  return (
    <li className="flex flex-col gap-2 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong className="font-medium">{c.name}</strong>
        <span className="flex items-center gap-2 text-sm">
          <Badge variant="outline">{c.tier}</Badge>
          <span className="font-mono tabular-nums">{c.score.toFixed(0)}</span>
          {c.target_score !== null && (
            <span className="font-mono text-xs text-muted-foreground">
              {" "}
              / meta {c.target_score}
            </span>
          )}
        </span>
      </div>
      <meter
        className="sr-only"
        aria-label={`${c.name}: ${c.score.toFixed(0)} de 100${c.target ? `, meta ${c.target}` : ""}`}
        min={0}
        max={100}
        value={c.score}
      />
      <div
        aria-hidden="true"
        title={`${c.title} · ${c.score.toFixed(1)} (pico ${c.peak.toFixed(1)}) · ${c.points} pts`}
        className="relative h-2 rounded-full bg-[var(--seq-track)]"
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-[var(--seq-fill)]"
          style={{ width: `${c.score}%` }}
        />
        {c.rust_lost > 0 && (
          <div
            className="absolute inset-y-0 rounded-full bg-rust"
            style={{
              left: `calc(${c.score}% + 2px)`,
              width: `max(0px, calc(${c.rust_lost}% - 2px))`,
            }}
          />
        )}
        {c.target_score !== null && (
          <div
            className="absolute -inset-y-1 w-0.5 bg-foreground"
            style={{ left: `${c.target_score}%` }}
          />
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className={cn("flex items-center gap-1.5", status.tone)}>
          <Icon aria-hidden className="size-3.5" /> {status.label(c)}
        </span>
        <Button
          variant="link"
          size="sm"
          className="h-auto p-0 text-xs"
          onClick={() => setOpen((v) => !v)}
        >
          {open
            ? "Ocultar conteúdos"
            : `Ver ${c.contents.length} conteúdo${c.contents.length === 1 ? "" : "s"}`}
        </Button>
      </div>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[28rem] text-sm [&_td]:px-2 [&_td]:py-1.5 [&_th]:px-2 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-medium [&_tr]:border-b">
            <caption className="sr-only">Conteúdos que contam para {c.name}</caption>
            <thead className="text-xs text-muted-foreground">
              <tr>
                <th scope="col">Conteúdo</th>
                <th scope="col">Progresso</th>
                <th scope="col">Conservação</th>
                <th scope="col">Ferrugem</th>
              </tr>
            </thead>
            <tbody>
              {c.contents.map((x) => (
                <tr key={x.title}>
                  <td>{x.title}</td>
                  <td className="font-mono tabular-nums">{Math.round(x.progress * 100)}%</td>
                  <td className="font-mono tabular-nums">{Math.round(x.freshness * 100)}%</td>
                  <td>
                    {x.rust_in_days === null
                      ? "—"
                      : x.rust_in_days === 0
                        ? "enferrujando"
                        : `em ${x.rust_in_days} d`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </li>
  );
}

/** Para onde foi o esforço: barras ranqueadas por área (uma cor só, o número ao lado). */
function EffortBar({ sheet }: { sheet: CompetencySheet }) {
  const total = sheet.total_points;
  const ranked = [...sheet.effort].sort((a, b) => b.points - a.points);
  const max = Math.max(...ranked.map((e) => e.points), 1);
  return (
    <section aria-labelledby="h-effort" className={cn(card, "flex flex-col gap-3")}>
      <h2 id="h-effort" className="text-lg font-semibold">
        Para onde foi seu esforço
      </h2>
      {total === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhum ponto ainda: a primeira sessão pontuada aparece aqui.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {ranked.map((e) => (
            <li
              key={e.area}
              className="grid grid-cols-[minmax(0,8rem)_1fr_auto] items-center gap-3 text-sm"
            >
              <span className="truncate">{e.area}</span>
              <div aria-hidden="true" className="h-2 rounded-full bg-[var(--seq-track)]">
                <div
                  className="h-full rounded-full bg-[var(--seq-fill)]"
                  style={{ width: `${(e.points / max) * 100}%` }}
                />
              </div>
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                {e.points} pts · {Math.round((e.points / total) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
