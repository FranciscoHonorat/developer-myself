import { useState } from "react";
import { useCompetencies } from "../api/hooks";
import type { Competency, CompetencySheet, CompetencyStatus } from "../api/types";
import { ErrorText } from "./ErrorText";

const STATUS: Record<CompetencyStatus, { icon: string; label: (c: Competency) => string }> = {
  "em dia": { icon: "✅", label: () => "em dia" },
  "enferruja em breve": {
    icon: "⏳",
    label: (c) => `enferruja em ${c.rust_in_days} dia${c.rust_in_days === 1 ? "" : "s"}`,
  },
  enferrujando: {
    icon: "⚠️",
    label: (c) => `enferrujando: −${c.rust_lost.toFixed(1)} (revise ou resolva um desafio)`,
  },
  "sem progresso": { icon: "⬜", label: () => "ainda não iniciada" },
};

export function CompetenciesView() {
  const sheet = useCompetencies();
  if (sheet.isPending) return <p className="muted">Carregando competências…</p>;
  if (sheet.isError) return <ErrorText error={sheet.error} />;
  const s = sheet.data;
  if (s.competencies.length === 0)
    return <p className="muted">Adicione conteúdos à trilha para ver suas competências.</p>;

  const ranked = [...s.competencies].sort((a, b) => b.score - a.score || b.peak - a.peak);
  const rusting = s.competencies.filter((c) => c.status === "enferrujando").length;
  const prevLevelXp = 50 * (s.level - 1) ** 2;
  const levelPct = ((s.xp - prevLevelXp) / (s.next_level_xp - prevLevelXp)) * 100;

  return (
    <div className="stack viz-root">
      <section className="stats" aria-label="Resumo">
        <div className="card stat">
          <div className="hero-figure">Nível {s.level}</div>
          <meter
            className="sr-only"
            aria-label="XP até o próximo nível"
            min={prevLevelXp}
            max={s.next_level_xp}
            value={s.xp}
          />
          <div className="meter-track" aria-hidden="true">
            <div className="meter-fill" style={{ width: `${levelPct}%` }} />
          </div>
          <div className="small muted">
            {s.xp} XP · próximo nível em {s.next_level_xp} XP
          </div>
        </div>
        <div className="card stat">
          <div className="stat-value">{s.total_points}</div>
          <div className="small muted">pontos conquistados</div>
        </div>
        <div className="card stat">
          <div className="stat-value">{rusting}</div>
          <div className="small muted">
            {rusting === 1 ? "competência enferrujando" : "competências enferrujando"}
          </div>
        </div>
      </section>

      <EffortBar sheet={s} />

      <section className="card" aria-labelledby="h-skills">
        <h2 id="h-skills">Competências</h2>
        <p className="small muted">
          Barra = nível atual (0 a 100). Trecho laranja = perdido para a ferrugem. Traço vertical =
          meta do mapa para o perfil DevSecOps. Faixas: Aprendiz · Praticante (25) · Proficiente
          (50) · Especialista (75).
        </p>
        <ul className="skills">
          {ranked.map((c) => (
            <SkillRow key={c.key} c={c} />
          ))}
        </ul>
        <p className="small muted">
          Ferrugem: sem revisar nem resolver desafios de um conteúdo por mais de{" "}
          {s.rules.grace_days} dias, a contribuição dele cai {s.rules.decay_per_day * 100}% ao dia,
          até {s.rules.floor * 100}%. Seus pontos nunca diminuem; uma revisão tira a ferrugem na
          hora.
        </p>
      </section>
    </div>
  );
}

function SkillRow({ c }: { c: Competency }) {
  const [open, setOpen] = useState(false);
  const status = STATUS[c.status];
  return (
    <li className="skill">
      <div className="row between wrap">
        <strong>{c.name}</strong>
        <span className="small">
          <span className="pill level">{c.tier}</span> {c.score.toFixed(0)}
          {c.target_score !== null && <span className="muted"> / meta {c.target_score}</span>}
        </span>
      </div>
      <meter
        className="sr-only"
        aria-label={`${c.name}: ${c.score.toFixed(0)} de 100${c.target ? `, meta ${c.target}` : ""}`}
        min={0}
        max={100}
        value={c.score}
      />
      <div
        className="skill-bar"
        aria-hidden="true"
        title={`${c.title} · ${c.score.toFixed(1)} (pico ${c.peak.toFixed(1)}) · ${c.points} pts`}
      >
        <div className="skill-fill" style={{ width: `${c.score}%` }} />
        {c.rust_lost > 0 && (
          <div
            className="skill-rust"
            style={{
              left: `calc(${c.score}% + 2px)`,
              width: `max(0px, calc(${c.rust_lost}% - 2px))`,
            }}
          />
        )}
        {c.target_score !== null && (
          <div className="skill-target" style={{ left: `${c.target_score}%` }} />
        )}
      </div>
      <div className="row between wrap small">
        <span className="muted">
          {status.icon} {status.label(c)}
        </span>
        <button type="button" className="link small" onClick={() => setOpen((v) => !v)}>
          {open
            ? "Ocultar conteúdos"
            : `Ver ${c.contents.length} conteúdo${c.contents.length === 1 ? "" : "s"}`}
        </button>
      </div>
      {open && (
        <table className="contrib">
          <caption className="sr-only">Conteúdos que contam para {c.name}</caption>
          <thead>
            <tr>
              <th scope="col">Conteúdo</th>
              <th scope="col">Progresso</th>
              <th scope="col">Conservação</th>
              <th scope="col">Ferrugem</th>
            </tr>
          </thead>
          <tbody>
            {c.contents.map((x) => (
              <tr key={x.title}>
                <td>{x.title}</td>
                <td className="num">{Math.round(x.progress * 100)}%</td>
                <td className="num">{Math.round(x.freshness * 100)}%</td>
                <td>
                  {x.rust_in_days === null
                    ? "—"
                    : x.rust_in_days === 0
                      ? "enferrujando"
                      : `em ${x.rust_in_days} d`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </li>
  );
}

/** Para onde foi o esforço: barras ranqueadas por área (8 áreas: uma cor só, o número ao lado). */
function EffortBar({ sheet }: { sheet: CompetencySheet }) {
  const total = sheet.total_points;
  const ranked = [...sheet.effort].sort((a, b) => b.points - a.points);
  const max = Math.max(...ranked.map((e) => e.points), 1);
  return (
    <section className="card" aria-labelledby="h-effort">
      <h2 id="h-effort">Para onde foi seu esforço</h2>
      {total === 0 ? (
        <p className="small muted">Nenhum ponto ainda: a primeira sessão pontuada aparece aqui.</p>
      ) : (
        <ul className="effort-bars">
          {ranked.map((e) => (
            <li key={e.area}>
              <span>{e.area}</span>
              <div className="effort-track" aria-hidden="true">
                <div className="effort-fill" style={{ width: `${(e.points / max) * 100}%` }} />
              </div>
              <span className="num small">
                {e.points} pts · {Math.round((e.points / total) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
