# ADR-0011: Frontend em React + TypeScript (Vite)

**Status:** Proposto
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

A UI exibe a trilha, o timer da sessão, o editor de anotações e os avisos de bloqueio. **O frontend não guarda regras de negócio**: ele exibe o que o domínio decidiu.

## Decisão

- **Vite + React + TypeScript `strict`** e Biome ([ADR-0007](ADR-0007-toolchain-qualidade.md)).
- **TanStack Query** para o estado do servidor (cache, invalidação após cada comando). Nada de Redux: o estado global é o servidor.
- **`api/` como port**: um único módulo encapsula o `fetch` (`credentials: "same-origin"`, cabeçalho CSRF). Os componentes nunca chamam `fetch` diretamente.
- **O timer é só visual.** O cronômetro da tela não decide pontos. Ao finalizar, a UI mostra a resposta do servidor (`PointAwarded` ou `PointWithheld{reason}`).
- **Vitest + Testing Library**, com testes guiados pelo que o usuário vê, e Playwright para os smoke tests e2e.
- Dev: o proxy do Vite manda `/api` para o FastAPI, mantendo a **mesma origem** que o cookie exige ([ADR-0009](ADR-0009-appsec.md)).

## Opções consideradas

| | Vite SPA ✅ | Next.js |
|---|---|---|
| Precisa de SSR/SEO? | Não (app autenticada) | — |
| Peças móveis | 1 build estático | Servidor Node extra |

## Consequências

- ✅ O frontend é publicado como arquivos estáticos atrás do mesmo reverse proxy da API.
- 🔁 Se surgirem páginas públicas indexáveis, reavaliar o Next.js só para elas.
