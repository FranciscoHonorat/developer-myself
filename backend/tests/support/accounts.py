"""Username dos testes HTTP: derivado do e-mail, como a migração faz com contas antigas."""

import re


def handle(email: str) -> str:
    local = re.sub(r"[^a-z0-9._-]", "_", email.split("@", 1)[0].strip().lower())[:30]
    return local if len(local) >= 3 else f"{local}-1"
