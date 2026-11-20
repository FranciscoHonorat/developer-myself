# Caderno por matéria — design

**Data:** 2026-11-17 · **Status:** aprovado

## Intenção

Um bloco de notas livre e grande por matéria, para escrever conceitos com as próprias palavras **durante** a sessão (não só ao final), e reler/editar depois ao clicar na matéria.

## Objetivos

- Um caderno por conteúdo (matéria), que cresce ao longo de todas as sessões.
- Editável dentro do painel da sessão ativa, com salvamento automático.
- Aba **Caderno**: lista de matérias → clicar abre o caderno (ler e editar a qualquer momento).
- Botão **📓 Caderno** no card de cada matéria abre o mesmo caderno.

## Não-objetivos

- **Não** substitui os 3 campos (estudei/entendi/revisar): eles continuam obrigatórios para pontuar e alimentam a rede neural.
- O caderno **não** pontua, não tem mínimo de caracteres e não gera eventos/outbox.
- Sem formatação rica nesta versão (texto puro; Markdown pode vir depois).

## Anti-objetivos

- Perder texto: recarregar a página no meio da sessão não pode apagar o que foi escrito.
- Interferir na trilha: salvar o caderno não pode conflitar com iniciar/finalizar sessão.

## Abordagens

| | Escolha |
|---|---|
| **A. Agregado `Notebook` separado da trilha, coleção própria, autosave** | ✅ escolhida: não toca `StudyPlan`, eventos nem ML; sem disputa de escrita |
| B. Texto dentro de `Content` no `StudyPlan` | descartada: cada autosave regravaria a trilha inteira e competiria com os comandos de sessão |
| C. Só `localStorage` | descartada: perde dados entre dispositivos/limpezas |

## Design

**Backend (contexto `learning`, regra hexagonal mantida):**
- `learning/domain/notebook.py`: `Notebook(learner_id, content_id, text, version, updated_at)`. Texto até **100 000** caracteres. `edit(text, expected_version, now)` → recusa com `NotebookConflict` se a versão não bate (concorrência otimista: duas abas não se sobrescrevem em silêncio).
- Porta `NotebookRepository` (get / save com versão) com adapters **memória** e **Mongo** (coleção `notebooks`, índice único `(learner_id, content_id)`).
- Casos de uso: `get_notebook` (caderno vazio, versão 0, se ainda não existe) e `save_notebook`. Ambos conferem se o conteúdo existe na trilha do aprendiz (404 caso contrário). Remover um conteúdo apaga o caderno dele.
- HTTP: `GET /api/contents/{id}/notebook` → `{text, version, updated_at}`; `PUT /api/contents/{id}/notebook` com `{text, version}` → nova versão; `409` com `code: "NotebookConflictError"` em conflito (segue o padrão de erros do projeto); `GET /api/notebooks` → resumo (content_id, tamanho, updated_at) para a aba.

**Frontend:**
- Componente `NotebookEditor` (textarea grande + "salvando… / salvo ✓ / erro"), autosave com debounce de ~1 s e no `blur`; em 409 avisa "editado em outro lugar" e oferece recarregar.
- Usado no `ActiveSessionPanel` (acima dos 3 campos), na nova aba **Caderno** (lista de matérias à esquerda, editor à direita; no celular, lista → editor) e via botão no `ContentCard`.

**Testes (BDD, como o resto do projeto):** `caderno.feature` em português (escrever, reler, conflito de versão, conteúdo inexistente, limite de tamanho, remover conteúdo apaga o caderno); domínio com 100% de branches; contrato do repositório em memória e Mongo; HTTP; Vitest do editor (autosave e conflito).

## Decisões que tomei (pode corrigir)

- Concorrência otimista com versão, em vez de "última escrita vence".
- Limite de 100 000 caracteres.
- Caderno de matéria bloqueada (ainda na fila) também pode ser escrito na aba Caderno.
