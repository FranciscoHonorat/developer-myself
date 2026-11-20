import { type FormEvent, useState } from "react";
import { useChangePreferences } from "@/api/hooks";
import type { Preferences } from "@/api/types";
import { hours, WEEKDAY_SHORT } from "@/api/weekLabels";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const OPTIONS = [180, 210, 240];

const chip =
  "flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-accent has-[:checked]:text-accent-foreground has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring";

/** Ritmo: minutos por dia e dias de folga. A semana é recalculada no servidor. */
export function PreferencesForm({
  prefs,
  onSaved,
  submitLabel = "Salvar ritmo",
}: {
  prefs: Preferences;
  onSaved?: () => void;
  submitLabel?: string;
}) {
  const [minutes, setMinutes] = useState(prefs.minutes_per_day);
  const [rest, setRest] = useState<number[]>(prefs.rest_days);
  const change = useChangePreferences();
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    change
      .mutateAsync({ minutes, restDays: rest })
      .then(() => onSaved?.())
      .catch(() => {}); // o erro aparece via change.error
  };
  const toggle = (d: number) =>
    setRest((r) => (r.includes(d) ? r.filter((x) => x !== d) : [...r, d].sort()));

  return (
    <form className="flex flex-col gap-5" onSubmit={onSubmit} aria-label="Preferências de estudo">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Tempo de estudo por dia</legend>
        <div className="grid grid-cols-3 gap-2">
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
