# ADR-0004: Backend em Python 3.15 + FastAPI

**Status:** Proposto. Substitui a parte de backend do [ADR-0001](ADR%20-0001-tech.md) (Go).
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

O sistema é I/O-bound (Mongo, RabbitMQ, HTTP) e tem um único usuário no início. O ecossistema de ML futuro ([ADR-0012](ADR-0012-dados-para-ml.md)) é Python.

## Decisão

- **Python 3.15**, a estável mais recente (lançada em 2026-10-09). Critério: projeto novo começa na versão estável mais recente. Trazemos do 3.14 o `uuid.uuid7()` nativo, que gera IDs ordenados no tempo e dá boa localidade no índice `_id`, e as anotações avaliadas de forma adiada (PEP 649), que dispensam `from __future__ import annotations`. Do 3.15 vem o `frozendict` embutido (PEP 814), útil em value objects.
  - **Condição de saída:** se alguma dependência com extensão C (`pydantic-core`, `pymongo`, `argon2-cffi`) não tiver *wheel* para o 3.15 no passo 0, voltamos para o 3.14 e registramos o motivo aqui.
- **FastAPI + Uvicorn**, com **async de ponta a ponta**: `pymongo.AsyncMongoClient` (a API async oficial; o Motor está descontinuado) e `aio-pika`.
- **Pydantic só nos adapters de entrada** (DTOs, `pydantic-settings` para configuração). O domínio usa `@dataclass(frozen=True, slots=True)`.
- O `Depends` do FastAPI apenas **entrega** o que o `bootstrap.py` montou e nunca constrói infraestrutura. O `lifespan` abre e fecha os clientes.

## Opções consideradas

| | FastAPI ✅ | Go (ADR-0001) | Django + DRF | Litestar |
|---|---|---|---|---|
| Fit hexagonal | Alto (fino) | Alto | Baixo (ORM acoplado) | Alto |
| Async nativo | Sim | Sim | Parcial | Sim |
| Ecossistema ML | Mesmo | Separado | Mesmo | Mesmo |
| Comunidade/material | Muito alta | Alta | Muito alta | Média |

O Go seria mais rápido e mais barato de operar, mas desempenho não é uma restrição aqui. Ter uma única linguagem, também usada pelo ML, pesa mais.

## Consequências

- ✅ `async` permite que o mesmo processo atenda HTTP e eventos sem threads.
- ⚠️ Uma chamada bloqueante (ex.: `argon2` síncrono) trava o event loop. Ela deve ir para `asyncio.to_thread`.
- 🔁 Os builds *free-threaded* ficam fora por enquanto; reavaliar só se surgir trabalho CPU-bound.
