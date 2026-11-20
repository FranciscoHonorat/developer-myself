import { Plus } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useAddContent } from "@/api/hooks";
import { KIND_LABEL } from "@/api/labels";
import type { ContentKind } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const KINDS = Object.keys(KIND_LABEL) as ContentKind[];

/** Título + tipo. Usado no diálogo da Trilha e, inline, no guia da primeira vez. */
export function AddContentForm({
  onAdded,
  submitLabel = "Adicionar",
}: {
  onAdded?: () => void;
  submitLabel?: string;
}) {
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<ContentKind>("BOOK");
  const add = useAddContent();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    // mutateAsync: o refetch pode desmontar o formulário (ex.: guia da primeira vez) antes da
    // resposta, e o TanStack não chama callbacks de `mutate` de componente desmontado.
    add
      .mutateAsync({ title: title.trim(), kind })
      .then(() => {
        setTitle("");
        onAdded?.();
      })
      .catch(() => {}); // o erro aparece via add.error
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="content-title">Título</Label>
        <Input
          id="content-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex.: Clean Code, curso de Docker…"
          maxLength={200}
          required
          autoFocus
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="content-kind">Tipo</Label>
        <Select value={kind} onValueChange={(v) => setKind(v as ContentKind)}>
          <SelectTrigger id="content-kind" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {KINDS.map((k) => (
              <SelectItem key={k} value={k}>
                {KIND_LABEL[k]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <ErrorState error={add.error} compact />
      <Button type="submit" disabled={add.isPending} className="self-end">
        {submitLabel}
      </Button>
    </form>
  );
}

export function AddContentDialog() {
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden /> Adicionar conteúdo
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Adicionar conteúdo</DialogTitle>
          <DialogDescription>
            Livro, curso, artigo ou vídeo. Entra na fila; o primeiro começa na hora.
          </DialogDescription>
        </DialogHeader>
        <AddContentForm onAdded={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}
