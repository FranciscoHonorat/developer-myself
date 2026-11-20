import { useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { ApiError, api } from "@/api/client";
import { keys, useNotebook } from "@/api/hooks";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const AUTOSAVE_MS = 1000;
const MAX_CHARS = 100_000;
const DRAFT_SEPARATOR = "\n\n— rascunho não salvo —\n";

type Status = "idle" | "dirty" | "saving" | "saved" | "conflict" | "error";

const STATUS_TEXT: Record<Exclude<Status, "conflict" | "error">, string> = {
  idle: "",
  dirty: "Alterações não salvas",
  saving: "Salvando…",
  saved: "Salvo",
};

interface Props {
  contentId: string;
  title: string;
  /** Editor ocupando a altura útil (página do Caderno). */
  tall?: boolean;
}

/**
 * Bloco livre da matéria com autosave: 1 s depois de parar de digitar, no blur, ao esconder
 * a aba e ao desmontar (ex.: "Finalizar sessão"). Um PUT por vez, sempre com a versão mais
 * recente; em 409 (outra aba salvou antes) para de salvar até o usuário recarregar.
 */
export function NotebookEditor({ contentId, title, tall = false }: Props) {
  const qc = useQueryClient();
  const notebook = useNotebook(contentId);
  const [text, setText] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<unknown>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const fieldId = useId();

  // Refs: o salvamento sempre enxerga o texto e a versão mais recentes.
  const textRef = useRef("");
  const savedRef = useRef("");
  const versionRef = useRef(0);
  const inFlight = useRef(false);
  const blocked = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const apply = useCallback((value: string, version: number) => {
    textRef.current = value;
    savedRef.current = value;
    versionRef.current = version;
    blocked.current = false;
    setText(value);
    setStatus("idle");
  }, []);

  // Carrega uma vez e, depois, acompanha versões novas do cache (outra cópia do editor na
  // mesma tela salvou, ou um refetch trouxe algo mais novo) — só quando não há nada pendente.
  useEffect(() => {
    const data = notebook.data;
    if (!data) return;
    if (!loaded) {
      apply(data.text, data.version);
      setLoaded(true);
      return;
    }
    const clean = textRef.current === savedRef.current && !inFlight.current && !blocked.current;
    if (clean && data.version > versionRef.current) apply(data.text, data.version);
  }, [notebook.data, loaded, apply]);

  const flush = useCallback(async (): Promise<void> => {
    clearTimeout(timer.current);
    timer.current = undefined;
    if (blocked.current || inFlight.current || textRef.current === savedRef.current) return;
    inFlight.current = true;
    setStatus("saving");
    const sending = textRef.current;
    try {
      const saved = await api.saveNotebook(contentId, sending, versionRef.current);
      versionRef.current = saved.version;
      savedRef.current = sending;
      setError(null);
      qc.setQueryData(keys.notebook(contentId), saved);
      void qc.invalidateQueries({ queryKey: keys.notebooks });
    } catch (e) {
      inFlight.current = false;
      if (e instanceof ApiError && e.status === 409) {
        blocked.current = true;
        setStatus("conflict");
      } else {
        setError(e);
        setStatus("error");
      }
      return;
    }
    inFlight.current = false;
    if (textRef.current !== savedRef.current) await flush();
    else {
      setSavedAt(new Date());
      setStatus("saved");
    }
  }, [contentId, qc]);

  // Desmontar (ex.: sessão finalizada) e esconder a aba salvam o que estiver pendente.
  const flushRef = useRef(flush);
  flushRef.current = flush;
  useEffect(() => {
    const onHide = () => {
      if (document.visibilityState === "hidden") void flushRef.current();
    };
    // Recarregar/fechar com algo não salvo: o navegador pergunta antes de sair.
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (textRef.current !== savedRef.current || inFlight.current) e.preventDefault();
    };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("beforeunload", onBeforeUnload);
      void flushRef.current();
    };
  }, []);

  const onChange = (value: string) => {
    textRef.current = value;
    setText(value);
    if (blocked.current) return;
    setStatus("dirty");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => void flush(), AUTOSAVE_MS);
  };

  // Traz a versão do servidor sem jogar fora o que não foi salvo: o rascunho vai no fim.
  const reload = async () => {
    const draft = textRef.current;
    const unsaved = draft !== savedRef.current;
    const fresh = await notebook.refetch();
    if (!fresh.data) return;
    apply(fresh.data.text, fresh.data.version);
    if (unsaved && draft !== fresh.data.text) onChange(fresh.data.text + DRAFT_SEPARATOR + draft);
  };

  const statusText =
    status === "saved" && savedAt
      ? `Salvo às ${savedAt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
      : status === "conflict" || status === "error"
        ? ""
        : STATUS_TEXT[status];

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={fieldId}>Caderno de {title}</Label>
      <Textarea
        id={fieldId}
        value={text}
        rows={10}
        maxLength={MAX_CHARS}
        disabled={!loaded}
        readOnly={status === "conflict"}
        placeholder="Escreva conceitos com as suas palavras…"
        className={cn("resize-y leading-relaxed", tall ? "min-h-[60dvh]" : "min-h-56")}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => void flush()}
      />
      <div className="flex items-center justify-between gap-3 text-xs">
        <span
          role="status"
          className={cn(
            "flex items-center gap-1.5",
            status === "saved" ? "text-primary" : "text-muted-foreground",
            (status === "conflict" || status === "error") && "text-warning",
          )}
        >
          {status === "saved" && <Check aria-hidden className="size-3.5" />}
          {status === "conflict" ? (
            <>
              Editado em outro lugar.{" "}
              <Button variant="link" size="sm" className="h-auto p-0" onClick={() => void reload()}>
                Recarregar
              </Button>
            </>
          ) : status === "error" ? (
            "Não foi possível salvar."
          ) : (
            statusText
          )}
        </span>
        <span className="font-mono text-muted-foreground tabular-nums">
          {text.length.toLocaleString("pt-BR")} caracteres
        </span>
      </div>
      <ErrorState error={notebook.error ?? error} compact />
    </div>
  );
}
