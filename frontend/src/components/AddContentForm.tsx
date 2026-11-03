import { type FormEvent, useState } from "react";
import { useAddContent } from "../api/hooks";
import { KIND_LABEL } from "../api/labels";
import type { ContentKind } from "../api/types";
import { ErrorText } from "./ErrorText";

const KINDS = Object.keys(KIND_LABEL) as ContentKind[];

export function AddContentForm() {
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<ContentKind>("BOOK");
  const add = useAddContent();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate({ title, kind }, { onSuccess: () => setTitle("") });
  };

  return (
    <form className="card row wrap" onSubmit={onSubmit} aria-label="Adicionar conteúdo">
      <label className="grow">
        Novo conteúdo
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex.: Clean Code, curso de Docker…"
          maxLength={200}
          required
        />
      </label>
      <label>
        Tipo
        <select value={kind} onChange={(e) => setKind(e.target.value as ContentKind)}>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {KIND_LABEL[k]}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className="primary" disabled={add.isPending}>
        Adicionar
      </button>
      <ErrorText error={add.error} />
    </form>
  );
}
