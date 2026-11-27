# Aquecimento de recuperação — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aquecimento de ~2 min na tela Hoje (2 perguntas sem consultar → conferir → concluir), fora de sessão, sem ponto, mais a "pergunta para o eu do futuro" no fim da sessão de estudo.

**Architecture:** Estado do aquecimento no agregado `StudyPlan` (outbox atômico, ADR-0006), evento `WarmupFinished` consumido pelo histórico. A escolha do conteúdo e do "próximo passo" fica em `planning` (compositor que já usa o `ReviewRecommender`). O front reaproveita `RecallTest`.

**Tech Stack:** Python 3 / FastAPI / pytest-bdd (Gherkin pt) / MongoDB 8.2+ / RabbitMQ 4 (quorum) · React + TanStack Query + Vitest + playwright-bdd.

**Spec:** `docs/specs/2026-11-21-aquecimento-de-recuperacao-design.md` — leia antes de qualquer tarefa.

## Global Constraints

- **Sem commits** neste repo sem pedido explícito do usuário: cada tarefa termina em "checkpoint" (testes verdes), não em `git commit`. Trabalhar numa branch nova `feat/aquecimento-de-recuperacao` criada a partir do HEAD atual.
- Domínio (`learning.domain`, `curriculum.domain`) com **100% de branches** (`make test-unit`).
- Regra de dependência (`make test-arch`): domínio puro; `learning` não importa `planning`/`insights`; só `planning` compõe contextos.
- Toda regra nova de comportamento ganha cenário em Gherkin **pt** (`backend/tests/features/*.feature`).
- Textos de tela exatos (spec): `🔥 Aquecimento · 2 perguntas · ~2 min`, `✅ Aquecimento feito. Bora estudar "{title}"?`, `✅ Aquecimento feito. Bora revisar "{title}"?`, `✅ Aquecimento feito.`, `Iniciar sessão`, `Por hoje é só`, `✅ Aquecimento feito hoje`, `💭 Deixar uma pergunta para o seu eu do futuro (opcional)`, `Sua resposta esperada`, `Esse aquecimento expirou — que tal um novo?`. Nenhum texto de cobrança.
- Valores: 2 perguntas no aquecimento, 3 na revisão; `LEARNER`+`TO_REVIEW` ≤ `count-1`; `TO_REVIEW` ≤ 2; fila de perguntas do aprendiz ≤ 5 (FIFO, descarta a mais antiga); pergunta ≤ 500, resposta esperada ≤ 2 000; expiração 4 h; 1 aquecimento por dia local (data do início).
- `schema_version` 4 → **5**. Evento `warmup_finished` v1, routing key `learning.warmup_finished.v1`.
- Gate final: `make check` (lint, typecheck, test, test-web, test-int) e `make e2e`.

## Review Focus

1. **Iniciar sessão com aquecimento pela metade** (outra aba, ou abandonou): a sessão inicia e o aquecimento some sem registro → teste na Tarefa 2.
2. **Começar 23:58 e concluir 00:02:** conclui e conta para o dia do início; o card não reaparece no dia seguinte por engano → teste na Tarefa 2.
3. **Duplo envio do "Concluir"** (duas abas / duplo clique): o 2º recebe 409 `NoActiveWarmupError` e a tela só recarrega o estado, sem erro assustador → testes nas Tarefas 6 e 7.
4. **Aquecimento inflando estatísticas/retreino:** registros `warmup_finished` fora de `stats` (sessões, minutos, pontos, sequência) e de `labeled_reviews` → teste na Tarefa 5.
5. **Remover o conteúdo** com aquecimento ativo nele: aquecimento descartado, `GET /api/warmup` não quebra → teste na Tarefa 2.

---

### Task 1: Perguntas do aprendiz no domínio

**Files:**
- Modify: `backend/src/developer_myself/learning/domain/value_objects.py`, `learning/domain/content.py`, `learning/domain/study_plan.py` (`finish_session`), `learning/domain/events.py` (`StudySessionFinished`)
- Test: `backend/tests/unit/test_study_plan.py`, `backend/tests/unit/test_value_objects.py`

**Interfaces:**
- Produces:
  - `LEARNER_ANSWER_MAX_LENGTH = 2_000`; `@dataclass(frozen=True, slots=True) class LearnerQuestion: id: uuid.UUID; text: str; created_at: datetime; answer: str | None = None` — texto vazio/só espaços ou > `QUESTION_MAX_LENGTH` → `InvalidValueError`; `answer` > 2 000 → `InvalidValueError`; `answer` só com espaços vira `None`.
  - `RecallQuestion.expected_answer: str | None = None` (campo novo, último).
  - `MAX_LEARNER_QUESTIONS = 5` em `content.py`; `Content.learner_questions: tuple[LearnerQuestion, ...] = ()`; `Content._add_learner_question(q: LearnerQuestion) -> None` (FIFO, corta para os 5 mais novos); `Content._consume_learner_questions(ids: set[uuid.UUID]) -> None`.
  - `StudyPlan.finish_session(notes, now, recall=None, answers=(), future_question: LearnerQuestion | None = None)` — adiciona à fila só em sessão `STUDY` não expirada (pontuada ou não); em `REVIEW`, consome as `LearnerQuestion` cujos ids aparecem em perguntas `source=LEARNER` da sessão.
  - `StudySessionFinished.future_question: dict[str, object] | None = None` (`{"id", "text", "answer"}`).
  - Mensagem de `_graded_test` passa a usar o número real: `f"Responda e corrija as {len(questions)} perguntas do teste antes de finalizar."`

- [ ] **Step 1: Testes que falham** em `test_study_plan.py`:
  - `test_study_session_keeps_future_question`: estudo de 25 min com `future_question` → `content.learner_questions[-1].text == "O que é CQS?"` e evento `StudySessionFinished.future_question["text"] == "O que é CQS?"`.
  - `test_unscored_study_still_keeps_future_question` (24 min) → fila tem 1.
  - `test_review_ignores_future_question` → fila continua vazia.
  - `test_learner_questions_keep_only_five_newest`: 6 sessões com perguntas "q1".."q6" → textos `("q2", …, "q6")`.
  - `test_review_consumes_learner_questions_it_asked`: revisão com `RecallQuestion(id=lq.id, source=LEARNER, …)` respondida → `lq` sai da fila; outra pergunta do aprendiz fica.
  - `test_value_objects.py`: `LearnerQuestion` vazia, 501 chars, resposta com 2 001 chars → `InvalidValueError`; resposta `"  "` → `None`.
- [ ] **Step 2:** `cd backend && poetry run pytest tests/unit/test_study_plan.py tests/unit/test_value_objects.py -q` → FAIL (nomes não existem).
- [ ] **Step 3:** Implementar as interfaces acima.
- [ ] **Step 4:** Mesmo comando → PASS; `make test-unit` → 100% de branches.
- [ ] **Step 5: Checkpoint** (sem commit).

### Task 2: Aquecimento no agregado

**Files:**
- Modify: `learning/domain/study_plan.py`, `learning/domain/errors.py`, `learning/domain/events.py`
- Test: `backend/tests/unit/test_warmup.py` (novo)

**Interfaces:**
- Consumes: Tarefa 1 (`LearnerQuestion`, `_consume_learner_questions`).
- Produces:
  - Erros: `WarmupAlreadyDoneError(DomainError)` (→ 409), `NoActiveWarmupError(DomainError)` (→ 409), `NothingToWarmUpError(InvalidValueError)` (→ 422). O mapeamento HTTP já é automático por herança (`composition/container.py:_install_error_handlers`).
  - `WARMUP_EXPIRY = SESSION_EXPIRY` (4 h).
  - `@dataclass(frozen=True, slots=True) class ActiveWarmup: content_id: ContentId; started_at: datetime; questions: tuple[RecallQuestion, ...]`
  - Campos `StudyPlan.active_warmup: ActiveWarmup | None = None`, `StudyPlan.last_warmup_on: date | None = None`.
  - `StudyPlan.can_warm_up(content: Content) -> bool` — `content.session_kind is not None and content.session_count > 0`.
  - `StudyPlan.warmed_up_today(now: datetime) -> bool`
  - `StudyPlan.current_warmup(now: datetime) -> ActiveWarmup | None` — consulta pura: `None` se ausente ou com mais de 4 h.
  - `StudyPlan.start_warmup(content_id: ContentId, questions: tuple[RecallQuestion, ...], now: datetime) -> ActiveWarmup` — ordem: descarta o vencido; ativo existente → devolve o mesmo (ignora `questions`); sessão ativa → `SessionAlreadyActiveError`; feito hoje → `WarmupAlreadyDoneError`; não elegível → `NothingToWarmUpError`. Não registra evento.
  - `StudyPlan.finish_warmup(answers: tuple[RecallAnswer, ...], now: datetime) -> ContentId` — sem ativo ou vencido → `NoActiveWarmupError` (e limpa o vencido); valida com `_graded_test`; `last_warmup_on = local_date(started_at)`; consome perguntas `LEARNER`; registra `WarmupFinished`; devolve o `content_id`.
  - `StudyPlan.cancel_warmup(now: datetime) -> None` — sem ativo → `NoActiveWarmupError`; limpa sem evento.
  - `start_session` limpa `active_warmup` ao iniciar com sucesso; `remove_content` limpa se o aquecimento for daquele conteúdo.
  - Evento `@dataclass(frozen=True, slots=True, kw_only=True) class WarmupFinished(DomainEvent): content_id: uuid.UUID; content_title: str; started_at: datetime; finished_at: datetime; duration_seconds: int; recall_test: tuple[dict[str, object], ...]` (`type_name()` → `"warmup_finished"`).

- [ ] **Step 1: Testes que falham** em `test_warmup.py` (um por linha, com o estado montado pelos helpers de `test_study_plan.py`):
  - `test_start_returns_given_questions` / `test_start_again_returns_same_warmup` (perguntas novas ignoradas)
  - `test_start_refused_with_active_session` → `SessionAlreadyActiveError`
  - `test_start_refused_after_done_today` → `WarmupAlreadyDoneError`; `test_next_local_day_allows_again`
  - `test_content_without_finished_session_is_not_eligible` / `test_locked_content_is_not_eligible` → `NothingToWarmUpError`
  - `test_finish_requires_every_answer` → `RecallTestRequiredError` com "2 perguntas"
  - `test_finish_records_event_and_awards_nothing`: `WarmupFinished.recall_test` com 2 itens, `points` inalterado, nenhum `PointAwarded`
  - `test_finish_consumes_learner_question`
  - `test_finish_across_midnight_counts_for_start_day` (Review Focus 2): início 23:58 local, fim 00:02 → `last_warmup_on` = dia do início; `warmed_up_today` no dia seguinte é `False`
  - `test_finish_after_4h_raises_and_clears` → `NoActiveWarmupError`, `active_warmup is None`
  - `test_cancel_clears_without_event` / `test_cancel_without_warmup_raises`
  - `test_start_session_discards_active_warmup` (Review Focus 1): sem evento de aquecimento
  - `test_remove_content_discards_its_warmup` (Review Focus 5)
- [ ] **Step 2:** `poetry run pytest tests/unit/test_warmup.py -q` → FAIL.
- [ ] **Step 3:** Implementar as interfaces.
- [ ] **Step 4:** `make test-unit` → PASS com 100% de branches.
- [ ] **Step 5: Checkpoint.**

### Task 3: Escolha das perguntas com `count` e origem `LEARNER`

**Files:**
- Modify: `learning/application/questions.py`, `learning/adapters/curriculum/question_picker.py`
- Test: `backend/tests/unit/test_review_questions.py`

**Interfaces:**
- Produces: `QuestionPicker.pick(plan, content, now, count: int = 3) -> tuple[RecallQuestion, ...]`; `QUESTIONS_PER_REVIEW = 3`, `QUESTIONS_PER_WARMUP = 2` (em `question_picker.py`); template `"learner_question": "{}"`. Perguntas `LEARNER` usam `id=lq.id`, `topic=None`, `expected_answer=lq.answer`, em ordem de criação (mais antiga primeiro). Limite conjunto: `LEARNER` + `TO_REVIEW` ≤ `count - 1`; `TO_REVIEW` ≤ `MAX_FROM_TO_REVIEW` (2).

- [ ] **Step 1: Testes que falham:**
  - `test_warmup_has_two_questions`
  - `test_learner_question_comes_first_with_expected_answer`
  - `test_warmup_keeps_one_slot_for_topics`: 2 perguntas do aprendiz + "preciso revisar" → 1 `LEARNER` + 1 `SPACED_TOPIC`/`TOPIC`
  - `test_review_takes_at_most_two_from_learner_and_to_review`: 3 do aprendiz → 2 `LEARNER` + 1 tópico
  - Os testes atuais de revisão sem perguntas do aprendiz seguem passando sem mudança.
- [ ] **Step 2:** `poetry run pytest tests/unit/test_review_questions.py -q` → FAIL.
- [ ] **Step 3:** Implementar (quem chama sem `count` continua com 3).
- [ ] **Step 4:** PASS + `make typecheck`.
- [ ] **Step 5: Checkpoint.**

### Task 4: Casos de uso, escolha do conteúdo e BDD

**Files:**
- Modify: `learning/application/use_cases.py` (`FinishSession`, `LearningUseCases`, novos casos de uso)
- Create: `planning/application/warmup.py`
- Create: `backend/tests/features/aquecimento.feature`, `backend/tests/features/test_aquecimento.py`
- Modify: `backend/tests/features/teste_de_memoria.feature`, `test_teste_de_memoria.py`, `conftest.py` (World: `question_picker` já injetado; adicionar helpers de aquecimento)

**Interfaces:**
- Consumes: Tarefas 1–3.
- Produces:
  - `@dataclass(frozen=True, slots=True) class FutureQuestionInput: text: str; answer: str | None = None`
  - `FinishSession.__call__(learner_id, notes, recall_rating=None, answers=None, future_question: FutureQuestionInput | None = None)` — cria `LearnerQuestion(id=uuid.uuid7(), created_at=clock.now(), …)`.
  - `StartWarmup(_UseCase)` com `question_picker: QuestionPicker | None = None`; `__call__(learner_id: uuid.UUID, content_id: uuid.UUID) -> ActiveWarmup` — se `plan.current_warmup(now)` existe, devolve sem chamar o picker nem salvar; senão `pick(..., count=QUESTIONS_PER_WARMUP)` (`()` sem picker) → `start_warmup` → salva.
  - `FinishWarmup.__call__(learner_id, answers: list[AnswerInput]) -> ContentId`; `CancelWarmup.__call__(learner_id) -> None`. Quando o domínio limpa um vencido antes de levantar o erro, salvar antes de relançar (mesmo padrão de `StartSession`).
  - `LearningUseCases` ganha `start_warmup`, `finish_warmup`, `cancel_warmup` (o `build` passa `question_picker` para `StartWarmup`).
  - Em `planning/application/warmup.py`:
    - `warmup_target(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> Content | None` — em andamento elegível com `last_session_at` mais recente; senão o 1º elegível do ranking de revisões do `daily_plan` (consolidado, < 30 pontos, por menor chance de lembrar).
    - `@dataclass(frozen=True, slots=True) class NextStep: content_id: str; title: str; kind: SessionKind`
    - `next_step(plan, recommender, now) -> NextStep | None` — `plan.requires_review(now) and not plan.reviewed_today(now)` → 1ª revisão do `daily_plan`; senão 1º estudo; senão 1ª revisão; senão `None`.
    - `@dataclass(frozen=True, slots=True) class WarmupStatus: available: bool; done_today: bool; target: Content | None; active: ActiveWarmup | None`
    - `warmup_status(plan, recommender, now) -> WarmupStatus` — `available = target is not None and not done_today and plan.active_session is None`.

- [ ] **Step 1: Cenários que falham** em `aquecimento.feature` (pt), cada um um `Cenário`:
  - Conteúdo estudado ao menos uma vez oferece aquecimento com 2 perguntas
  - Conteúdo nunca estudado não oferece aquecimento
  - Sem nada em andamento, o consolidado com menor chance de lembrar é aquecido
  - A pergunta do eu do futuro vem primeiro
  - Recarregar devolve as mesmas perguntas
  - Concluir sem corrigir é recusado
  - Concluir não dá ponto e registra o aquecimento no histórico
  - Só um aquecimento por dia
  - Com sessão ativa não há aquecimento
  - Cancelar não registra nada
  - Depois do aquecimento, o próximo passo é a revisão pendente (com "DDD" consolidado e "Clean Code" em andamento, `next_step` → revisar "DDD")

  Em `teste_de_memoria.feature`: "A pergunta do eu do futuro entra na revisão" e "A pergunta usada sai da fila".
- [ ] **Step 2:** `poetry run pytest tests/features -q` → FAIL nos cenários novos.
- [ ] **Step 3:** Implementar casos de uso, `planning/application/warmup.py` e steps.
- [ ] **Step 4:** `make test-bdd test-unit test-arch` → PASS.
- [ ] **Step 5: Checkpoint.**

### Task 5: Persistência Mongo v5, evento no RabbitMQ e histórico

**Files:**
- Modify: `learning/adapters/mongo/repository.py` (`SCHEMA_VERSION = 5`, `_v4_to_v5`, `to_document`/`from_document`), `learning/adapters/memory/repository.py` (se copiar campos explicitamente), `shared/adapters/mongo_setup.py` (`$jsonSchema`), `learning/adapters/rabbitmq/topology.py` (binding), `insights/application/history.py`
- Test: `backend/tests/integration/test_study_plan_repository_contract.py`, `test_mongo_specifics.py`, `test_events_end_to_end.py`, `test_history_store_contract.py`, `backend/tests/unit/test_session_record.py`

**Interfaces:**
- Produces:
  - Documento: `active_warmup: {content_id, started_at, questions: [...]} | null`, `last_warmup_on: "YYYY-MM-DD" | null`, `contents[].learner_questions: [{id, text, answer, created_at}]`, `questions[].expected_answer`. `_v4_to_v5` preenche os padrões (incl. `expected_answer: None` em `active_session.questions`).
  - `SESSION_HISTORY.bindings` ganha `"learning.warmup_finished.v1"`.
  - `SessionRecord.from_envelope` aceita `type == "warmup_finished"` → `kind="WARMUP"`, `awarded=False`, `reason=None`, notas `""`, `level_after=None`, `recall_test` do payload.
  - `HistoryQueries.stats` já filtra `type == "study_session_finished"`; `is_labeled_review` exige esse tipo → só travar com testes.

- [ ] **Step 1: Testes que falham:**
  - Contrato: plano com aquecimento ativo, `last_warmup_on` e perguntas do aprendiz sobrevive a `save`/`get` (memória e Mongo).
  - `test_mongo_specifics`: documento v4 cru → upcast v5 com os padrões; validador aceita o documento v5.
  - `test_session_record.py::test_warmup_envelope_becomes_warmup_record`.
  - `test_history_store_contract`/unit de `HistoryQueries`: `test_stats_ignore_warmups` e `test_labeled_reviews_ignore_warmups` (Review Focus 4).
  - `test_events_end_to_end`: concluir aquecimento → registro `WARMUP` no histórico pelo relay + consumer.
- [ ] **Step 2:** `poetry run pytest tests/unit/test_session_record.py -q` → FAIL; `make test-int` (Docker, mongo:8.2+) → FAIL nos novos.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `make test test-int` → PASS.
- [ ] **Step 5: Checkpoint.**

### Task 6: API HTTP

**Files:**
- Create: `planning/adapters/http/warmup_routes.py` (montar como `schedule_routes`, mesmo prefixo `/api` e rate limit)
- Modify: `learning/adapters/http/schemas.py` (`QuestionOut.expected_answer`, `FutureQuestionIn`, `FinishSessionIn.future_question`), `learning/adapters/http/routes.py` (repassar `future_question`), registro do router no app
- Test: `backend/tests/http/test_warmup_api.py` (novo), `backend/tests/http/test_api.py`

**Interfaces:**
- Consumes: Tarefa 4 (`warmup_status`, `next_step`, `StartWarmup`, `FinishWarmup`, `CancelWarmup`).
- Produces (JSON):
  - `GET /api/warmup` → `{available, done_today, content: {id, title} | null, active: {started_at, questions: QuestionOut[]} | null}`
  - `POST /api/warmup` (sem corpo; usa `warmup_target`) → `201` com `{started_at, questions}`; sem alvo → `422` `NothingToWarmUpError`
  - `POST /api/warmup/finish` `{answers: AnswerIn[] (max 10)}` → `200 {next: {content_id, title, kind} | null}`
  - `DELETE /api/warmup` → `204`
  - `FutureQuestionIn {text: str (1..500), answer: str | null (≤ 2000)}`

- [ ] **Step 1: Testes que falham** em `test_warmup_api.py`: fluxo completo GET → POST → finish → GET (`done_today: true`, `available: false`); POST repetido devolve as mesmas perguntas; finish sem respostas → 422; **finish duas vezes → 2º 409 com `code: "NoActiveWarmupError"`** (Review Focus 3); DELETE → 204, depois finish → 409; sem login → 401. Em `test_api.py`: `future_question` aceito no finish da sessão e devolvido como `expected_answer` na próxima revisão.
- [ ] **Step 2:** `make test-http` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `make test-http test-arch typecheck` → PASS.
- [ ] **Step 5: Checkpoint.**

### Task 7: Front — card, painel e pergunta do eu do futuro

**Files:**
- Modify: `frontend/src/api/types.ts`, `api/client.ts`, `api/hooks.ts`, `features/session/RecallTest.tsx` (mostra `Sua resposta esperada` no passo conferir), `features/session/SessionPanel.tsx` (campo opcional só em estudo), `features/progress/SessionHistory.tsx` + `api/labels.ts` (`WARMUP` → "Aquecimento"), `pages/TodayPage.tsx`
- Create: `frontend/src/features/warmup/WarmupCard.tsx`, `WarmupPanel.tsx`, + `*.test.tsx`

**Interfaces:**
- Consumes: Tarefa 6 (JSON acima).
- Produces: `api.warmup()`, `api.startWarmup()`, `api.finishWarmup(answers: RecallAnswer[])`, `api.cancelWarmup()`; `keys.warmup`; hooks `useWarmup`, `useStartWarmup`, `useFinishWarmup`, `useCancelWarmup` (concluir/cancelar invalidam `warmup`, `plan`, `today`, `history`; `useFinishSession` também invalida `warmup`). `NotesInput.future_question?: {text: string; answer?: string | null} | null`. `RecallQuestion.expected_answer?: string | null`.
- Comportamento: `TodayPage` mostra o card **acima** do próximo passo quando `available`, sem sessão ativa e sem onboarding; com `done_today` mostra a linha discreta. `WarmupPanel` usa `RecallTest` com `storageKey = "warmup:" + started_at`; conclusão com os textos exatos e os botões; [Iniciar sessão] chama `useStartSession(next.content_id)`. Resposta 409 ao concluir → `clearRecallDraft`, toast `Esse aquecimento expirou — que tal um novo?` e refetch.

- [ ] **Step 1: Testes que falham (Vitest):**
  - `WarmupCard`: texto `🔥 Aquecimento · 2 perguntas · ~2 min` quando `available`; nada quando `!available && !done_today`; `✅ Aquecimento feito hoje` quando `done_today`.
  - `WarmupPanel`: esconde a resposta esperada até conferir; "Concluir" só habilita com 2 correções; conclusão com `kind: "REVIEW"` mostra `Bora revisar "DDD"?`; com `next: null` não mostra [Iniciar sessão]; 409 limpa o rascunho e mostra a mensagem de expirado (Review Focus 3).
  - `SessionPanel`: bloco `💭 Deixar uma pergunta…` só em estudo, recolhido; ao preencher, `finishSession` recebe `future_question`.
  - `TodayPage`: card aparece acima do `NextStepCard`; some com sessão ativa.
- [ ] **Step 2:** `make test-web` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `make test-web lint typecheck` → PASS.
- [ ] **Step 5: Checkpoint.**

### Task 8: E2E, README e fechamento

**Files:**
- Modify: `frontend/e2e/features/jornada.feature`, `frontend/e2e/steps/jornada.steps.ts`, `readme.md` (linha "Aquecimento" e "Pergunta do eu do futuro" na tabela de regras)

- [ ] **Step 1: Cenário e2e que falha:** adicionar "Clean Code" → sessão curta de estudo finalizada com pergunta do eu do futuro (sessão curta não pontua, mas conta como estudada; o e2e não controla o relógio) → card de aquecimento aparece → a pergunta escrita é a 1ª → corrigir as 2 e concluir → "Iniciar sessão" abre a sessão de "Clean Code".
- [ ] **Step 2:** `make e2e` → FAIL.
- [ ] **Step 3:** Implementar steps; atualizar o README.
- [ ] **Step 4:** `make check` e `make e2e` → PASS.
- [ ] **Step 5: Checkpoint final** — reportar ao usuário; commit/PR só se ele pedir.
