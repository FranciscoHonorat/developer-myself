import { type FormEvent, useState } from "react";
import { useAddChallenge, useSolveChallenge } from "../api/hooks";
import { LEVEL_LABEL } from "../api/labels";
import type { Challenge, Content, MasteryLevel } from "../api/types";
import { ErrorText } from "./ErrorText";

export function ChallengeList({ content }: { content: Content }) {
  const [description, setDescription] = useState("");
  const [level, setLevel] = useState<MasteryLevel>(content.next_level?.level ?? "INTERMEDIATE");
  const add = useAddChallenge();

  const onAdd = (e: FormEvent) => {
    e.preventDefault();
    add.mutate(
      { contentId: content.id, description, level },
      { onSuccess: () => setDescription("") },
    );
  };

  return (
    <div className="challenges">
      {content.challenges.length === 0 && (
        <p className="muted small">
          Nenhum desafio ainda. Crie desafios práticos (ex.: “refatorar um módulo aplicando o
          capítulo 3”). Cada nível exige 3 desafios resolvidos.
        </p>
      )}
      <ul>
        {content.challenges.map((c) => (
          <ChallengeItem
            key={c.id}
            contentId={content.id}
            challenge={c}
            locked={content.status === "LOCKED"}
          />
        ))}
      </ul>
      <form className="row wrap" onSubmit={onAdd} aria-label={`Novo desafio em ${content.title}`}>
        <input
          className="grow"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Descreva um desafio prático"
          maxLength={2000}
          required
        />
        <select value={level} onChange={(e) => setLevel(e.target.value as MasteryLevel)}>
          <option value="INTERMEDIATE">{LEVEL_LABEL.INTERMEDIATE}</option>
          <option value="ADVANCED">{LEVEL_LABEL.ADVANCED}</option>
        </select>
        <button type="submit" className="ghost" disabled={add.isPending}>
          + Desafio
        </button>
      </form>
      <ErrorText error={add.error} />
    </div>
  );
}

function ChallengeItem(props: { contentId: string; challenge: Challenge; locked: boolean }) {
  const { contentId, challenge, locked } = props;
  const [evidence, setEvidence] = useState("");
  const [open, setOpen] = useState(false);
  const solve = useSolveChallenge();

  const onSolve = (e: FormEvent) => {
    e.preventDefault();
    solve.mutate({ contentId, challengeId: challenge.id, evidence });
  };

  return (
    <li className={challenge.solved ? "challenge solved" : "challenge"}>
      <div className="row between">
        <span>
          {challenge.solved ? "✅" : "⬜"} {challenge.description}{" "}
          <span className="pill">{LEVEL_LABEL[challenge.target_level]}</span>
        </span>
        {!challenge.solved && !locked && (
          <button type="button" className="link" onClick={() => setOpen((v) => !v)}>
            Resolver
          </button>
        )}
      </div>
      {challenge.solved && challenge.evidence && (
        <p className="small muted evidence">Evidência: {challenge.evidence}</p>
      )}
      {open && !challenge.solved && (
        <form className="row wrap" onSubmit={onSolve}>
          <input
            className="grow"
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            placeholder="Link do código/solução ou explicação"
            aria-label="Evidência"
            required
          />
          <button type="submit" className="primary" disabled={solve.isPending}>
            Confirmar
          </button>
          <ErrorText error={solve.error} />
        </form>
      )}
    </li>
  );
}
