import { Trash2 } from "lucide-react";
import { useState } from "react";
import {
  useAdminAccounts,
  useAdminDeleteAccount,
  useAdminRegistration,
  useSetRegistration,
} from "@/api/hooks";
import type { AdminAccount } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
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
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const date = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString("pt-BR") : "—");

/** Área de admin: abrir/fechar o cadastro e gerenciar contas (só contagens, nunca notas). */
export function AdminPage() {
  const accounts = useAdminAccounts();
  const items = accounts.data?.pages.flatMap((p) => p.items);

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
      <RegistrationToggle />

      <section aria-labelledby="h-accounts" className="flex flex-col gap-3">
        <h2 id="h-accounts" className="text-lg font-semibold">
          Contas
        </h2>
        {accounts.isPending && <Skeleton className="h-40 w-full" />}
        <ErrorState error={accounts.error} compact />
        {items && (
          <div className="overflow-x-auto rounded-xl border bg-card">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr className="border-b">
                  <th className="px-4 py-2 font-medium">Username</th>
                  <th className="px-4 py-2 font-medium">E-mail</th>
                  <th className="px-4 py-2 font-medium">Cadastro</th>
                  <th className="px-4 py-2 font-medium">Última sessão</th>
                  <th className="px-4 py-2 text-right font-medium">Conteúdos</th>
                  <th className="px-4 py-2 text-right font-medium">Sessões</th>
                  <th className="px-4 py-2">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <tr key={a.id} className="border-b last:border-0">
                    <td className="px-4 py-2 font-mono text-xs">{a.username ?? "—"}</td>
                    <td className="max-w-56 truncate px-4 py-2 font-medium">{a.email}</td>
                    <td className="px-4 py-2 font-mono text-xs">{date(a.created_at)}</td>
                    <td className="px-4 py-2 font-mono text-xs">{date(a.last_activity_at)}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums">{a.contents}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums">{a.sessions}</td>
                    <td className="px-4 py-2 text-right">
                      <DeleteAccount account={a} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {accounts.hasNextPage && (
          <Button
            variant="outline"
            className="self-center"
            onClick={() => void accounts.fetchNextPage()}
            disabled={accounts.isFetchingNextPage}
          >
            {accounts.isFetchingNextPage ? "Carregando…" : "Carregar mais"}
          </Button>
        )}
      </section>
    </div>
  );
}

function RegistrationToggle() {
  const registration = useAdminRegistration();
  const setRegistration = useSetRegistration();
  const open = registration.data?.open;

  return (
    <section className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <span id="lbl-registration" className="font-medium">
            Cadastro aberto
          </span>
          <span className="text-xs text-muted-foreground">
            Fechado, ninguém cria conta nova; o login continua normal.
          </span>
        </div>
        {open !== undefined && (
          <button
            type="button"
            role="switch"
            aria-checked={open}
            aria-labelledby="lbl-registration"
            disabled={setRegistration.isPending}
            onClick={() => setRegistration.mutate(!open)}
            className={cn(
              "relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
              open ? "bg-primary" : "bg-muted",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "inline-block size-5 rounded-full bg-background shadow transition-transform",
                open ? "translate-x-5" : "translate-x-0",
              )}
            />
          </button>
        )}
      </div>
      <ErrorState error={registration.error ?? setRegistration.error} compact />
    </section>
  );
}

function DeleteAccount({ account }: { account: AdminAccount }) {
  const remove = useAdminDeleteAccount();
  const [typed, setTyped] = useState("");
  const [open, setOpen] = useState(false);
  const inputId = `confirm-${account.id}`;

  const onOpenChange = (next: boolean) => {
    setOpen(next);
    setTyped("");
    remove.reset();
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-destructive">
          <Trash2 aria-hidden className="size-4" /> Excluir
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir {account.email}?</AlertDialogTitle>
          <AlertDialogDescription>
            Apaga a conta, a trilha, o histórico e o caderno. Não dá para desfazer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor={inputId}>Digite o e-mail da conta para confirmar</Label>
          <Input
            id={inputId}
            autoComplete="off"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        </div>
        <ErrorState error={remove.error} compact />
        <AlertDialogFooter>
          <AlertDialogCancel>Voltar</AlertDialogCancel>
          <AlertDialogAction
            className={buttonVariants({ variant: "destructive" })}
            disabled={typed.trim().toLowerCase() !== account.email || remove.isPending}
            onClick={(e) => {
              // Só fecha quando der certo: se falhar, o erro aparece aqui dentro.
              e.preventDefault();
              remove.mutate(account.id, { onSuccess: () => setOpen(false) });
            }}
          >
            Excluir conta
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
