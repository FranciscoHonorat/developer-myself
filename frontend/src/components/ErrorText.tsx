import { ApiError } from "../api/client";

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : "Falha de conexão.";
  return (
    <p role="alert" className="error">
      {message}
    </p>
  );
}
