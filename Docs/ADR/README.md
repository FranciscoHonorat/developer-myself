# Architecture Decision Records

| # | Decisão | Status |
|---|---|---|
| 0001 | [Definição de tecnologias](ADR%20-0001-tech.md) | Substituído em parte por 0004, 0005 e 0010 |
| 0002 | [Modelo de domínio — trilha gamificada](ADR-0002-modelo-de-dominio.md) | Aceito |
| 0003 | [Arquitetura hexagonal e layout sem `__init__.py`](ADR-0003-arquitetura-hexagonal.md) | Proposto |
| 0004 | [Backend Python 3.15 + FastAPI](ADR-0004-backend-python-fastapi.md) | Proposto |
| 0005 | [MongoDB como persistência do agregado](ADR-0005-mongodb.md) | Proposto |
| 0006 | [Eventos via outbox embutido + RabbitMQ](ADR-0006-eventos-outbox-rabbitmq.md) | Proposto |
| 0007 | [Toolchain, lint, format e automação](ADR-0007-toolchain-qualidade.md) | Proposto |
| 0008 | [Estratégia de testes TDD + BDD](ADR-0008-estrategia-de-testes.md) | Proposto |
| 0009 | [AppSec](ADR-0009-appsec.md) | Proposto |
| 0010 | [DevOps](ADR-0010-devops.md) | Proposto |
| 0011 | [Frontend React](ADR-0011-frontend-react.md) | Proposto |
| 0012 | [Dados para ML futuro](ADR-0012-dados-para-ml.md) | Proposto (adiado) |

## Ordem de implementação

Cada passo é um commit (ou PR) que **funciona e tem significado sozinho**.

| Passo | Entrega | Prova de que está pronto |
|---|---|---|
| 0 | `git init`, `.tool-versions`, `pyproject.toml`, Ruff, mypy, pre-commit, `Makefile` | `make check` verde com 1 teste; pytest-bdd lendo `# language: pt` |
| 1 | VOs: `Duration`, `Notes` (3 campos), `Points`, `MasteryLevel` | Testes unitários |
| 2 | `Content` + `StudyPlan.add_content` (fila de bloqueio) | Cenário "Conteúdo novo entra bloqueado" |
| 3 | Sessões + `ScoringPolicy` (25 min, anotações, 4 h) | Cenários de pontuação e de abandono |
| 4 | Regra de revisão diária | Cenários de revisão |
| 4b | `Challenge` + `MasteryPolicy` (pontos **e** 3 desafios) | Cenários de desbloqueio por nível |
| 5 | Teste de arquitetura (regra de dependência) | Falha ao importar `pymongo` no domínio |
| 6 | Casos de uso + `FakeClock` + repositório em memória + suíte de contrato | BDD via casos de uso |
| 7 | Adapter Mongo (optimistic lock, `$jsonSchema`) | Mesma suíte de contrato, agora no Mongo |
| 8 | `identity` + adapter HTTP FastAPI | Cadastro, login e iniciar/finalizar sessão via HTTP |
| 9 | Outbox relay + RabbitMQ + consumer do histórico | Evento chega em `study_sessions` de forma idempotente |
| 10 | Dockerfile, compose, pipeline de CI e scans | PR roda o pipeline inteiro |
| 11 | Frontend React | Smoke e2e no Playwright |
