import { type LucideIcon, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { GRADE_LABEL } from "@/api/labels";
import type { RecallAnswer, RecallGrade, RecallQuestion } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface Draft {
  step: "answer" | "check";
  answers: Record<string, string>;
  grades: Record<string, RecallGrade>;
  useful: Record<string, boolean | null>;
}

const EMPTY: Draft = { step: "answer", answers: {}, grades: {}, useful: {} };
const GRADES = Object.keys(GRADE_LABEL) as RecallGrade[];
const GRADE_STYLE: Record<RecallGrade, string> = {
  MISSED: "border-destructive bg-destructive/10 text-destructive",
  PARTIAL: "border-warning bg-warning-bg text-warning",
  RECALLED: "border-primary bg-accent text-accent-foreground",
};

function load(key: string): Draft {
  try {
    const raw = localStorage.getItem(key);
    return raw ? { ...EMPTY, ...(JSON.parse(raw) as Partial<Draft>) } : EMPTY;
  } catch {
    return EMPTY;
  }
}

function save(key: string, draft: Draft) {
  try {
    localStorage.setItem(key, JSON.stringify(draft));
  } catch {
    // sem storage (aba privada, bloqueio): o teste continua, só não sobrevive a recarregar
  }
}

export function clearRecallDraft(key: string) {
  try {
    localStorage.removeItem(key);
  } catch {
    // idem
  }
}

/** Limpa rascunhos locais de testes/aquecimentos ao sair ou trocar de conta. */
export function clearAllRecallDrafts() {
  try {
    const toRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && (k.startsWith("recall:") || k.startsWith("warmup:"))) toRemove.push(k);
    }
    for (const k of toRemove) localStorage.removeItem(k);
  } catch {
    // sem storage
  }
}

interface Props {
  questions: RecallQuestion[];
  storageKey: string;
  /** `answers` só vem preenchido quando as 3 perguntas têm correção. */
  onChange: (answers: RecallAnswer[] | null, checking: boolean) => void;
}

/** Teste de memória: responder sem consultar, conferir, corrigir. */
export function RecallTest({ questions, storageKey, onChange }: Props) {
  const [draft, setDraft] = useState<Draft>(() => load(storageKey));
  const checking = draft.step === "check";

  const update = (patch: Partial<Draft>) =>
    setDraft((d) => {
      const next = { ...d, ...patch };
      save(storageKey, next);
      return next;
    });

  useEffect(() => {
    const graded: RecallAnswer[] = [];
    for (const q of questions) {
      const grade = draft.grades[q.id];
      if (grade === undefined) break;
      graded.push({
        question_id: q.id,
        answer: draft.answers[q.id] ?? "",
        grade,
        useful: draft.useful[q.id] ?? null,
      });
    }
    onChange(graded.length === questions.length ? graded : null, draft.step === "check");
  }, [draft, questions, onChange]);

  return (
    <fieldset className="flex flex-col gap-4 rounded-xl border bg-background/40 p-4">
      <legend className="px-1 text-sm font-medium">
        Teste de memória{" "}
        <span className="font-normal text-muted-foreground">
          {checking
            ? "— confira com o caderno e corrija cada resposta"
            : "— responda sem consultar; vale responder “não lembro”"}
        </span>
      </legend>
      <ol className="flex flex-col gap-5">
        {questions.map((q, i) => (
          <li key={q.id} className="flex flex-col gap-2">
            {checking ? (
              <>
                <p className="text-sm font-medium">
                  <span aria-hidden className="mr-2 font-mono text-xs text-muted-foreground">
                    {i + 1}.
                  </span>
                  {q.text}
                </p>
                <p className="whitespace-pre-wrap rounded-md bg-muted px-3 py-2 text-sm [overflow-wrap:anywhere]">
                  {draft.answers[q.id] || <em className="text-muted-foreground">(em branco)</em>}
                </p>
                {q.expected_answer ? (
                  <div className="flex flex-col gap-1 rounded-md border border-dashed px-3 py-2 text-sm">
                    <span className="text-xs font-medium text-muted-foreground">
                      Sua resposta esperada
                    </span>
                    <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">
                      {q.expected_answer}
                    </p>
                  </div>
                ) : null}
                <div className="flex flex-wrap items-center gap-2">
                  <div
                    role="radiogroup"
                    aria-label={`Correção: ${q.text}`}
                    className="flex flex-wrap gap-2"
                  >
                    {GRADES.map((grade) => (
                      <label
                        key={grade}
                        className={cn(
                          "cursor-pointer rounded-full border px-3 py-1 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                          draft.grades[q.id] === grade && GRADE_STYLE[grade],
                        )}
                      >
                        <input
                          type="radio"
                          name={`grade-${q.id}`}
                          value={grade}
                          className="sr-only"
                          checked={draft.grades[q.id] === grade}
                          onChange={() => update({ grades: { ...draft.grades, [q.id]: grade } })}
                        />
                        {GRADE_LABEL[grade]}
                      </label>
                    ))}
                  </div>
                  <span className="ml-auto flex gap-1">
                    <UsefulButton
                      label="Pergunta útil"
                      icon={ThumbsUp}
                      pressed={draft.useful[q.id] === true}
                      onClick={() =>
                        update({
                          useful: {
                            ...draft.useful,
                            [q.id]: draft.useful[q.id] === true ? null : true,
                          },
                        })
                      }
                    />
                    <UsefulButton
                      label="Pergunta ruim"
                      icon={ThumbsDown}
                      pressed={draft.useful[q.id] === false}
                      onClick={() =>
                        update({
                          useful: {
                            ...draft.useful,
                            [q.id]: draft.useful[q.id] === false ? null : false,
                          },
                        })
                      }
                    />
                  </span>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span aria-hidden className="font-mono text-xs text-muted-foreground">
                    {i + 1}.
                  </span>
                  <Label htmlFor={`answer-${q.id}`} className="leading-snug">
                    {q.text}
                  </Label>
                </div>
                <Textarea
                  id={`answer-${q.id}`}
                  rows={3}
                  maxLength={5000}
                  value={draft.answers[q.id] ?? ""}
                  onChange={(e) =>
                    update({ answers: { ...draft.answers, [q.id]: e.target.value } })
                  }
                />
              </>
            )}
          </li>
        ))}
      </ol>
      {!checking && (
        <Button type="button" className="self-start" onClick={() => update({ step: "check" })}>
          Conferir respostas
        </Button>
      )}
    </fieldset>
  );
}

function UsefulButton(props: {
  label: string;
  icon: LucideIcon;
  pressed: boolean;
  onClick: () => void;
}) {
  const Icon = props.icon;
  return (
    <Button
      type="button"
      variant={props.pressed ? "secondary" : "ghost"}
      size="icon"
      aria-label={props.label}
      title={props.label}
      aria-pressed={props.pressed}
      onClick={props.onClick}
      className={cn(props.pressed && "text-primary")}
    >
      <Icon aria-hidden />
    </Button>
  );
}
