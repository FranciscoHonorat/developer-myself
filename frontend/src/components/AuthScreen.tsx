import { type FormEvent, useState } from "react";
import { ApiError, api } from "../api/client";
import { useAuthCommand } from "../api/hooks";

export function AuthScreen() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const submit = useAuthCommand(() =>
    mode === "login" ? api.login(email, password) : api.register(email, password, timezone),
  );

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit.mutate(undefined);
  };

  return (
    <div className="auth">
      <form className="card auth-card" onSubmit={onSubmit}>
        <h1>🧠 Developer Myself</h1>
        <p className="muted">
          Estude com foco, revise todo dia e prove o que aprendeu com desafios.
        </p>
        <label>
          E-mail
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "register" ? 10 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {mode === "register" && (
          <p className="hint">Mínimo de 10 caracteres. Fuso detectado: {timezone}</p>
        )}
        {submit.error && (
          <p role="alert" className="error">
            {submit.error instanceof ApiError ? submit.error.message : "Falha de conexão."}
          </p>
        )}
        <button type="submit" className="primary" disabled={submit.isPending}>
          {mode === "login" ? "Entrar" : "Criar conta"}
        </button>
        <button
          type="button"
          className="link"
          onClick={() => {
            submit.reset();
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "Não tem conta? Cadastre-se" : "Já tem conta? Entrar"}
        </button>
      </form>
    </div>
  );
}
