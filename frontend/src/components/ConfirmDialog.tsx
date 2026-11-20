import type { ReactNode } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";

interface Props {
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  /** O botão que abre a confirmação (modo com gatilho). */
  children?: ReactNode;
  /** Modo controlado: para abrir a partir de um item de menu, por exemplo. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/** Confirmação acessível (substitui `window.confirm`). */
export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  cancelLabel = "Voltar",
  destructive = false,
  onConfirm,
  children,
  open,
  onOpenChange,
}: Props) {
  const controlled = open === undefined ? {} : { open, ...(onOpenChange ? { onOpenChange } : {}) };
  return (
    <AlertDialog {...controlled}>
      {children && <AlertDialogTrigger asChild>{children}</AlertDialogTrigger>}
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            className={destructive ? buttonVariants({ variant: "destructive" }) : undefined}
            onClick={onConfirm}
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
