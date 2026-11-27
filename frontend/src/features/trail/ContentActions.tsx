import {
  CalendarDays,
  CircleCheckBig,
  Compass,
  Ellipsis,
  NotebookPen,
  Pencil,
  Target,
  Trash2,
} from "lucide-react";
import { Link } from "react-router";
import type { Content } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Props {
  content: Content;
  notebookLocked: boolean;
  canFinish: boolean;
  atMaxLevel: boolean;
  canRemove: boolean;
  onRename: () => void;
  onEditPurpose: () => void;
  onSchedule: () => void;
  onChallenges: () => void;
  onFinish: () => void;
  onRemove: () => void;
}

/** Ações secundárias do conteúdo, no menu "⋯" do card. */
export function ContentActions(p: Props) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Mais ações para ${p.content.title}`}>
          <Ellipsis aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuItem onSelect={p.onRename}>
          <Pencil aria-hidden /> Renomear
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={p.onEditPurpose}>
          <Compass aria-hidden /> Editar propósito
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={p.onSchedule}>
          <CalendarDays aria-hidden /> Cronograma
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={p.onChallenges}>
          <Target aria-hidden /> Desafios
        </DropdownMenuItem>
        {!p.notebookLocked && (
          <DropdownMenuItem asChild>
            <Link to={`/caderno/${p.content.id}`}>
              <NotebookPen aria-hidden /> Caderno
            </Link>
          </DropdownMenuItem>
        )}
        {(p.canFinish || p.canRemove) && <DropdownMenuSeparator />}
        {p.canFinish && (
          <DropdownMenuItem disabled={!p.atMaxLevel} onSelect={p.onFinish}>
            <CircleCheckBig aria-hidden /> Concluir
          </DropdownMenuItem>
        )}
        {p.canRemove && (
          <DropdownMenuItem variant="destructive" onSelect={p.onRemove}>
            <Trash2 aria-hidden /> Remover
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
