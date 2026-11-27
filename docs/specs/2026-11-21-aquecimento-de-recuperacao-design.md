# Aquecimento de recuperação — design (entrega 1 de 3)

**Data:** 2026-11-21 · **Status:** aprovado

## Intenção e porquê

O aprendiz relatou dois problemas no uso real:

1. **Estuda e esquece.** Hoje o teste de memória só existe em **revisão**, e só se revisa conteúdo **consolidado** (≈ dia 10). Nos primeiros dias de um conteúdo — quando a curva do esquecimento é mais íngreme — não há nenhuma tentativa de lembrar.
2. **Abre o app e não começa.** O primeiro passo possível é uma sessão de no mínimo 25 min com 3 anotações (às vezes precedida de uma revisão obrigatória). A barreira de entrada é alta.

Esta entrega cria o **aquecimento**: uma ação própria de ~2 minutos na tela Hoje — 2 perguntas respondidas sem consultar, depois conferidas — que pode ser feita **sem abrir uma sessão**. Ela junta duas ideias:

- **Psicologia do aprendizado:** prática de recuperação desde o dia 1 e efeito de geração (o aprendiz escreve perguntas para o "eu do futuro").
- **Psicologia comportamental:** reduzir o atrito do primeiro passo (o menor comportamento possível que ainda conta), com uma deixa para continuar ("Bora estudar X?") sem punir quem para ali.

Também alimenta a **entrega 2 (painel de evidências)**: o aprendiz disse que só sente evolução quando "consegue explicar sem consultar ou resolver um problema sozinho". Cada aquecimento corrigido é uma dessas evidências.

## Roteiro (atualiza o da spec 2026-11-17)

O plano novo passa na frente do roteiro antigo (decisão do aprendiz):

1. **Aquecimento de recuperação** — esta spec.
2. **Painel de evidências** — "você vs. você há 30 dias": % explicado sem consultar (aquecimento + revisão), desafios resolvidos, provas pontuais ("acertou X, que errou em 3/out"). Sem ranking nem comparação com outras pessoas.
3. **Sessão curta não zera** — sessão < 25 min registra tempo e conta como presença, sem dar ponto.

Depois, continuam valendo as etapas pendentes do roteiro antigo: perguntas do caderno (pares pergunta/resposta — esta entrega já cobre uma versão leve), FSRS, pontos ligados a resultado, desafios com critério, duração pela profundidade, painel de lacunas.

## Objetivos

1. Na tela **Hoje**, um card **🔥 Aquecimento · 2 perguntas · ~2 min** aparece quando há material para perguntar e o aquecimento do dia ainda não foi feito.
2. O aquecimento tem os mesmos passos do teste da revisão: **responder sem consultar → conferir (Errei / Parcial / Acertei, 👍/👎 opcional) → concluir**.
3. Ao concluir: **"✅ Aquecimento feito. Bora estudar "{conteúdo}"?"** com **[Iniciar sessão]** e **[Por hoje é só]**. Parar ali é um desfecho válido, sem mensagem de culpa.
4. No fim de uma **sessão de estudo**, campo **opcional** "Pergunta para o seu eu do futuro" (+ resposta esperada opcional). Essas perguntas têm **prioridade** no próximo aquecimento ou revisão da matéria.
5. Cada aquecimento concluído gera um evento e vai para o histórico, com o mesmo formato de item de teste da revisão (dataset da IA e base do painel da entrega 2).

## Não-objetivos

- Dar **ponto**, XP ou mexer em nível/ferrugem. O aquecimento não pontua.
- Substituir a **revisão obrigatória** do dia (Regra 2 continua igual).
- Teste de memória dentro da sessão de **estudo** (a sessão segue como hoje).
- Sequência de dias (*streak*), lembretes/notificações, painel de evidências (entrega 2), sessão curta (entrega 3).
- FSRS ou IA escolhendo perguntas: a escolha continua por regra fixa atrás do port `QuestionPicker`.

## Anti-objetivos

- Qualquer coisa que faça o aquecimento parecer **obrigação** ou **punição** (bloquear sessão sem aquecimento, mensagem de "você não aqueceu", contador vermelho).
- Mostrar material antes de responder.
- Perder respostas digitadas ao recarregar.
- Aquecimento que leve mais que ~2–3 min (mais perguntas, campos obrigatórios extras).

## Abordagens consideradas

| | |
|---|---|
| **1. Aquecimento separado, fora de sessão** ✅ escolhida pelo aprendiz | Ação própria na tela Hoje, sem compromisso de 25 min. Ataca o "abro e não começo". Custo: conceito novo no domínio (tentativa de recuperação fora de sessão), com evento e histórico próprios. |
| 2. Aquecimento dentro da sessão de estudo | Reaproveita quase todo o código do teste da revisão, mas o primeiro passo continua sendo a sessão de 25 min — não resolve o "não começo". |
| 3. Só no front, sem servidor | Mais rápido, mas perguntas e respostas ficariam fora do histórico/eventos: sem dados para o painel (entrega 2) nem para a IA. |

Dentro da opção 1, o estado do aquecimento fica **no agregado `StudyPlan`** (como a sessão ativa e o teste da revisão), para gravar estado + evento na mesma escrita atômica do outbox (ADR-0006) e manter as perguntas fixas ao recarregar.

## Design

### Domínio (`learning`)

- **`ActiveWarmup`** (value object, no `StudyPlan`): `content_id`, `started_at`, `questions: tuple[RecallQuestion, ...]` (2 itens).
- **`StudyPlan.active_warmup: ActiveWarmup | None`** e **`last_warmup_on: date | None`** (data local do aprendiz).
- **`start_warmup(content_id, questions, now)`**:
  - recusa se já existe sessão ativa (`SessionAlreadyActiveError`, reaproveitado) — aquecer é antes de estudar;
  - recusa se o aquecimento de hoje já foi feito (`WarmupAlreadyDoneError`, 409);
  - se já existe aquecimento ativo, **devolve o mesmo** (idempotente: recarregar não troca perguntas);
  - recusa conteúdo não elegível (`NothingToWarmUpError`, 422): elegível = tem sessão possível (`session_kind` não é `None`) **e** pelo menos 1 sessão finalizada.
- **`finish_warmup(answers, now)`**: exige uma resposta corrigida por pergunta (mesma validação de `_graded_test` da revisão → `RecallTestRequiredError`). Grava `last_warmup_on` = **data local do início** do aquecimento, limpa `active_warmup`, consome as perguntas do aprendiz usadas (ver abaixo) e registra **`WarmupFinished`**. Sem aquecimento ativo (ou expirado) → `NoActiveWarmupError` (409).
- **`cancel_warmup(now)`**: limpa sem registrar nada (como cancelar sessão).
- **Expiração:** só por tempo — aquecimento ativo há **mais de 4 h** é descartado em silêncio (sem evento). Virar a meia-noite no meio **não** expira: o aquecimento conta para o dia em que começou.
- **Iniciar sessão com aquecimento ativo:** a sessão inicia normalmente e o aquecimento é **descartado em silêncio** (nunca bloquear estudo por causa do aquecimento).
- **Remover o conteúdo** de um aquecimento ativo descarta o aquecimento.
- **Qual conteúdo o aquecimento usa** — decidido em `planning` (composição), não no domínio, porque o ranking usa o `ReviewRecommender`:
  1. o conteúdo **em andamento** elegível com sessão mais recente;
  2. senão, entre os **consolidados com menos de 30 pontos** (mesmo filtro e ranking do `daily_plan`, ou seja, da lista de revisões da tela Hoje), o de **menor chance de lembrar** que seja elegível;
  3. senão, nenhum → o card não aparece.
  O domínio só garante a elegibilidade.

### Perguntas do aprendiz ("eu do futuro")

- **`LearnerQuestion`** (value object): `id`, `text` (≤ 500, obrigatória), `answer` (≤ 2 000, opcional), `created_at`.
- **`Content.learner_questions: tuple[LearnerQuestion, ...]`** — fila FIFO, **máximo 5** (a 6ª descarta a mais antiga).
- **`finish_session(..., future_question=None)`**: em sessão de **estudo** finalizada (pontuada ou não), se veio pergunta, entra na fila. Revisão não pede (já tem teste).
- Quando uma pergunta do aprendiz é **usada** num aquecimento ou revisão **concluídos**, ela sai da fila. A correção fica no histórico; se errou, o aprendiz tende a anotar em "preciso revisar", que já volta como pergunta.
- Na conferência, se a pergunta tem `answer`, ela aparece como **"Sua resposta esperada"** ao lado da resposta dada.

### Escolha das perguntas

- `QuestionPicker.pick` ganha `count: int` (revisão = 3, aquecimento = 2). `RuleQuestionPicker` passa a respeitar `count`.
- Nova origem no topo da ordem: **`LEARNER`** (já reservada no enum), modelo `learner_question`, texto exatamente como o aprendiz escreveu; o `id` da `RecallQuestion` é o `id` da `LearnerQuestion`.
- Ordem completa: `LEARNER` → `TO_REVIEW` → `SPACED_TOPIC` (warmup do cronograma: 1, 3, 7 dias) → `TOPIC`. Mantém o "sem repetir texto".
- **Vaga garantida:** `LEARNER` + `TO_REVIEW` juntos ocupam no máximo `count - 1` vagas (aquecimento: 1; revisão: 2), e `TO_REVIEW` continua com teto 2. Sempre sobra ao menos 1 vaga para `SPACED_TOPIC`/`TOPIC`. Na revisão sem perguntas do aprendiz, o comportamento atual não muda.
- `RecallQuestion` ganha `expected_answer: str | None` (só preenchido para `LEARNER`).

### Evento

- **`WarmupFinished`** (v1): `content_id`, `content_title`, `started_at`, `finished_at`, `duration_seconds`, `recall_test` (mesmo formato de item que `StudySessionFinished.recall_test`: `question_id, text, source, template, topic, position, answer, grade, useful`).
- Routing key `learning.warmup_finished.v1`. A fila `insights.session-history` passa a assinar também essa chave.
- `StudySessionFinished` ganha `future_question: dict | None = None` (aditivo, mesma versão).

### Persistência

- Mongo `study_plans`: `schema_version` 4 → **5** com upcaster lazy (`active_warmup: None`, `last_warmup_on: None`, `learner_questions: []` em cada conteúdo). Validador `$jsonSchema` aceita os campos novos. O `scripts/deploy.sh` já faz backup quando o schema sobe.
- Histórico (`insights`): novo tipo de registro `warmup` ao lado das sessões (mesma coleção, campo `kind: "warmup"`), com `recall_test`. Listagem de histórico mostra os dois.

### HTTP

- `GET /api/warmup` → `{ available: bool, done_today: bool, content: {id, title} | null, active: {questions, started_at} | null }`.
- `POST /api/warmup` → inicia (ou devolve o ativo); `201` com as perguntas.
- `POST /api/warmup/finish` → `{ answers: [{question_id, answer, grade, useful}] }`; `200` com `{ next: {content_id, title, kind: "STUDY" | "REVIEW"} | null }`. O `next` é **o mesmo próximo passo que a tela Hoje sugeriria** (`dayItems`): revisões antes de estudos, pulando o que já foi feito hoje (conteúdo com sessão hoje, ou revisão do dia já feita); `null` se não sobrar nada. Assim "Iniciar sessão" nunca leva a um estudo que não pontua por `NO_REVIEW`.
- `available` do `GET` é `false` enquanto houver sessão ativa.
- `DELETE /api/warmup` → cancela.
- `FinishSessionIn` ganha `future_question: { text, answer? } | null`.
- Rate limit igual às demais rotas autenticadas.

### Tela

- **Hoje:** card do aquecimento **no topo**, acima de revisões e estudo, só quando `available && !done_today`. Depois de feito, vira uma linha discreta "✅ Aquecimento feito hoje".
- **Painel do aquecimento:** mesmos três passos e componentes do teste da revisão (reaproveitar). Rascunho das respostas no `localStorage` (chave = `started_at`), limpo ao concluir/cancelar.
- **Conclusão:** mensagem positiva + **[Iniciar sessão]** (abre a sessão do `next`) e **[Por hoje é só]** (fecha o painel). Texto: **"✅ Aquecimento feito. Bora estudar "{title}"?"** quando `kind` = `STUDY`, **"✅ Aquecimento feito. Bora revisar "{title}"?"** quando `REVIEW`, e só **"✅ Aquecimento feito."** (sem [Iniciar sessão]) quando `next` é `null`. Nenhum texto de cobrança.
- **Concluir depois de expirado (> 4 h):** a API responde 409; a tela apaga o rascunho, avisa "Esse aquecimento expirou — que tal um novo?" e volta ao card.
- **Histórico e estatísticas:** o aquecimento aparece no histórico como "Aquecimento", mas **não** entra nas estatísticas de sessões/minutos/pontos/sequência nem no dataset de retreino da rede (só registros `study_session_finished` entram, como hoje).
- **Fim da sessão de estudo:** abaixo das 3 anotações, bloco recolhido "💭 Deixar uma pergunta para o seu eu do futuro (opcional)" com pergunta + resposta esperada.

### Testes

- BDD novo `aquecimento.feature` (pt): card disponível só com material e sem aquecimento hoje; 2 perguntas; pergunta do aprendiz vem primeiro; recarregar devolve as mesmas perguntas; concluir exige correções; concluir não dá ponto; um por dia; não inicia com sessão ativa; conteúdo sem sessão não aquece; consolidado com menor chance quando não há em andamento; cancelar não registra; evento carrega o teste.
- BDD `teste_de_memoria.feature`: pergunta do aprendiz entra na revisão (máx. 2) e sai da fila ao concluir.
- Unit do domínio (100% de branches), contrato do Mongo com upcaster v4→v5, HTTP, consumer do histórico, Vitest (card, painel, conclusão, pergunta do eu do futuro), e2e de um aquecimento seguido de "Iniciar sessão".

## Decisões que tomei (pode corrigir)

- **2 perguntas**, no máximo 1 escrita pelo aprendiz.
- **1 aquecimento por dia** (dia local). Mais que isso vira estudo disfarçado e dilui o sinal do painel.
- **Sem ponto** pelo aquecimento.
- **Pergunta do eu do futuro opcional**, só em sessão de estudo, fila de no máximo 5; sai da fila quando usada.
- Card **no topo** da tela Hoje (é o primeiro passo).
- Aquecimento **não pode** acontecer com sessão ativa; já **iniciar sessão** com aquecimento ativo descarta o aquecimento em silêncio.
- Expirar/cancelar **não registra** nada. Expira só por tempo (4 h); conta para o dia em que começou.
- Conteúdo do aquecimento escolhido em `planning` com o mesmo filtro/ranking das revisões da tela Hoje (consolidado com < 30 pontos); concluídos não aquecem.
- "Bora estudar/revisar?" segue o próximo passo da tela Hoje (revisão primeiro, se exigida).
- `LEARNER` + `TO_REVIEW` ≤ `count - 1`: sempre sobra 1 vaga para tópico.
- Aquecimento fora das estatísticas e do retreino.

## O que fica para quem construir

Nomes internos, layout fino do card e do painel, texto exato das mensagens (desde que sem tom de cobrança), formato interno do registro de histórico (desde que traga os campos listados).
