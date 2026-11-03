import { useState } from "react";
import { api } from "./api/client";
import { useAuthCommand, useMe } from "./api/hooks";
import { AuthScreen } from "./components/AuthScreen";
import { CompetenciesView } from "./components/CompetenciesView";
import { HistoryView } from "./components/HistoryView";
import { PlanView } from "./components/PlanView";
import { SettingsView } from "./components/SettingsView";
import { WeekView } from "./components/WeekView";

type Tab = "plan" | "week" | "skills" | "history" | "settings";
const TABS: { id: Tab; label: string }[] = [
  { id: "plan", label: "Trilha" },
  { id: "week", label: "Semana" },
  { id: "skills", label: "Competências" },
  { id: "history", label: "Histórico" },
  { id: "settings", label: "Conta" },
];

export function App() {
  const me = useMe();
  const [tab, setTab] = useState<Tab>("plan");
  const logout = useAuthCommand(() => api.logout());

  if (me.isPending) return <p className="center muted">Carregando…</p>;
  if (me.isError) return <AuthScreen />;

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">🧠 Developer Myself</h1>
        <nav aria-label="Seções">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? "tab active" : "tab"}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="user">
          <span className="muted">{me.data.email}</span>
          <button type="button" className="ghost" onClick={() => logout.mutate(undefined)}>
            Sair
          </button>
        </div>
      </header>
      <main>
        {tab === "plan" && <PlanView />}
        {tab === "week" && <WeekView />}
        {tab === "skills" && <CompetenciesView />}
        {tab === "history" && <HistoryView />}
        {tab === "settings" && <SettingsView />}
      </main>
    </div>
  );
}
