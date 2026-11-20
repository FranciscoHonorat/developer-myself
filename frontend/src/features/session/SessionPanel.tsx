import { CircleCheck, NotebookPen, RotateCcw } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useCancelSession, useFinishSession } from "@/api/hooks";
import { charsWithoutSpaces, formatDuration, RECALL_LABEL, SESSION_LABEL } from "@/api/labels";
import type { ActiveSession, Outcome, RecallAnswer } from "@/api/types";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { NotebookEditor } from "@/features/notebook/NotebookEditor";
import { MOBILE_QUERY, useMediaQuery } from "@/lib/useMediaQuery";
import { cn } from "@/lib/utils";
import { RecallSteps } from "./RecallSteps";
import { clearRecallDraft, RecallTest } from "./RecallTest";

const MIN_SECONDS = 25 * 60;
const MIN_CHARS = 50;

interface Props {
  session: ActiveSession;
  serverTime: string;
  onFinished: (outcome: Outcome) => void;
}

/**
 * Uma instância por sessão: se a sessão ativa troca (cancelada e reiniciada em outra aba),
 * anotações, autoavaliação e rascunho do teste recomeçam em vez de vazar da anterior.
 */
export function SessionPanel(props: Props) {
  return <SessionPanelBody key={props.session.started_at} {...props} />;
}

/** O timer é só visual: quem marca início/fim e decide os pontos é o servidor. */
function SessionPanelBody({ session, serverTime, onFinished }: Props) {
  const offset = useMemo(() => Date.parse(serverTime) - Date.now(), [serverTime]);
  const [now, setNow] = useState(() => Date.now() + offset);
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now() + offset), 1000);
    return () => window.clearInterval(id);
  }, [offset]);

  const [studied, setStudied] = useState("");
  const [understood, setUnderstood] = useState("");
  const [toReview, setToReview] = useState("");
  const [recall, setRecall] = useState<number | null>(null);
  const isReview = session.kind === "REVIEW";
  const hasTest = isReview && session.questions.length > 0;
  const recallKey = `recall:${session.started_at}`;
  const [answers, setAnswers] = useState<RecallAnswer[] | null>(null);
  const [checking, setChecking] = useState(false);
  const onTestChange = useCallback((a: RecallAnswer[] | null, isChecking: boolean) => {
    setAnswers(a);
    setChecking(isChecking);
  }, []);
  // Na revisão, o material (caderno e "preciso revisar") só aparece depois de conferir.
  const showMaterial = !hasTest || checking;
  const testDone = !hasTest || answers !== null;
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const step: 1 | 2 | 3 = !checking ? 1 : answers === null ? 2 : 3;
  const finish = useFinishSession();
  const cancel = useCancelSession();

  const elapsed = (now - Date.parse(session.started_at)) / 1000;
  const chars = charsWithoutSpaces(studied, understood, toReview);
  const allFilled = [studied, understood, toReview].every((f) => f.trim() !== "");
  const progress = Math.min(1, elapsed / MIN_SECONDS);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    // mutateAsync, não mutate({onSuccess}): o refetch do plano pode desmontar este painel antes
    // da resposta, e o TanStack não chama callbacks do mutate de componente desmontado.
    finish
      .mutateAsync({
        studied,
        understood,
        to_review: toReview,
        ...(isReview && recall !== null ? { recall_rating: recall } : {}),
        ...(hasTest && answers ? { answers } : {}),
      })
      .then((outcome) => {
        clearRecallDraft(recallKey);
        setStudied("");
        setUnderstood("");
        setToReview("");
        setRecall(null);
        onFinished(outcome);
      })
      .catch(() => {
        // o erro já aparece via finish.error
      });
  };

  const time = (iso: string) =>
    new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const notebook = <NotebookEditor contentId={session.content_id} title={session.content_title} />;
  const notes: [string, string, (v: string) => void][] = [
    ["O que estudei", studied, setStudied],
    ["O que entendi", understood, setUnderstood],
    ["O que preciso revisar", toReview, setToReview],
  ];

  return (
    <div
      className={cn(
        "grid gap-6",
        showMaterial && !isMobile && "lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]",
      )}
    >
      <section
        aria-labelledby="h-session"
        className="flex flex-col gap-6 rounded-2xl border border-primary/40 bg-card p-5 sm:p-6"
      >
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="font-mono text-xs font-semibold uppercase tracking-wider text-primary">
              › sessão em andamento
            </p>
            <h2 id="h-session" className="mt-1 text-xl font-semibold tracking-tight">
              {session.kind ? SESSION_LABEL[session.kind] : "Sessão"}: {session.content_title}
            </h2>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              início {time(session.started_at)} · expira {time(session.expires_at)}
            </p>
          </div>
          <div
            role="timer"
            aria-label="Tempo decorrido"
            className="font-mono text-5xl font-semibold tabular-nums tracking-tight"
          >
            {formatDuration(elapsed)}
          </div>
        </header>

        <div className="flex flex-col gap-2">
          <Progress value={Math.round(progress * 100)} aria-label="Tempo até valer ponto" />
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {elapsed < MIN_SECONDS ? (
              `Faltam ${formatDuration(MIN_SECONDS - elapsed)} para a sessão valer ponto.`
            ) : (
              <>
                <CircleCheck aria-hidden className="size-3.5 text-primary" /> Tempo mínimo atingido.
              </>
            )}
          </p>
        </div>

        {showMaterial && session.last_to_review && (
          <aside
            aria-label="Último preciso revisar"
            className="rounded-lg border-l-2 border-primary bg-muted px-4 py-3 text-sm"
          >
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <RotateCcw aria-hidden className="size-3.5" /> Da última vez você anotou para revisar:
            </p>
            <p className="mt-1 whitespace-pre-wrap [overflow-wrap:anywhere]">
              {session.last_to_review}
            </p>
          </aside>
        )}

        {hasTest && (
          <div className="flex flex-col gap-3">
            <RecallSteps current={step} />
            <RecallTest
              questions={session.questions}
              storageKey={recallKey}
              onChange={onTestChange}
            />
          </div>
        )}

        {showMaterial && isMobile && (
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline">
                <NotebookPen aria-hidden /> Abrir caderno
              </Button>
            </SheetTrigger>
            <SheetContent side="bottom" className="max-h-[85dvh] overflow-y-auto">
              <SheetHeader>
                <SheetTitle>Caderno</SheetTitle>
                <SheetDescription>{session.content_title}</SheetDescription>
              </SheetHeader>
              <div className="px-4 pb-4">{notebook}</div>
            </SheetContent>
          </Sheet>
        )}

        <form onSubmit={onSubmit} className="flex flex-col gap-5">
          {isReview && (
            <fieldset className="flex flex-col gap-2">
              <legend id="recall-legend" className="mb-2 text-sm font-medium">
                {hasTest
                  ? "Antes de conferir, quanto você lembrava?"
                  : "Antes de revisar, quanto você lembrava?"}{" "}
                <span className="font-normal text-muted-foreground">(ensina a rede neural)</span>
              </legend>
              <div
                role="radiogroup"
                aria-labelledby="recall-legend"
                className="grid grid-cols-2 gap-2 sm:grid-cols-4"
              >
                {Object.entries(RECALL_LABEL).map(([value, label]) => (
                  <label
                    key={value}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                      recall === Number(value) && "border-primary bg-accent text-accent-foreground",
                    )}
                  >
                    <input
                      type="radio"
                      name="recall"
                      value={value}
                      className="sr-only"
                      checked={recall === Number(value)}
                      disabled={!testDone}
                      onChange={() => setRecall(Number(value))}
                    />
                    <span className="font-mono text-xs text-muted-foreground">{value}</span> {label}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {notes.map(([label, value, set], i) => (
            <div key={label} className="flex flex-col gap-2">
              <Label htmlFor={`note-${i}`}>{label}</Label>
              <Textarea
                id={`note-${i}`}
                value={value}
                onChange={(e) => set(e.target.value)}
                rows={2}
              />
            </div>
          ))}
          <p
            aria-live="polite"
            className={cn(
              "font-mono text-xs",
              chars >= MIN_CHARS && allFilled ? "text-primary" : "text-muted-foreground",
            )}
          >
            {chars}/{MIN_CHARS} caracteres (sem espaços)
            {!allFilled && " · preencha os três campos"}
          </p>
          <ErrorState error={finish.error ?? cancel.error} compact />
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <ConfirmDialog
              title="Cancelar a sessão?"
              description="Ela não vai pontuar e o rascunho do teste será descartado."
              confirmLabel="Cancelar sessão"
              destructive
              onConfirm={() =>
                cancel
                  .mutateAsync(undefined)
                  .then(() => clearRecallDraft(recallKey))
                  .catch(() => {})
              }
            >
              <Button type="button" variant="ghost" disabled={cancel.isPending}>
                Cancelar
              </Button>
            </ConfirmDialog>
            <Button
              type="submit"
              size="lg"
              className="sm:ml-auto"
              disabled={finish.isPending || (isReview && recall === null) || !testDone}
            >
              Finalizar sessão
            </Button>
          </div>
        </form>
      </section>

      {showMaterial && !isMobile && <aside aria-label="Caderno da sessão">{notebook}</aside>}
    </div>
  );
}
