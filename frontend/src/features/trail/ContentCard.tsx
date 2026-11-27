import { ArrowDown, ArrowUp, Compass, Lock, Play, RotateCcw, Target } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import {
  useChangeContentPurpose,
  useFinishContent,
  useRemoveContent,
  useRenameContent,
  useStartSession,
} from "@/api/hooks";
import { KIND_LABEL, LEVEL_LABEL, STATUS_LABEL } from "@/api/labels";
import type { Content, ContentStatus } from "@/api/types";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState } from "@/components/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ChallengeList } from "./ChallengeList";
import { ContentActions } from "./ContentActions";
import { ScheduleView } from "./ScheduleView";

interface Props {
  content: Content;
  hasActiveSession: boolean;
  /** Teste de memória deste conteúdo em andamento: sem caderno fora do painel da sessão. */
  notebookLocked?: boolean;
  onMoveUp?: (() => void) | undefined;
  onMoveDown?: (() => void) | undefined;
  reordering?: boolean;
}

const STATUS_STYLE: Record<ContentStatus, string> = {
  IN_PROGRESS: "border-primary/50 bg-accent text-accent-foreground",
  CONSOLIDATED: "text-foreground",
  FINISHED: "text-muted-foreground",
  LOCKED: "text-muted-foreground",
};

export function ContentCard({
  content,
  hasActiveSession,
  notebookLocked = false,
  onMoveUp,
  onMoveDown,
  reordering = false,
}: Props) {
  const navigate = useNavigate();
  const start = useStartSession();
  const finish = useFinishContent();
  const rename = useRenameContent();
  const changePurpose = useChangeContentPurpose();
  const remove = useRemoveContent();
  const [panel, setPanel] = useState<"challenges" | "schedule" | null>(null);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(content.title);
  const [editingPurpose, setEditingPurpose] = useState(false);
  const [purpose, setPurpose] = useState(content.purpose ?? "");
  const [confirm, setConfirm] = useState<"finish" | "remove" | null>(null);

  const hasProgress =
    content.points > 0 ||
    content.last_session_at !== null ||
    content.challenges.some((c) => c.solved);
  const locked = content.status === "LOCKED";
  const finishable = content.status === "IN_PROGRESS" || content.status === "CONSOLIDATED";
  // Espelha a regra do servidor só para a UX; quem decide é o domínio.
  const atMaxLevel = content.level === "ADVANCED";
  const next = content.next_level;
  const isStudy = content.status === "IN_PROGRESS";
  const solved = content.challenges.filter((c) => c.solved).length;
  const toggle = (p: "challenges" | "schedule") => setPanel((cur) => (cur === p ? null : p));

  return (
    <article
      aria-label={content.title}
      className={cn(
        "flex flex-col gap-4 rounded-xl border bg-card p-4 sm:p-5",
        locked && "border-dashed opacity-80",
      )}
    >
      <header className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          {editing ? (
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                rename.mutate(
                  { contentId: content.id, title },
                  { onSuccess: () => setEditing(false) },
                );
              }}
            >
              <Input
                aria-label="Novo título"
                value={title}
                maxLength={200}
                onChange={(e) => setTitle(e.target.value)}
                autoFocus
              />
              <Button type="submit" size="sm" disabled={rename.isPending}>
                Salvar
              </Button>
            </form>
          ) : (
            <h3 className="truncate text-base font-semibold">{content.title}</h3>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <span>{KIND_LABEL[content.kind]}</span>
            <Badge variant="outline" className={STATUS_STYLE[content.status]}>
              {STATUS_LABEL[content.status]}
            </Badge>
            <Badge variant="outline">{LEVEL_LABEL[content.level]}</Badge>
            {content.daily && content.status === "IN_PROGRESS" ? (
              <Badge variant="outline" title="Hábito diário: 2 pomodoros por dia, fora das vagas">
                Todo dia
              </Badge>
            ) : null}
          </div>
        </div>
        <p className="shrink-0 text-right font-mono">
          <span className="text-xl font-semibold tabular-nums">{content.points}</span>
          <span className="text-xs text-muted-foreground"> pts</span>
        </p>
        <ContentActions
          content={content}
          notebookLocked={notebookLocked}
          canFinish={finishable}
          atMaxLevel={atMaxLevel}
          canRemove={!hasProgress}
          onRename={() => setEditing((v) => !v)}
          onEditPurpose={() => {
            setPurpose(content.purpose ?? "");
            setEditingPurpose((v) => !v);
          }}
          onSchedule={() => toggle("schedule")}
          onChallenges={() => toggle("challenges")}
          onFinish={() => setConfirm("finish")}
          onRemove={() => setConfirm("remove")}
        />
      </header>

      {editingPurpose ? (
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            changePurpose.mutate(
              { contentId: content.id, purpose: purpose.trim() || null },
              { onSuccess: () => setEditingPurpose(false) },
            );
          }}
        >
          <Input
            aria-label={`Propósito de ${content.title}`}
            value={purpose}
            maxLength={300}
            placeholder="Por que este conteúdo importa para você?"
            onChange={(e) => setPurpose(e.target.value)}
            autoFocus
          />
          <Button type="submit" size="sm" disabled={changePurpose.isPending}>
            Salvar
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => setEditingPurpose(false)}>
            Cancelar
          </Button>
        </form>
      ) : (
        content.purpose && (
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
            <Compass aria-hidden className="mt-0.5 size-3.5 shrink-0 text-primary" />
            <span>{content.purpose}</span>
          </p>
        )
      )}

      {locked && (
        <div className="flex flex-col gap-2">
          <p className="flex items-start gap-2 text-sm text-muted-foreground">
            <Lock aria-hidden className="mt-0.5 size-4 shrink-0" />
            <span>
              <span className="font-mono">#{content.queue_position}</span> na fila.{" "}
              {content.lock_reason}
            </span>
          </p>
          {(onMoveUp || onMoveDown) && (
            <div className="flex flex-wrap gap-1.5">
              {onMoveUp && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={reordering}
                  aria-label={`Subir ${content.title} na fila`}
                  onClick={onMoveUp}
                >
                  <ArrowUp aria-hidden className="size-3.5" /> Subir na fila
                </Button>
              )}
              {onMoveDown && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={reordering}
                  aria-label={`Descer ${content.title} na fila`}
                  onClick={onMoveDown}
                >
                  <ArrowDown aria-hidden className="size-3.5" /> Descer na fila
                </Button>
              )}
            </div>
          )}
        </div>
      )}

      {next && !locked && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">Para {LEVEL_LABEL[next.level]}:</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Meter label="Pontos" value={content.points} max={next.points_required} />
            <Meter label="Desafios" value={next.challenges_solved} max={next.challenges_required} />
          </div>
          {content.points >= Math.ceil(next.points_required / 2) &&
            next.challenges_solved < next.challenges_required && (
              <p className="text-xs text-muted-foreground">
                Zona de desafio: seus pontos avançaram — um desafio prático agora consolida este
                nível.
              </p>
            )}
        </div>
      )}

      {finishable && !atMaxLevel && (
        <p className="text-xs text-muted-foreground">
          Chegue a Avançado para concluir este conteúdo.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {!locked && (
          <Button
            disabled={hasActiveSession || start.isPending}
            title={hasActiveSession ? "Já existe uma sessão em andamento" : undefined}
            onClick={() =>
              start
                .mutateAsync(content.id)
                .then(() => navigate("/hoje"))
                .catch(() => {})
            }
          >
            {isStudy ? <Play aria-hidden className="fill-current" /> : <RotateCcw aria-hidden />}
            {isStudy ? "Estudar" : "Revisar"}
          </Button>
        )}
        <Button
          variant="outline"
          aria-expanded={panel === "challenges"}
          onClick={() => toggle("challenges")}
        >
          <Target aria-hidden />
          Desafios{" "}
          <span className="font-mono text-xs text-muted-foreground">
            {solved}/{content.challenges.length}
          </span>
        </Button>
      </div>

      <ErrorState
        error={start.error ?? finish.error ?? rename.error ?? changePurpose.error ?? remove.error}
        compact
      />
      {panel === "schedule" && <ScheduleView contentId={content.id} />}
      {panel === "challenges" && <ChallengeList content={content} />}

      <ConfirmDialog
        open={confirm === "finish"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={`Marcar "${content.title}" como concluído?`}
        description="Ele sai da revisão diária e libera espaço na trilha."
        confirmLabel="Concluir"
        onConfirm={() => finish.mutate(content.id)}
      />
      <ConfirmDialog
        open={confirm === "remove"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={`Remover "${content.title}" da trilha?`}
        description="Ele ainda não tem progresso; nada se perde além do item."
        confirmLabel="Remover"
        destructive
        onConfirm={() => remove.mutate(content.id)}
      />
    </article>
  );
}

function Meter({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max === 0 ? 100 : Math.min(100, (value / max) * 100);
  return (
    <div className="flex flex-col gap-1">
      <span className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono tabular-nums">
          {value}/{max}
        </span>
      </span>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className="h-1.5 overflow-hidden rounded-full bg-primary/15"
      >
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
