import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Anterior · Página X de Y · Próxima. Some quando tudo cabe numa página. */
export function Pagination({
  page,
  totalPages,
  onChange,
  label,
}: {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
  label: string;
}) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label={`Páginas de ${label}`} className="flex items-center justify-center gap-3">
      <Button variant="outline" size="sm" onClick={() => onChange(page - 1)} disabled={page <= 1}>
        <ChevronLeft aria-hidden className="size-4" /> Anterior
      </Button>
      <span aria-live="polite" className="font-mono text-xs tabular-nums text-muted-foreground">
        Página {page} de {totalPages}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
      >
        Próxima <ChevronRight aria-hidden className="size-4" />
      </Button>
    </nav>
  );
}
