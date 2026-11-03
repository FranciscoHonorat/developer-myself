import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import { useAuthCommand, useChangeTimezone, usePlan } from "../api/hooks";
import { ErrorText } from "./ErrorText";

export function SettingsView() {
  const plan = usePlan();
  const changeTz = useChangeTimezone();
  const [timezone, setTimezone] = useState("");
  const [password, setPassword] = useState("");
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
    <div className="stack narrow">
      <form className="card stack" onSubmit={onTz}>
        <h2>Fuso horário</h2>
        <p className="muted small">
          O “dia” da revisão é o seu dia local. Atual: <strong>{plan.data?.timezone}</strong>
        </p>
        <select
          value={timezone || plan.data?.timezone || ""}
          onChange={(e) => setTimezone(e.target.value)}
          aria-label="Fuso horário"
        >
          {zones.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
        <button type="submit" className="primary" disabled={changeTz.isPending}>
          Salvar
        </button>
        {changeTz.isSuccess && <p className="hint ok-text">Fuso atualizado.</p>}
        <ErrorText error={changeTz.error} />
      </form>

      <section className="card stack">
        <h2>Seus dados (LGPD)</h2>
        <button type="button" className="ghost" onClick={onExport}>
          ⬇ Exportar meus dados (JSON)
        </button>
        <ErrorText error={exportError} />
      </section>

      <form
        className="card stack danger"
        onSubmit={(e) => {
          e.preventDefault();
          if (window.confirm("Excluir a conta, a trilha e todo o histórico? Não há volta."))
            remove.mutate(undefined);
        }}
      >
        <h2>Excluir conta</h2>
        <label>
          Confirme sua senha
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <button type="submit" className="danger-btn" disabled={remove.isPending}>
          Excluir definitivamente
        </button>
        <ErrorText error={remove.error} />
      </form>
    </div>
  );
}
