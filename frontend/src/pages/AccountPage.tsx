import { Download, LogOut } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { api } from "@/api/client";
import { useAuthCommand, useChangeTimezone, useMe, usePlan } from "@/api/hooks";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PreferencesForm } from "@/features/account/PreferencesForm";
import { ThemeSelect } from "@/features/account/ThemeSelect";
import { cn } from "@/lib/utils";

function Card({
  title,
  description,
  danger,
  children,
}: {
  title: string;
  description?: ReactNode;
  danger?: boolean;
  children: ReactNode;
}) {
  return (
    <section
      className={cn(
        "flex flex-col gap-4 rounded-xl border bg-card p-5",
        danger && "border-destructive/40",
      )}
    >
      <div className="flex flex-col gap-1">
        <h2 className={cn("text-base font-semibold", danger && "text-destructive")}>{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  );
}

/** Conta: aparência, ritmo, fuso, dados (LGPD), exclusão e saída. */
export function AccountPage() {
  const me = useMe();
  const plan = usePlan();
  const logout = useAuthCommand(() => api.logout());
  const changeTz = useChangeTimezone();
  const [timezone, setTimezone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const remove = useAuthCommand(() => api.deleteAccount(password));
  const [exportError, setExportError] = useState<unknown>(null);
  const zones = Intl.supportedValuesOf("timeZone");

  const onTz = (e: FormEvent) => {
    e.preventDefault();
    changeTz.mutate(timezone || (plan.data?.timezone ?? "UTC"));
  };

  const onExport = async () => {
    try {
      const data = await api.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "developer-myself-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <header className="flex flex-wrap items-center gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">Conta</h1>
          <p className="truncate font-mono text-xs text-muted-foreground">{me.data?.email}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="ml-auto"
          onClick={() => logout.mutate(undefined)}
        >
          <LogOut aria-hidden /> Sair
        </Button>
      </header>

      <Card title="Aparência" description="Vale só neste navegador.">
        <ThemeSelect />
      </Card>

      <Card title="Ritmo de estudo" description="A semana é recalculada a partir daqui.">
        {plan.data && <PreferencesForm prefs={plan.data.preferences} />}
      </Card>

      <Card
        title="Fuso horário"
        description={
          <>
            O “dia” da revisão é o seu dia local. Atual:{" "}
            <span className="font-mono text-foreground">{plan.data?.timezone}</span>
          </>
        }
      >
        <form className="flex flex-col gap-2 sm:flex-row" onSubmit={onTz}>
          <select
            aria-label="Fuso horário"
            value={timezone || plan.data?.timezone || ""}
            onChange={(e) => setTimezone(e.target.value)}
            className="h-9 flex-1 rounded-md border border-input bg-transparent px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {zones.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
          <Button type="submit" disabled={changeTz.isPending}>
            Salvar
          </Button>
        </form>
        {changeTz.isSuccess && <p className="text-sm text-primary">Fuso atualizado.</p>}
        <ErrorState error={changeTz.error} compact />
      </Card>

      <Card title="Seus dados (LGPD)" description="Baixe tudo o que o app guarda sobre você.">
        <Button variant="outline" className="self-start" onClick={onExport}>
          <Download aria-hidden /> Exportar meus dados (JSON)
        </Button>
        <ErrorState error={exportError} compact />
      </Card>

      <Card
        title="Excluir conta"
        description="Apaga a conta, a trilha, os cadernos e todo o histórico."
        danger
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setConfirmDelete(true);
          }}
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="delete-password">Confirme sua senha</Label>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button
            type="submit"
            variant="destructive"
            className="self-start"
            disabled={remove.isPending}
          >
            Excluir definitivamente
          </Button>
          <ErrorState error={remove.error} compact />
        </form>
        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title="Excluir a conta, a trilha e todo o histórico?"
          description="Não há volta. Exporte seus dados antes, se quiser guardá-los."
          confirmLabel="Excluir"
          destructive
          onConfirm={() => remove.mutate(undefined)}
        />
      </Card>
    </div>
  );
}
