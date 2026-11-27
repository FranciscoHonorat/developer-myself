import { Brain, Repeat, Timer } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, type Location, Navigate, useLocation } from "react-router";
import { ApiError, api } from "@/api/client";
import { useAuthCommand, useMe, useRegistrationStatus } from "@/api/hooks";
import { Brand } from "@/app/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Volta para a rota que pediu login (guardada pelo RequireAuth), ou para o Hoje. */
function destination(state: unknown): string {
  const from = (state as { from?: Location } | null)?.from;
  if (!from?.pathname.startsWith("/") || from.pathname.startsWith("//")) return "/hoje";
  return `${from.pathname}${from.search}`;
}

const METHOD = [
  {
    icon: Repeat,
    title: "Repetição espaçada",
    text: "Revise antes de estudar: o que você revisa, fica.",
  },
  {
    icon: Timer,
    title: "Sessões de 25 min",
    text: "Foco curto, anotações honestas, um ponto por sessão.",
  },
  {
    icon: Brain,
    title: "IA que aprende com você",
    text: "Ela estima o que você está perto de esquecer.",
  },
];

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const location = useLocation();
  const me = useMe();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [hint, setHint] = useState<string | null>(null);
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const isLogin = mode === "login";
  const registration = useRegistrationStatus(!isLogin);

  const submit = useAuthCommand(() =>
    isLogin ? api.login(username, password) : api.register(username, email, password, timezone),
  );

  if (me.isSuccess) return <Navigate to={destination(location.state)} replace />;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Gerenciador de senha antigo preenche o e-mail salvo: explicar em vez de "senha inválida".
    if (isLogin && username.includes("@")) {
      setHint("Use o username (a parte do e-mail antes do @), não o e-mail.");
      return;
    }
    setHint(null);
    submit.mutate(undefined);
  };

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <main className="flex flex-col justify-center px-4 py-10 sm:px-10">
        <div className="mx-auto flex w-full max-w-sm flex-col gap-8">
          <Brand className="text-base" />
          <p className="text-sm text-muted-foreground lg:hidden">
            Estude com foco, revise todo dia e prove o que aprendeu com desafios.
          </p>
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              {isLogin ? "Entrar" : "Criar sua conta"}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isLogin ? "Bom te ver de novo." : "Leva menos de um minuto."}
            </p>
          </div>
          {isLogin && (
            <p className="rounded-lg border px-3 py-2 text-sm text-muted-foreground">
              Agora o login é por username: o seu é a parte do e-mail antes do @ (você pode trocar
              na página Conta).
            </p>
          )}
          {!isLogin && registration.data?.open === false && (
            <p
              role="status"
              className="rounded-lg border border-warning/50 px-3 py-2 text-sm text-warning"
            >
              Novos cadastros estão fechados no momento.
            </p>
          )}
          <form className="flex flex-col gap-4" onSubmit={onSubmit}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                required
                minLength={3}
                maxLength={30}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              {!isLogin && (
                <p className="text-xs text-muted-foreground">
                  De 3 a 30 caracteres: letras minúsculas, números, ponto, _ ou -.
                </p>
              )}
            </div>
            {!isLogin && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
                minLength={isLogin ? undefined : 10}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {!isLogin && (
                <p className="text-xs text-muted-foreground">
                  Mínimo de 10 caracteres. Fuso detectado:{" "}
                  <span className="font-mono">{timezone}</span>
                </p>
              )}
            </div>
            {(hint || submit.error) && (
              <p
                role="alert"
                className="rounded-lg border border-destructive/40 px-3 py-2 text-sm text-destructive"
              >
                {hint ??
                  (submit.error instanceof ApiError ? submit.error.message : "Falha de conexão.")}
              </p>
            )}
            <Button type="submit" size="lg" disabled={submit.isPending}>
              {isLogin ? "Entrar" : "Criar conta"}
            </Button>
          </form>
          <Link
            to={isLogin ? "/cadastro" : "/entrar"}
            state={location.state}
            onClick={() => submit.reset()}
            className="text-center text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            {isLogin ? "Não tem conta? Cadastre-se" : "Já tem conta? Entrar"}
          </Link>
        </div>
      </main>
      <aside
        aria-label="Como funciona"
        className="relative hidden overflow-hidden border-l bg-card lg:flex lg:flex-col lg:justify-center lg:px-14"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute -top-32 -right-32 size-96 rounded-full bg-primary/10 blur-3xl"
        />
        <p className="font-mono text-sm text-muted-foreground">$ developer-myself --método</p>
        <h2 className="mt-3 max-w-md text-3xl font-semibold tracking-tight">
          Estude com foco, revise todo dia e prove o que aprendeu.
        </h2>
        <ul className="mt-10 flex max-w-md flex-col gap-6">
          {METHOD.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex gap-4">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-primary/40 bg-accent">
                <Icon aria-hidden className="size-5 text-primary" />
              </span>
              <span>
                <strong className="block font-medium">{title}</strong>
                <span className="text-sm text-muted-foreground">{text}</span>
              </span>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
