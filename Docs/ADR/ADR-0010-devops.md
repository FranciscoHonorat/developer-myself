# ADR-0010: DevOps — containers, CI e observabilidade

**Status:** Proposto. Adia AWS/Kubernetes/Prometheus do [ADR-0001](ADR%20-0001-tech.md).
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

Há um desenvolvedor e um usuário. O objetivo é feedback rápido e um caminho de deploy repetível, sem operar um cluster.

## Decisão

### Ambiente local: `docker compose`

`api` · `worker` (relay do outbox + consumers) · `mongo` (replica set de 1 nó + init) · `rabbitmq:4-management` · `web` (Vite). A API e o worker usam a **mesma imagem** com comandos diferentes, o que garante que rodam o mesmo código.

### Pipeline (GitHub Actions), cada job chamando `make`

```
lint+typecheck ─▶ unit+bdd ─▶ integration (Testcontainers) ─▶ security (gitleaks, pip-audit, npm audit, Trivy) ─▶ build image
```

Os jobs rodam com cache de Poetry e npm, e PRs não fazem merge com o pipeline vermelho.

### Imagem

Multi-stage. O estágio de build roda `poetry sync --only main` e o de runtime usa `python:3.15-slim`, com usuário sem root, `HEALTHCHECK` e **digest fixo**.

### Configuração (12-factor)

Tudo vem do env via `pydantic-settings`. O mesmo artefato roda em dev, CI e produção.

### Observabilidade mínima

- Logs JSON (`structlog`) com `correlation_id` gerado no HTTP e **propagado no envelope dos eventos** ([ADR-0006](ADR-0006-eventos-outbox-rabbitmq.md)). Assim dá para seguir um clique até o consumer.
- `/healthz` (o processo está vivo) e `/readyz` (Mongo e Rabbit respondem).
- Métricas de negócio, como sessões e pontos por dia, viram projeções do `insights` e não Prometheus por enquanto.

### Fluxo de trabalho

Trunk-based, PRs pequenos, Conventional Commits, `tidy:` separado de `feat:`.

## Opções consideradas

| | Compose + 1 VM/PaaS ✅ | Kubernetes (ADR-0001) |
|---|---|---|
| Ops | Baixo | Alto |
| Custo p/ 1 usuário | Centavos | Dezenas de US$/mês |

## Consequências

- ✅ `git clone && make install && make up` sobe tudo.
- 🔁 Kubernetes e Prometheus voltam à mesa quando houver mais de um serviço com escala independente.
