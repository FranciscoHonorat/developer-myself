import { type FormEvent, useState } from "react";
import { useChangePreferences } from "@/api/hooks";
import type { Preferences } from "@/api/types";
import { hours, WEEKDAY_SHORT } from "@/api/weekLabels";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// De 3h a 8h (o servidor aceita até 480 min); de meia em meia hora até 6h.
const OPTIONS = [180, 210, 240, 270, 300, 330, 360, 420, 480];

const chip =
  "flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-accent has-[:checked]:text-accent-foreground has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring";

const PARALLEL_OPTIONS: [number, string][] = [
  [1, "1 · foco único"],
  [2, "2 · equilibrado"],
  [3, "3 · paralelo"],
];

/** Ritmo: minutos por dia, dias de folga e (opcional) conteúdos em paralelo. */
export function PreferencesForm({
  prefs,
  maxInProgress,
  onSaved,
  submitLabel = "Salvar ritmo",
}: {
  prefs: Preferences;
  maxInProgress?: number;
  onSaved?: () => void;
  submitLabel?: string;
}) {
  const [minutes, setMinutes] = useState(prefs.minutes_per_day);
  const [rest, setRest] = useState<number[]>(prefs.rest_days);
  const [slots, setSlots] = useState<number | undefined>(maxInProgress);
  const change = useChangePreferences();
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    change
      .mutateAsync({
        minutes,
        restDays: rest,
        ...(slots !== undefined ? { maxInProgress: slots } : {}),
      })
      .then(() => onSaved?.())
      .catch(() => {}); // o erro aparece via change.error
  };
  const toggle = (d: number) =>
    setRest((r) => (r.includes(d) ? r.filter((x) => x !== d) : [...r, d].sort()));

  return (
    <form className="flex flex-col gap-5" onSubmit={onSubmit} aria-label="Preferências de estudo">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Tempo de estudo por dia</legend>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {OPTIONS.map((m) => (
            <label key={m} className={chip}>
              <input
                type="radio"
                name="minutes"
                className="sr-only"
                checked={minutes === m}
                onChange={() => setMinutes(m)}
              />
              <span className="font-mono">{hours(m)}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Dias de folga</legend>
        <div className="grid grid-cols-7 gap-1.5">
          {WEEKDAY_SHORT.map((label, d) => (
            <label key={label} className={cn(chip, "px-1")}>
              <input
                type="checkbox"
                className="sr-only"
                checked={rest.includes(d)}
                onChange={() => toggle(d)}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      {slots !== undefined && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">Conteúdos em paralelo</legend>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {PARALLEL_OPTIONS.map(([value, label]) => (
              <label key={value} className={chip}>
                <input
                  type="radio"
                  name="max_in_progress"
                  className="sr-only"
                  checked={slots === value}
                  onChange={() => setSlots(value)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Você escolhe quantas matérias estudar ao mesmo tempo (hábitos diários ficam fora das
            vagas).
          </p>
        </fieldset>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={change.isPending}>
          {submitLabel}
        </Button>
        {change.isSuccess && <span className="text-sm text-primary">Semana recalculada.</span>}
      </div>
      <ErrorState error={change.error} compact />
    </form>
  );
}
