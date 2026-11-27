# Revisão como teste de memória — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Toda revisão começa com 3 perguntas respondidas de memória e corrigidas pelo aprendiz (obrigatório para finalizar), o último "preciso revisar" volta no topo de toda sessão, e cada pergunta vira dado de treino da IA futura.

**Architecture:** O teste vive na sessão do agregado `StudyPlan`: as perguntas são escolhidas por um port `QuestionPicker` ao iniciar uma revisão e guardadas na `ActiveSession`; as respostas chegam no finalizar e seguem no `StudySessionFinished` → outbox → histórico (`insights`). A escolha inicial é por regra (`review_questions.py`, composição `learning` + `curriculum`); a IA implementará o mesmo port depois.

**Tech Stack:** Python 3.15 · FastAPI · pymongo async · pytest-bdd · React 19 · TanStack Query · Vitest.

**Spec:** `docs/specs/2026-11-17-revisao-como-teste-design.md`

## Global Constraints

- **Sem commits** neste repositório; onde haveria commit, rode `make lint typecheck` e siga.
- **3 perguntas** por revisão; no máximo **2** vindas do "preciso revisar".
- Texto da pergunta ≤ **500**; item do "preciso revisar" cortado em **400** + "…"; resposta ≤ **5 000** (pode ser vazia).
- Correções: `MISSED` (Errei) · `PARTIAL` (Parcial) · `RECALLED` (Acertei). `useful`: `true` · `false` · `null` (opcional).
- Origens: `TO_REVIEW` · `SPACED_TOPIC` · `TOPIC` · `LEARNER` (reservada). Modelos: `explain_to_review`, `recall_topic`, `when_to_use`, `teach_beginner`.
- Textos fixos: `"Explique sem consultar: {item}"`, `"O que você lembra de {tópico}? Explique com um exemplo seu."`, `"Quando usar {tópico} e quando não usar?"`, `"Explique {tópico} para quem está começando."`, banner `"🔁 Da última vez você anotou para revisar:"`.
- Revisão com perguntas não finaliza sem uma correção para cada pergunta → `RecallTestRequiredError` (subclasse de `InvalidValueError` → 422). Sessão sem perguntas não exige teste.
- Mongo `study_plans`: `SCHEMA_VERSION = 4`, upcaster lazy v3→v4.
- Domínio puro, 100% de branches no domínio, `mypy --strict`, Ruff, Biome; BDD em português.

## Review Focus

1. **Revisão aberta antes do deploy** (sessão ativa sem perguntas) finaliza sem teste e sem erro → cenário BDD na Task 3.
2. **"Preciso revisar" só com espaços, linhas vazias ou marcadores soltos** (`"- \n•  \n"`) não gera pergunta vazia → teste na Task 3.
3. **Respostas com id repetido, id desconhecido ou faltando uma** são recusadas → testes na Task 1.
4. **Recarregar no meio do teste** mantém respostas e passo → Vitest na Task 6.
5. **Dia de desafio/laboratório sem tópicos espaçados, ou matéria com 1 tópico só** ainda gera 3 perguntas de textos diferentes → teste na Task 3.

---

### Task 1: Domínio do teste

**Files:**
- Modify: `backend/src/developer_myself/learning/domain/value_objects.py`, `.../domain/errors.py`, `.../domain/content.py`, `.../domain/study_plan.py`, `.../domain/events.py`
- Test: `backend/tests/unit/test_recall_test.py`

**Interfaces:**
- Produces:
  - `class QuestionSource(StrEnum)`: `TO_REVIEW, SPACED_TOPIC, TOPIC, LEARNER`.
  - `class RecallGrade(StrEnum)`: `MISSED, PARTIAL, RECALLED`.
  - `@dataclass(frozen=True, slots=True) class RecallQuestion: id: uuid.UUID; text: str; source: QuestionSource; template: str; topic: str | None = None` — `__post_init__`: texto não vazio após `strip` e ≤ 500, senão `InvalidValueError`; `topic` ≤ 500.
  - `@dataclass(frozen=True, slots=True) class RecallAnswer: question_id: uuid.UUID; answer: str; grade: RecallGrade; useful: bool | None = None` — `answer` ≤ 5 000 (`InvalidValueError`).
  - `class RecallTestRequiredError(InvalidValueError)` em `errors.py`.
  - `ActiveSession` ganha `questions: tuple[RecallQuestion, ...] = ()`.
  - `Content` ganha `last_to_review: str | None = None`; `_register_session(..., to_review: str)` atualiza quando `to_review.strip()` não é vazio.
  - `StudyPlan.start_session(content_id, now, questions: tuple[RecallQuestion, ...] = ())` — guarda `questions` só se o tipo for `REVIEW`.
  - `StudyPlan.finish_session(notes, now, recall=None, answers: tuple[RecallAnswer, ...] = ())` — se `session.questions` não vazio: `{a.question_id for a in answers}` precisa ser **igual** ao conjunto de ids das perguntas e `len(answers) == len(questions)`; senão `RecallTestRequiredError("Responda e corrija as 3 perguntas do teste antes de finalizar.")`. Checar **antes** da expiração (como a autoavaliação).
  - `StudyPlan.backfill_last_to_review(content_id: ContentId, text: str) -> bool` — define só se `last_to_review` é `None` e `text.strip()` não vazio; devolve se mudou. (Usado na Task 5.)
  - `StudySessionFinished` ganha `recall_test: tuple[dict[str, object], ...] = ()`, um item por pergunta, na ordem: `{"question_id", "text", "source", "template", "topic", "position" (0..2), "answer", "grade", "useful"}`.

- [x] **Step 1: Testes que falham** em `tests/unit/test_recall_test.py` (padrão de `test_study_plan.py`: plano com um conteúdo consolidado via helpers do próprio arquivo ou do domínio):
  - `test_question_text_must_not_be_blank` / `test_question_text_over_500_is_refused` / `test_answer_over_5000_is_refused`.
  - `test_review_start_keeps_the_questions` (3 perguntas → `plan.active_session.questions` igual).
  - `test_study_start_ignores_questions` (conteúdo em andamento → `questions == ()`).
  - `test_finish_review_without_answers_is_refused` → `RecallTestRequiredError`; sessão continua ativa.
  - `test_finish_with_missing_answer_is_refused`, `test_finish_with_unknown_question_id_is_refused`, `test_finish_with_duplicated_answer_is_refused`.
  - `test_finish_with_all_missed_still_awards_when_rules_met` (25 min, boas notas, revisão do dia → `outcome.awarded`).
  - `test_finish_without_questions_needs_no_test` (sessão de revisão iniciada sem perguntas).
  - `test_event_carries_the_recall_test` (os 9 campos, `position` 0..2, `grade` como string do enum após `envelope`).
  - `test_finish_updates_last_to_review` e `test_blank_to_review_keeps_previous`.
  - `test_backfill_sets_only_when_empty` (`True` na 1ª, `False` se já tinha ou texto em branco).
- [x] **Step 2:** `cd backend && poetry run pytest tests/unit/test_recall_test.py -q` → FAIL (ImportError).
- [x] **Step 3:** Implementar conforme Interfaces.
- [x] **Step 4:** `make test-unit test-arch` → PASS com 100% de branches (os BDD existentes continuam verdes; `simulation.py` não muda porque os defaults são vazios).

---

### Task 2: Persistência (Mongo v4)

**Files:**
- Modify: `backend/src/developer_myself/learning/adapters/mongo/repository.py`, `backend/src/developer_myself/shared/adapters/mongo_setup.py`
- Test: `backend/tests/integration/test_study_plan_repository_contract.py`, e o arquivo onde hoje se testa `upcast` (procure `upcast(` em `backend/tests`)

**Interfaces:**
- Consumes: `RecallQuestion`, `ActiveSession.questions`, `Content.last_to_review` (Task 1).
- Produces: `SCHEMA_VERSION = 4`; `_v3_to_v4(doc)` põe `last_to_review: None` em cada conteúdo e `questions: []` em `active_session` (se houver); `UPCASTERS[3] = _v3_to_v4`. Mapper grava/lê `active_session.questions` como `[{id, text, source, template, topic}]` e `contents[].last_to_review`. Validador: `active_session.properties.questions` `{"bsonType": "array"}`; conteúdo `last_to_review` `{"bsonType": ["string", "null"]}`.

- [x] **Step 1: Testes que falham:** no contrato, `rich_plan()` passa a ter uma revisão ativa com 3 perguntas e um conteúdo com `last_to_review`; `test_roundtrip_preserves_the_whole_aggregate` já compara `contents` e `active_session` — basta enriquecer o fixture. Novo `test_upcast_v3_to_v4` (doc v3 sem os campos → v4 com `last_to_review None` e `questions []`).
- [x] **Step 2:** `make test-int` → FAIL.
- [x] **Step 3:** Implementar.
- [x] **Step 4:** `make test-int lint typecheck` → PASS.

---

### Task 3: Escolha das perguntas + casos de uso + BDD

**Files:**
- Create: `backend/src/developer_myself/learning/application/questions.py` (port), `backend/src/developer_myself/review_questions.py` (regra)
- Modify: `backend/src/developer_myself/learning/application/use_cases.py` (`StartSession`, `FinishSession`, `build`), `bootstrap.py`, `mongo_bootstrap.py`
- Create: `backend/tests/features/teste_de_memoria.feature`, `backend/tests/features/test_teste_de_memoria.py`, `backend/tests/unit/test_review_questions.py`
- Modify: `backend/tests/features/conftest.py` (`World` usa o picker real)

**Interfaces:**
- Consumes: Task 1; `schedule_for(title)`, `today_for(points)`, `Schedule.day(n).warmup`, `CatalogEntry.topics`.
- Produces:
  - `class QuestionPicker(Protocol): def pick(self, plan: StudyPlan, content: Content, now: datetime) -> tuple[RecallQuestion, ...]: ...`
  - `class RuleQuestionPicker` (em `review_questions.py`) com `QUESTIONS_PER_REVIEW = 3`, `MAX_FROM_TO_REVIEW = 2`. Algoritmo: (1) itens de `content.last_to_review` divididos por linha, removendo marcadores `-`, `•`, `*`, `1.`/`1)` e espaços, descartando vazios, até 2, cortados em 400 + "…" → `TO_REVIEW`/`explain_to_review`, `topic` = item original (≤ 500); (2) `warmup` do dia `today_for(content.points.value)` do cronograma, sem o sufixo `" (N dia(s) atrás)"` → `SPACED_TOPIC`/`recall_topic`; (3) `entry.topics` começando pelo índice do tópico do dia (ou 0) em ciclo, com modelos em rodízio `recall_topic` → `when_to_use` → `teach_beginner` → `TOPIC`. Nunca repete o texto final; para no 3º. `id = uuid.uuid7()`.
  - `StartSession` ganha `question_picker: QuestionPicker | None = None`; quando o `content.session_kind` é `REVIEW` e há picker, passa `picker.pick(plan, content, now)` ao `start_session`.
  - `@dataclass(frozen=True, slots=True) class AnswerInput: question_id: uuid.UUID; answer: str; grade: str; useful: bool | None = None`; `FinishSession.__call__(learner_id, notes, recall_rating=None, answers: list[AnswerInput] | None = None)` converte (`grade` inválido → `InvalidValueError`).
  - `LearningUseCases.build(..., *, notebooks, question_picker: QuestionPicker | None = None)`. Os dois bootstraps passam `RuleQuestionPicker()`.

- [x] **Step 1: Unit do picker** (`test_review_questions.py`, conteúdo do catálogo real, ex.: "Learning Go"):
  - `test_to_review_items_come_first_split_by_line` (`"- canais\n- select"` → 2 primeiras `TO_REVIEW` com textos `"Explique sem consultar: canais"`/`"… select"`).
  - `test_at_most_two_from_to_review` (5 itens → 2).
  - `test_long_item_is_cut_at_400` (texto termina em "…", `topic` guarda o original até 500).
  - `test_blank_bullets_make_no_question` (`"- \n•  \n"` → nenhuma `TO_REVIEW`).
  - `test_spaced_topics_follow` (conteúdo com pontos num dia que tem `warmup` → 3ª é `SPACED_TOPIC` sem "dias atrás").
  - `test_always_three_distinct_even_with_one_topic` (conteúdo fora do catálogo/1 tópico, dia de desafio → 3 textos distintos, modelos em rodízio).
- [x] **Step 2: `teste_de_memoria.feature`** (`# language: pt`), cenários:
  - *A revisão começa com 3 perguntas*: `Dado que "Clean Code" está consolidado` / `Quando eu inicio uma sessão em "Clean Code"` / `Então a sessão tem 3 perguntas de memória`.
  - *O "preciso revisar" vira a primeira pergunta*: consolidado + `E que anotei para revisar em "Clean Code": "CQS"` (sessão de 25 min com essas notas) → inicio → `Então a 1ª pergunta é "Explique sem consultar: CQS"`.
  - *Sem corrigir o teste não dá para finalizar*: inicio revisão → `Quando eu finalizo a revisão 25 minutos depois sem responder o teste` → `Então a finalização é recusada pedindo o teste`.
  - *Errar tudo ainda pontua*: `Dado que "Clean Code" está consolidado` (10 pontos) / `E que iniciei uma sessão em "Clean Code"` / `Quando eu finalizo a revisão 25 minutos depois errando todas` → `Então "Clean Code" tem 11 pontos` (step de pontos existente).
  - *Estudo não tem teste*: em andamento → inicio → `Então a sessão não tem perguntas de memória`.
  - *Revisão aberta antes da mudança*: `Dado que uma revisão de "Clean Code" foi aberta antes do teste existir` (inicia sem picker) → finaliza com notas e nota 3 → pontua.
  - *O "preciso revisar" volta na próxima sessão*: estudo com `to_review` "goroutines" → `Então o último "preciso revisar" de "Clean Code" é "goroutines"`.
  - *O histórico guarda o teste*: revisão corrigida → `Então o histórico registra 3 perguntas com as minhas correções`.
- [x] **Step 3:** `cd backend && poetry run pytest tests/unit/test_review_questions.py tests/features/test_teste_de_memoria.py -q` → FAIL.
- [x] **Step 4:** Implementar port, picker, casos de uso, `World` e bootstraps.
- [x] **Step 5:** `make test test-arch typecheck lint` → PASS (o teste de arquitetura não cobre a raiz; manter `review_questions.py` sem importar adapters).

---

### Task 4: Histórico + HTTP

**Files:**
- Modify: `backend/src/developer_myself/insights/application/history.py`, `.../insights/adapters/http_routes.py`, `.../learning/adapters/http/schemas.py`, `.../learning/adapters/http/routes.py`
- Test: `backend/tests/http/test_api.py`, `backend/tests/unit/test_projection.py` (ou onde `from_envelope` é testado)

**Interfaces:**
- Consumes: evento com `recall_test` (Task 1), casos de uso (Task 3).
- Produces (contrato do front):
  - `SessionRecord.recall_test: list[dict[str, Any]] = field(default_factory=list)`, lido de `p.get("recall_test", [])`; `SessionOut.recall_test: list[RecallItemOut]` com `{text, source, answer, grade, useful}`.
  - `ActiveSessionOut` ganha `questions: list[{id, text, source}]` e `last_to_review: str | None`; `ContentOut` ganha `last_to_review: str | None`.
  - `FinishSessionIn.answers: list[AnswerIn] = []`, `AnswerIn {question_id: UUID, answer: StrictStr (max 5000, default ""), grade: Literal["MISSED","PARTIAL","RECALLED"], useful: bool | None = None}`, `extra="forbid"`.
  - `RecallTestRequiredError` → 422 pelo handler existente (`InvalidValueError`).

- [x] **Step 1: Testes que falham** (HTTP; reutilize `consolidate()`):
  - `test_review_session_exposes_three_questions`: depois de consolidar, iniciar revisão → `GET /api/plan` `active_session.questions` com 3 itens e `last_to_review`.
  - `test_finish_review_without_answers_is_422` com `code == "RecallTestRequiredError"`.
  - `test_finish_review_with_answers_records_the_test`: finaliza com as 3 respostas → `GET /api/history` 1º item `recall_test` com 3 itens e `grade`.
  - `test_invalid_grade_is_422`.
  - `from_envelope` com payload sem `recall_test` → `[]` (unit).
- [x] **Step 2:** `make test-http` → FAIL.
- [x] **Step 3:** Implementar.
- [x] **Step 4:** `make lint typecheck test test-int` → PASS.

---

### Task 5: Backfill do "preciso revisar"

**Files:**
- Create: `backend/src/developer_myself/backfill_to_review.py`
- Modify: `Makefile` (alvo `backfill-to-review`)
- Test: `backend/tests/unit/test_backfill_to_review.py`

**Interfaces:**
- Consumes: `StudyPlan.backfill_last_to_review` (Task 1), `StudyPlanRepository`, `SessionHistoryStore.list_for` (veja a assinatura em `insights/application/history.py`).
- Produces: `async def backfill_last_to_review(plans: StudyPlanRepository, history: <store>, learner_id: uuid.UUID) -> int` — para cada conteúdo, o `notes_to_review` não vazio da sessão finalizada **mais recente** daquele `content_id`; salva o plano uma vez se mudou algo; devolve quantos conteúdos mudaram. `__main__`: conecta no Mongo pelas `Settings`, percorre os `_id` de `study_plans`, imprime o total. Alvo: `backfill-to-review: ## Preenche o "preciso revisar" das matérias a partir do histórico (stack no ar)` → `docker compose exec -T api python -m developer_myself.backfill_to_review`.

- [x] **Step 1: Testes que falham** (repositórios em memória): `test_fills_from_latest_non_empty_session`, `test_keeps_existing_value`, `test_idempotent_second_run_changes_nothing`.
- [x] **Step 2:** `poetry run pytest tests/unit/test_backfill_to_review.py -q` → FAIL.
- [x] **Step 3:** Implementar.
- [x] **Step 4:** `make test lint typecheck` → PASS; `make help | grep backfill` lista o alvo.

---

### Task 6: Tela — teste no painel, banner, histórico

**Files:**
- Modify: `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/hooks.ts`, `frontend/src/api/labels.ts`
- Create: `frontend/src/components/RecallTest.tsx`, `frontend/src/components/RecallTest.test.tsx`
- Modify: `frontend/src/components/ActiveSessionPanel.tsx` (+ teste), `frontend/src/components/HistoryView.tsx`, `frontend/src/styles.css`, `readme.md`

**Interfaces:**
- Consumes: contrato da Task 4.
- Produces:
  - Tipos: `RecallQuestion {id, text, source}`, `RecallGrade = "MISSED" | "PARTIAL" | "RECALLED"`, `RecallAnswer {question_id, answer, grade, useful}`; `ActiveSession.questions`, `ActiveSession.last_to_review`; `NotesInput` ganha `answers?: RecallAnswer[]`; `SessionRecord.recall_test`.
  - `GRADE_LABEL = { MISSED: "Errei", PARTIAL: "Parcial", RECALLED: "Acertei" }`.
  - `<RecallTest questions storageKey onChange(answers: RecallAnswer[] | null, checking: boolean) />`: passo 1 — cada pergunta com `<textarea aria-label={pergunta}>` e botão **"Conferir respostas"**; passo 2 — respostas só leitura, `radiogroup` Errei/Parcial/Acertei por pergunta e botões 👍/👎 (`aria-pressed`). Chama `onChange(answers, true)` quando as 3 têm correção, senão `onChange(null, …)`. Rascunho (respostas, passo, correções) em `localStorage[storageKey]` com try/catch; `storageKey = "recall:" + started_at`.
  - `ActiveSessionPanel`: banner `"🔁 Da última vez você anotou para revisar:"` + texto quando `session.last_to_review`; em revisão com perguntas, `RecallTest` antes de tudo e o `NotebookEditor` **só aparece depois de "Conferir"**; autoavaliação e "Finalizar" ficam desabilitados até as 3 correções; envia `answers` no finish; limpa o `localStorage` ao finalizar/cancelar.
  - `HistoryView`: lista o teste (pergunta, resposta, correção) quando `recall_test` não está vazio.

- [x] **Step 1: Testes que falham:**
  - `RecallTest.test.tsx`: `esconde as correções até conferir`; `só libera quando as 3 têm correção` (verifica `onChange` com 3 itens e grades); `guarda o rascunho e o passo ao recarregar` (desmonta, remonta com o mesmo `storageKey` → respostas e passo voltam); `👍/👎 é opcional`.
  - `ActiveSessionPanel.test.tsx`: `mostra o último "preciso revisar"`; `na revisão o caderno só aparece depois de conferir`; `finalizar envia as respostas do teste` (body do finish tem `answers` com 3 itens); `sessão de estudo não mostra teste`.
- [x] **Step 2:** `cd frontend && npx vitest run` → FAIL nos novos.
- [x] **Step 3:** Implementar; README: linha `| Teste de memória | Toda revisão começa com 3 perguntas respondidas sem consultar; você confere, marca Errei/Parcial/Acertei e só então finaliza. Seu último "preciso revisar" aparece no topo de cada sessão |`.
- [x] **Step 4: Verificação final:** `make check` e `make e2e` → verdes (o e2e existente cobre só estudo; a revisão completa fica coberta por HTTP + Vitest, porque consolidar exige 10 sessões de 25 min reais).
