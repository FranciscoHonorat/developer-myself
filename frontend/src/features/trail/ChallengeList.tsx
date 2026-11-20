import { Circle, CircleCheck, Plus } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useAddChallenge, useSolveChallenge } from "@/api/hooks";
import { LEVEL_LABEL } from "@/api/labels";
import type { Challenge, Content, MasteryLevel } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
    <div className="flex flex-col gap-3 rounded-lg border bg-background/40 p-3">
      {content.challenges.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Nenhum desafio ainda. Crie desafios práticos (ex.: “refatorar um módulo aplicando o
          capítulo 3”). Cada nível exige 3 desafios resolvidos.
        </p>
      )}
      {content.challenges.length > 0 && (
        <ul className="flex flex-col gap-2">
          {content.challenges.map((c) => (
            <ChallengeItem
              key={c.id}
              contentId={content.id}
              challenge={c}
              locked={content.status === "LOCKED"}
            />
          ))}
        </ul>
      )}
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={onAdd}
        aria-label={`Novo desafio em ${content.title}`}
      >
        <Input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Descreva um desafio prático"
          aria-label="Descreva um desafio prático"
          maxLength={2000}
          required
        />
        <select
          aria-label="Nível do desafio"
          value={level}
          onChange={(e) => setLevel(e.target.value as MasteryLevel)}
          className="h-9 rounded-md border border-input bg-transparent px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="INTERMEDIATE">{LEVEL_LABEL.INTERMEDIATE}</option>
          <option value="ADVANCED">{LEVEL_LABEL.ADVANCED}</option>
        </select>
        <Button type="submit" variant="outline" disabled={add.isPending}>
          <Plus aria-hidden /> Desafio
        </Button>
      </form>
      <ErrorState error={add.error} compact />
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
    <li className="flex flex-col gap-2 text-sm">
      <div className="flex items-start gap-2">
        {challenge.solved ? (
          <CircleCheck aria-label="resolvido" className="mt-0.5 size-4 shrink-0 text-primary" />
        ) : (
          <Circle aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="flex-1">
          {challenge.description}{" "}
          <Badge variant="outline" className="ml-1">
            {LEVEL_LABEL[challenge.target_level]}
          </Badge>
        </span>
        {!challenge.solved && !locked && (
          <Button variant="ghost" size="sm" onClick={() => setOpen((v) => !v)}>
            Resolver
          </Button>
        )}
      </div>
      {challenge.solved && challenge.evidence && (
        <p className="pl-6 text-xs text-muted-foreground [overflow-wrap:anywhere]">
          Evidência: {challenge.evidence}
        </p>
      )}
      {open && !challenge.solved && (
        <form className="flex flex-col gap-2 pl-6 sm:flex-row" onSubmit={onSolve}>
          <Input
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            placeholder="Link do código/solução ou explicação"
            aria-label="Evidência"
            required
          />
          <Button type="submit" disabled={solve.isPending}>
            Confirmar
          </Button>
          <ErrorState error={solve.error} compact />
        </form>
      )}
    </li>
  );
}
