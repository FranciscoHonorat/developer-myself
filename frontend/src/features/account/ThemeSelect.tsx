import { Monitor, Moon, Sun } from "lucide-react";
import { useState } from "react";
import { applyTheme, readTheme, saveTheme, type ThemeChoice } from "@/lib/theme";

const OPTIONS: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
  { value: "dark", label: "Escuro", icon: Moon },
  { value: "light", label: "Claro", icon: Sun },
  { value: "system", label: "Sistema", icon: Monitor },
];

/** Escuro (padrão), claro ou o do sistema; vale só neste navegador. */
export function ThemeSelect() {
  const [theme, setTheme] = useState<ThemeChoice>(readTheme);
  const choose = (t: ThemeChoice) => {
    setTheme(t);
    saveTheme(t);
    applyTheme(t);
  };
  return (
    <div role="radiogroup" aria-label="Tema" className="grid grid-cols-3 gap-2">
      {OPTIONS.map(({ value, label, icon: Icon }) => (
        <label
          key={value}
          className="flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-accent has-[:checked]:text-accent-foreground has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring"
        >
          <input
            type="radio"
            name="theme"
            className="sr-only"
            checked={theme === value}
            onChange={() => choose(value)}
          />
          <Icon aria-hidden className="size-5" />
          {label}
        </label>
      ))}
    </div>
  );
}
