# Caderno por matéria — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um bloco de notas livre por matéria, editável durante a sessão com autosave, relido/editado numa aba **Caderno** e pelo card da matéria.

**Architecture:** Novo agregado `Notebook` no contexto `learning`, separado do `StudyPlan` (coleção Mongo `notebooks`, sem eventos/outbox). Casos de uso `NotebookUseCases` conferem que o conteúdo existe na trilha do aprendiz. No front, um `NotebookEditor` com autosave (debounce 1 s, flush no blur/desmontar/aba oculta) é reutilizado no painel da sessão, na aba e no card.

**Tech Stack:** Python 3.15 · FastAPI · pymongo async · pytest-bdd · React 19 · TanStack Query · Vitest · playwright-bdd.

**Spec:** `docs/superpowers/specs/2026-11-17-caderno-por-materia-design.md`

## Global Constraints

- **Sem commits** neste repositório (uso pessoal; o usuário controla o histórico). Onde um plano normal diria "commit", rode `make lint typecheck` e siga.
- Texto do caderno: até **100 000** caracteres (`NOTEBOOK_MAX_CHARS = 100_000`); vazio é permitido (apagar tudo).
- Os 3 campos da sessão (estudei/entendi/revisar), pontos, eventos e rede neural **não mudam**.
- Concorrência otimista: o cliente envia a `version` que viu; diferente da atual → `NotebookConflictError` → HTTP **409**.
- Conteúdo inexistente na trilha do aprendiz → `ContentNotFoundError` → **404** (também protege contra id de outro usuário).
- Domínio puro (regra de `tests/architecture`), domínio com **100% de branches** (`make test-unit`), `mypy --strict`, Ruff, Biome.
- Textos de UI em português. Autosave: debounce **1000 ms**.
- Mongo 8.2+ (nesta máquina o 8.0 não sobe).

## Review Focus

1. **Finalizar a sessão com autosave pendente** (digitou e clicou "Finalizar" em < 1 s): o texto não pode se perder → o editor salva na hora ao desmontar (teste Vitest na Task 5).
2. **Digitar enquanto um salvamento está em voo**: o segundo PUT precisa usar a `version` devolvida pelo primeiro, senão gera 409 falso (teste Vitest na Task 5).
3. **Depois de um 409, o autosave para** até o usuário recarregar — senão ele fica em loop de conflito ou sobrescreve o outro lado (teste Vitest na Task 5).
4. **Id de conteúdo de outro aprendiz** em GET/PUT → 404, nunca o caderno alheio (teste HTTP na Task 4).
5. **Esvaziar o caderno** (apagar todo o texto) é um salvamento válido, não erro de validação (cenário BDD na Task 3).

---

### Task 1: Domínio `Notebook`

**Files:**
- Create: `backend/src/developer_myself/learning/domain/notebook.py`
- Modify: `backend/src/developer_myself/learning/domain/errors.py` (adicionar erro)
- Test: `backend/tests/unit/test_notebook.py`

**Interfaces:**
- Produces:
  - `NOTEBOOK_MAX_CHARS: int = 100_000`
  - `class NotebookConflictError(DomainError)` em `errors.py` — docstring: "O caderno mudou desde que foi aberto (outra aba)."
  - `@dataclass(slots=True) class Notebook: learner_id: LearnerId; content_id: ContentId; text: str = ""; version: int = 0; updated_at: datetime | None = None`
  - `Notebook.empty(learner_id: LearnerId, content_id: ContentId) -> Notebook` (classmethod)
  - `Notebook.edit(self, text: str, expected_version: int, now: datetime) -> None` — conflito se `expected_version != self.version`; `InvalidValueError` se `len(text) > NOTEBOOK_MAX_CHARS`; senão grava `text` e `updated_at = now`. **Não** incrementa `version` (quem incrementa é o repositório ao salvar, como no `StudyPlan`).
  - `Notebook.chars -> int` (property, `len(text)`)

- [x] **Step 1: Testes que falham** em `tests/unit/test_notebook.py`:
  - `test_empty_notebook_starts_at_version_zero`: `nb = Notebook.empty(...)` → `nb.text == ""`, `nb.version == 0`, `nb.updated_at is None`, `nb.chars == 0`.
  - `test_edit_replaces_text_and_stamps_time`: `nb.edit("conceito", 0, NOW)` → `nb.text == "conceito"`, `nb.updated_at == NOW`, `nb.version == 0`, `nb.chars == 8`.
  - `test_edit_with_stale_version_is_refused`: `nb.version = 2`; `pytest.raises(NotebookConflictError)` em `nb.edit("x", 1, NOW)`; texto não muda.
  - `test_edit_accepts_exactly_the_limit`: `"a" * 100_000` passa.
  - `test_edit_over_the_limit_is_refused`: `"a" * 100_001` → `InvalidValueError`.
  - `test_edit_to_empty_is_allowed`: depois de `"x"`, `edit("", 0, NOW)` → `text == ""`.
- [x] **Step 2:** `cd backend && poetry run pytest tests/unit/test_notebook.py -q` → FAIL (ImportError).
- [x] **Step 3:** Implementar `notebook.py` e o erro conforme Interfaces.
- [x] **Step 4:** `make test-unit test-arch` → PASS, cobertura do domínio 100%.

---

### Task 2: Repositório (port + memória + Mongo + contrato)

**Files:**
- Modify: `backend/src/developer_myself/learning/domain/repository.py` (novo Protocol)
- Create: `backend/src/developer_myself/learning/adapters/memory/notebook_repository.py`
- Create: `backend/src/developer_myself/learning/adapters/mongo/notebook_repository.py`
- Modify: `backend/src/developer_myself/shared/adapters/mongo_setup.py` (schema + índice)
- Test: `backend/tests/integration/test_notebook_repository_contract.py`

**Interfaces:**
- Consumes: `Notebook`, `ConcurrencyError` (já existe em `errors.py`).
- Produces:
  - `class NotebookRepository(Protocol)`:
    - `async def get(self, learner_id: LearnerId, content_id: ContentId) -> Notebook | None`
    - `async def save(self, notebook: Notebook) -> None` — optimistic lock: versão gravada ≠ `notebook.version` → `ConcurrencyError`; em sucesso `notebook.version += 1`.
    - `async def list_for(self, learner_id: LearnerId) -> list[Notebook]` — mais recente (`updated_at`) primeiro.
    - `async def delete(self, learner_id: LearnerId, content_id: ContentId) -> None` (idempotente)
    - `async def delete_all(self, learner_id: LearnerId) -> None` (exclusão de conta)
  - `InMemoryNotebookRepository` (dataclass, dict por `(learner_id, content_id)`, guarda/retorna cópias como `InMemoryStudyPlanRepository`).
  - `MongoNotebookRepository(collection: AsyncCollection[Doc])`. Documento: `{_id: content_id (UUID), learner_id: UUID, text, version, updated_at}`. Toda consulta filtra por `_id` **e** `learner_id`. `save`: versão 0 → `insert_one` (`DuplicateKeyError` → `ConcurrencyError`); senão `update_one({_id, learner_id, version: v}, {$set: {text, updated_at}, $inc: {version: 1}})`, `matched_count == 0` → `ConcurrencyError`.
  - Em `mongo_setup.py`: `NOTEBOOK_SCHEMA` (required `_id, learner_id, text, version, updated_at`; `text` string `maxLength: 100000`; `version` int/long ≥ 1; `updated_at` date); `ensure_schema` cria a coleção `notebooks` e o índice `[("learner_id", 1), ("updated_at", -1)]` nome `"by_learner"`.

- [x] **Step 1: Suíte de contrato que falha**, parametrizada `memory`/`mongo` igual a `test_study_plan_repository_contract.py` (`requires_docker`, `ensure_schema`, banco descartável):
  - `test_missing_notebook_is_none`
  - `test_save_then_get_round_trips` (texto, `updated_at`, `version == 1` após o save)
  - `test_second_save_increments_version` (→ 2)
  - `test_stale_save_raises_concurrency_error`: duas cópias lidas na v1; a primeira salva; a segunda → `ConcurrencyError`.
  - `test_two_first_saves_conflict`: dois `Notebook.empty` do mesmo conteúdo; o segundo save → `ConcurrencyError`.
  - `test_other_learner_cannot_read`: salvo para A; `get(B, mesmo content_id)` → `None`.
  - `test_list_for_returns_most_recent_first_and_only_mine`
  - `test_delete_and_delete_all`
- [x] **Step 2:** `cd backend && poetry run pytest tests/integration/test_notebook_repository_contract.py -q` → FAIL (ImportError).
- [x] **Step 3:** Implementar port, os dois adapters e o schema/índice.
- [x] **Step 4:** `make test-int` → PASS nos dois parâmetros (precisa de Docker); `make typecheck lint` limpos.

---

### Task 3: Casos de uso + BDD

**Files:**
- Create: `backend/src/developer_myself/learning/application/notebooks.py`
- Modify: `backend/src/developer_myself/learning/application/use_cases.py` (`RemoveContent`, `LearningUseCases`)
- Create: `backend/tests/features/caderno.feature`, `backend/tests/features/test_caderno.py`
- Modify: `backend/tests/features/conftest.py` (`World`)

**Interfaces:**
- Consumes: `NotebookRepository`, `Notebook`, `StudyPlanRepository`, `StudyPlanNotFoundError`, `StudyPlan.content()` (levanta `ContentNotFoundError`).
- Produces:
  - `@dataclass(slots=True) class NotebookUseCases: plans: StudyPlanRepository; notebooks: NotebookRepository; clock: Clock`
    - `async def get(self, learner_id: uuid.UUID, content_id: uuid.UUID) -> Notebook` — confere o conteúdo; inexistente no repo → `Notebook.empty(...)`.
    - `async def save(self, learner_id: uuid.UUID, content_id: uuid.UUID, text: str, version: int) -> Notebook` — confere o conteúdo → get-or-empty → `edit(text, version, clock.now())` → `save` → devolve o caderno (já com a versão nova).
    - `async def list(self, learner_id: uuid.UUID) -> list[Notebook]`
    - `async def erase(self, learner_id: uuid.UUID) -> None` → `delete_all`.
  - `RemoveContent` ganha o campo `notebooks: NotebookRepository | None = None`; depois de salvar a trilha, apaga o caderno do conteúdo removido.
  - `LearningUseCases` ganha o campo `notebooks: NotebookUseCases`; `build(cls, repository, clock, unlock_policy=None, *, notebooks: NotebookRepository)` monta `NotebookUseCases(repository, notebooks, clock)` e passa `notebooks=` ao `RemoveContent`.
  - `World` (conftest): campo `notebooks: InMemoryNotebookRepository`, passado ao `build`.

- [x] **Step 1: `caderno.feature`** (`# language: pt`, `Funcionalidade: Caderno da matéria`), cenários:
  - *Escrever no caderno durante a sessão*: `Dado que "Clean Code" está em andamento` / `E que iniciei uma sessão em "Clean Code"` / `Quando eu escrevo no caderno de "Clean Code": "Funções pequenas fazem uma coisa só"` / `Então o caderno de "Clean Code" diz "Funções pequenas fazem uma coisa só"`.
  - *O caderno não muda a pontuação*: escrever + `Quando eu estudo "Clean Code" por 25 minutos com anotações` → `Então "Clean Code" tem 1 ponto`.
  - *O caderno cresce entre sessões*: escrever "A" e depois "A\nB" (o step usa a versão atual) → diz "A\nB" (use `\n` literal no texto e substitua no step).
  - *Esvaziar o caderno*: escrever "x" e depois `eu apago o caderno de "Clean Code"` → `o caderno de "Clean Code" está vazio`.
  - *Duas abas abertas*: `Quando eu escrevo no caderno de "Clean Code" a partir de uma versão antiga` → `Então o salvamento do caderno é recusado por conflito`.
  - *Matéria na fila também tem caderno*: `Dado que "Refactoring" está bloqueado` → escrever → diz.
  - *Matéria que não está na trilha*: `Quando eu tento escrever no caderno de uma matéria que não existe` → `Então o salvamento do caderno é recusado porque a matéria não existe` (`ContentNotFoundError`).
  - *Texto grande demais*: `Quando eu tento escrever 100001 caracteres no caderno de "Clean Code"` → `Então o salvamento do caderno é recusado por tamanho`.
  - *Remover a matéria apaga o caderno*: `Dado que "Clean Code" está em andamento` / `E que "Refactoring" está bloqueado` / escrever em "Refactoring" / `Quando eu removo "Refactoring"` / `Então não existe caderno para "Refactoring"` (consulta o repositório direto, pois o conteúdo sumiu).
- [x] **Step 2: Steps** em `test_caderno.py` (`scenarios("caderno.feature")`, padrão de `test_competencias.py`); erros capturados em `world.error`. "Versão antiga" = versão atual − 1 depois de já existir uma escrita (o Given escreve uma vez antes).
- [x] **Step 3:** `cd backend && poetry run pytest tests/features/test_caderno.py -v` → FAIL.
- [x] **Step 4:** Implementar `notebooks.py`, o campo em `RemoveContent`, o `build` e o `World`. Atualizar também os outros dois chamadores de `build`: `bootstrap.py` passa `notebooks=InMemoryNotebookRepository()` e `mongo_bootstrap.py` passa `notebooks=MongoNotebookRepository(db.notebooks)`.
- [x] **Step 5:** `make test test-arch typecheck` → PASS.

---

### Task 4: HTTP + composição

**Files:**
- Modify: `backend/src/developer_myself/learning/adapters/http/schemas.py`, `.../http/routes.py`
- Modify: `backend/src/developer_myself/bootstrap.py`, `backend/src/developer_myself/mongo_bootstrap.py`
- Test: `backend/tests/http/test_api.py`

**Interfaces:**
- Consumes: `LearningUseCases.notebooks` (Task 3), `InMemoryNotebookRepository`/`MongoNotebookRepository` (Task 2).
- Produces (contrato para o front):
  - `GET /api/contents/{content_id}/notebook` → `NotebookOut {content_id: UUID, text: str, version: int, updated_at: datetime | None}`
  - `PUT /api/contents/{content_id}/notebook` body `NotebookIn {text: StrictStr (max_length=100_000), version: int (ge=0)}`, `extra="forbid"` → `NotebookOut`
  - `GET /api/notebooks` → `list[NotebookSummaryOut {content_id: UUID, chars: int, updated_at: datetime | None}]`
  - Erros já mapeados pelo handler genérico: `NotebookConflictError` → 409, `ContentNotFoundError` → 404, `InvalidValueError` → 422.
  - Composição (os repositórios já foram ligados ao `build` na Task 3): os dois `erase` (memória e Mongo) chamam também `delete_all` do repositório de cadernos.

- [x] **Step 1: Testes HTTP que falham** em `tests/http/test_api.py` (helpers `register`, `add_content`, `H`):
  - `test_notebook_starts_empty`: GET → `{"text": "", "version": 0, "updated_at": None}`.
  - `test_notebook_save_and_read_back`: PUT `{"text": "conceito", "version": 0}` → 200, `version == 1`; GET devolve o texto.
  - `test_notebook_stale_version_is_409`: dois PUT com `version: 0` → o segundo 409 e `code == "NotebookConflictError"`.
  - `test_notebook_of_another_learner_is_404`: A cria conteúdo e escreve; B (novo client/cookie) faz GET e PUT no mesmo id → 404 nos dois.
  - `test_notebook_too_long_is_422`: texto com 100 001 chars → 422.
  - `test_notebooks_list_summarizes`: depois de um PUT, `GET /api/notebooks` → um item com `chars` e `updated_at`.
  - `test_put_notebook_requires_csrf_header`: PUT sem `H` → 403.
  - `test_delete_account_erases_notebooks`: seguir o teste de exclusão de conta já existente e conferir que o repositório de cadernos ficou vazio para o aprendiz.
- [x] **Step 2:** `make test-http` → FAIL.
- [x] **Step 3:** Implementar schemas, rotas (finas, padrão das existentes) e a composição.
- [x] **Step 4:** `make lint typecheck test test-int` → PASS.

---

### Task 5: Front — API + `NotebookEditor` com autosave

**Files:**
- Modify: `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/hooks.ts`
- Create: `frontend/src/components/NotebookEditor.tsx`
- Test: `frontend/src/components/NotebookEditor.test.tsx`

**Interfaces:**
- Consumes: contrato HTTP da Task 4.
- Produces:
  - Tipos: `Notebook {content_id: string; text: string; version: number; updated_at: string | null}`, `NotebookSummary {content_id: string; chars: number; updated_at: string | null}`.
  - `api.notebook(contentId): Promise<Notebook>`, `api.saveNotebook(contentId, text, version): Promise<Notebook>`, `api.notebooks(): Promise<NotebookSummary[]>`.
  - `keys.notebook(id) = ["notebook", id]`, `keys.notebooks = ["notebooks"]`; `useNotebook(contentId)`, `useNotebooks()`. O autosave **não** usa `useCommand` (não invalida a trilha a cada tecla); ao salvar, atualiza o cache `keys.notebook(id)` com a resposta e invalida `keys.notebooks`.
  - `<NotebookEditor contentId: string; title: string />` — `<label>` "📓 Caderno de {title}" + textarea (`rows={10}`, `maxLength={100000}`) + status com `role="status"`: "Salvando…", "Salvo ✓", "Alterações não salvas", ou "Editado em outro lugar." com botão "Recarregar" (refaz o GET e substitui o texto local).
  - Algoritmo do autosave (refs, não estado, para `version`/texto mais recentes): cada mudança agenda salvar em 1000 ms; **um PUT por vez** — se o texto mudar durante o voo, ao voltar salva de novo com a `version` devolvida; `blur`, `visibilitychange → hidden` e o **cleanup ao desmontar** disparam o salvamento pendente na hora; em **409** para de agendar até "Recarregar"; outros erros mostram a mensagem e tentam de novo na próxima edição.

- [x] **Step 1: Testes que falham** (`vi.useFakeTimers()`, `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`, `fetch` roteado por URL/método):
  - `carrega o texto do caderno`: GET devolve `{text: "antes", version: 3}` → textarea mostra "antes".
  - `salva 1 s depois de parar de digitar, uma vez só`: digitar "abc"; após 999 ms nenhum PUT; após 1000 ms exatamente 1 PUT com body `{text: "antesabc", version: 3}`; status "Salvo ✓".
  - `usa a versão nova se editar durante o salvamento`: o 1º PUT fica pendente (promise manual); digitar mais; resolver com `version: 4`; o 2º PUT sai com `version: 4`.
  - `em conflito para de salvar e oferece recarregar`: PUT → 409; aparece "Editado em outro lugar."; digitar mais e avançar 2 s → nenhum PUT novo; clicar "Recarregar" refaz o GET.
  - `salva na hora ao desmontar com alteração pendente`: digitar, `unmount()` antes de 1 s → 1 PUT com o texto.
- [x] **Step 2:** `cd frontend && npx vitest run src/components/NotebookEditor.test.tsx` → FAIL.
- [x] **Step 3:** Implementar a API e o componente.
- [x] **Step 4:** `make test-web lint typecheck` → PASS.

---

### Task 6: Front — sessão, aba Caderno, card da matéria, e2e e README

**Files:**
- Modify: `frontend/src/components/ActiveSessionPanel.tsx` (+ `ActiveSessionPanel.test.tsx`)
- Create: `frontend/src/components/NotebookView.tsx`, `frontend/src/components/NotebookView.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/ContentCard.tsx` (+ `ContentCard.test.tsx`), `frontend/src/styles.css`
- Modify: `frontend/e2e/features/jornada.feature`, `frontend/e2e/steps/jornada.steps.ts`
- Modify: `readme.md` (linha "Caderno" na tabela "Regras do jogo")

**Interfaces:**
- Consumes: `NotebookEditor`, `useNotebooks`, `usePlan` (Task 5).
- Produces:
  - `ActiveSessionPanel` renderiza `<NotebookEditor contentId={session.content_id} title={session.content_title} />` **acima** do formulário dos 3 campos.
  - Aba nova em `App.tsx`: `{ id: "notebook", label: "Caderno" }` logo depois de "Semana"; `Tab` ganha `"notebook"`.
  - `<NotebookView />`: lista à esquerda com todos os conteúdos da trilha (`usePlan`), cada um um botão com o título e, se houver resumo em `useNotebooks`, "N caracteres · editado em dd/mm"; clicar seleciona e mostra `<NotebookEditor key={id} …>` à direita; sem conteúdos → "Adicione um conteúdo na Trilha para ter um caderno."; nada selecionado → "Escolha uma matéria.". Em telas estreitas (≤ 640 px) as colunas empilham.
  - `ContentCard`: botão `ghost` "📓 Caderno" ao lado de "Cronograma"; alterna `showNotebook` e renderiza `<NotebookEditor>` abaixo, como o `ScheduleView`.

- [x] **Step 1: Testes que falham:**
  - `ActiveSessionPanel.test.tsx`: os testes existentes leem `fetchMock.mock.calls[0]` — passe a rotear o mock por URL e a procurar a chamada de `/api/sessions/current/finish`. Novo: `mostra o caderno da matéria durante a sessão` → existe o campo "📓 Caderno de Clean Code".
  - `NotebookView.test.tsx`: `lista as matérias e abre o caderno ao clicar` (plano com 2 conteúdos; clicar "Clean Code" mostra o campo "📓 Caderno de Clean Code" com o texto do GET); `sem conteúdos mostra o convite`.
  - `ContentCard.test.tsx`: `abre o caderno pelo card` (clicar "📓 Caderno" mostra o campo).
- [x] **Step 2:** `cd frontend && npx vitest run` → FAIL nos novos.
- [x] **Step 3:** Implementar.
- [x] **Step 4: Cenário e2e** em `jornada.feature`: *O caderno guarda o que escrevi na matéria* — adiciono "Clean Code"; inicio sessão de estudo; `E eu escrevo no caderno "Funções pequenas fazem uma coisa só"`; finalizo com as anotações; `Quando eu abro "Clean Code" na aba Caderno`; `Então vejo "Funções pequenas fazem uma coisa só" no caderno`. Steps novos em `jornada.steps.ts` (o step de escrita espera o status "Salvo ✓").
- [x] **Step 5:** README: linha `| Caderno | Bloco livre por matéria, salvo sozinho enquanto você digita; não pontua. Abra na aba **Caderno** ou no botão 📓 do card |`.
- [x] **Step 6: Verificação final:** `make check` e `make e2e` → tudo verde. Conferir à mão com `make up`: escrever durante uma sessão, recarregar a página, o texto continua.
