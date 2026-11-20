import { useState } from "react";
import type { Preferences } from "@/api/types";
import { Button } from "@/components/ui/button";
import { PreferencesForm } from "@/features/account/PreferencesForm";
import { AddContentForm } from "@/features/trail/AddContentDialog";
import { cn } from "@/lib/utils";

interface Props {
  prefs: Preferences;
  /** O 1º conteúdo entrou: a trilha deixa de estar vazia, mas o guia continua até o fim. */
  onStarted: () => void;
  onDone: () => void;
}

/** Primeira vez: 1) primeiro conteúdo; 2) quanto tempo por dia. Pode ser pulado. */
export function OnboardingGuide({ prefs, onStarted, onDone }: Props) {
  const [step, setStep] = useState<1 | 2>(1);
  return (
    <section
      aria-labelledby="h-onboarding"
      className="flex flex-col gap-5 rounded-2xl border border-primary/40 bg-card p-5 sm:p-6"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs font-semibold uppercase tracking-wider text-primary">
          › primeiros passos · {step}/2
        </p>
        <Button variant="ghost" size="sm" onClick={onDone}>
          Pular
        </Button>
      </div>
      <ol aria-hidden className="grid grid-cols-2 gap-2">
        {[1, 2].map((n) => (
          <li key={n} className={cn("h-1 rounded-full", n <= step ? "bg-primary" : "bg-muted")} />
        ))}
      </ol>
      {step === 1 ? (
        <>
          <div className="flex flex-col gap-1">
            <h2 id="h-onboarding" className="text-xl font-semibold tracking-tight">
              Adicione seu primeiro conteúdo
            </h2>
            <p className="text-sm text-muted-foreground">
              Um livro, curso, artigo ou vídeo que você quer dominar. Ele vira uma trilha de 30
              dias.
            </p>
          </div>
          <AddContentForm
            submitLabel="Continuar"
            onAdded={() => {
              onStarted();
              setStep(2);
            }}
          />
        </>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <h2 id="h-onboarding" className="text-xl font-semibold tracking-tight">
              Quanto tempo por dia?
            </h2>
            <p className="text-sm text-muted-foreground">
              Dá para mudar depois na Conta. Revisões vêm sempre antes do estudo novo.
            </p>
          </div>
          <PreferencesForm prefs={prefs} submitLabel="Começar" onSaved={onDone} />
        </>
      )}
    </section>
  );
}
