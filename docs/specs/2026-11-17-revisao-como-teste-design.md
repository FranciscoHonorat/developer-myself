# Revisão como teste de memória — design (etapa 1 de 7)

**Data:** 2026-11-17 · **Status:** aprovado

## Intenção e porquê

Hoje uma "revisão" é uma sessão de 25 min igual às outras. A nota "quanto você lembrava?" (1 a 4) é uma autoavaliação sem teste antes, e essa nota é o rótulo que treina a rede neural. A ciência do aprendizado mostra que **tentar lembrar** (prática de recuperação) é o que fixa o conhecimento, e que a autoavaliação sem teste superestima o que sabemos.

Esta etapa faz **toda revisão começar com um teste curto de memória** e traz de volta o "preciso revisar" que o aprendiz escreve. É também a **fundação de dados da IA própria do projeto**: cada pergunta feita, respondida e corrigida vira exemplo de treino para os modelos que, nas próximas etapas, vão **escolher** a melhor pergunta (degrau 1) e **montar** perguntas por modelos de frase (degrau 2). Tudo será construído do zero, em Python puro, como o MLP que já existe.

Roteiro das etapas (cada uma com seu próprio design): 1) **esta**; 2) caderno gera perguntas (pares pergunta/resposta escritos pelo aprendiz); 3) revisão espaçada desde o dia 1 + FSRS; 4) pontos ligados a resultado; 5) desafios com critério; 6) duração pela profundidade; 7) painel de lacunas.

## Objetivos

1. Toda sessão de **revisão** (conteúdo consolidado ou concluído) começa com **3 perguntas**, respondidas **sem consultar** (o caderno e as anotações ficam escondidos até conferir).
2. Depois de responder, o aprendiz **confere** (vê o caderno e o último "preciso revisar") e corrige cada resposta: **Errei / Parcial / Acertei**, mais um **👍/👎 opcional** ("a pergunta foi útil?").
3. **A revisão só pode ser finalizada com as 3 perguntas corrigidas.** Errar não tira ponto; só não dá para pular.
4. A nota 1 a 4 continua obrigatória na revisão, mas passa a ser pedida **depois** do teste.
5. Em **qualquer** sessão (estudo ou revisão), o **último "preciso revisar"** da matéria aparece no topo.
6. Cada pergunta respondida é registrada com: texto, origem, modelo de frase usado, resposta, correção, utilidade, posição — no evento de fim de sessão e no histórico (dataset da IA).

## Não-objetivos

- Perguntas escritas pelo aprendiz no caderno (etapa 2). Nesta etapa a origem "aprendiz" ainda não existe, mas o modelo de dados já a prevê.
- IA escolhendo/montando perguntas (degraus 1 e 2): aqui a escolha é por **regra fixa**, atrás de um port que a IA vai implementar depois.
- Teste em sessões de **estudo** (dias 1–10) — revisão espaçada é a etapa 3.
- Mudar pontos, níveis, ferrugem ou as features/treino da rede neural atual.
- IA externa (API) — descartada pelo usuário.

## Anti-objetivos

- Mostrar o material antes de o aprendiz responder (anula o teste).
- Perder as respostas digitadas ao recarregar a página no meio do teste.
- Quebrar sessões que já estavam abertas quando a mudança entrar no ar.

## Abordagens consideradas

| | |
|---|---|
| **A. Teste dentro da sessão, no `StudyPlan`** ✅ escolhida | Perguntas escolhidas no servidor ao **iniciar** a revisão e guardadas na `ActiveSession`; respostas enviadas ao **finalizar**; "sem teste não finaliza" é regra do domínio (BDD); os dados seguem no `StudySessionFinished` pelo caminho de eventos que já alimenta a IA. Custo: mexe no agregado principal. |
| B. Agregado `RecallTest` separado | Mais desacoplado e já seria um banco de perguntas, mas a regra de pontuação passaria a depender de dois agregados sem gravação atômica, mais coleção/rotas, e os dados de treino ficariam fora do caminho de eventos. Faz sentido na etapa 2 (banco de perguntas do caderno). |
| C. Teste só no front | A escolha das perguntas ficaria no navegador, fora do alcance da IA. |

## Design

### Domínio (`learning`)

- **`RecallQuestion`** (value object): `id` (uuid), `text` (≤ 500), `source` (`TO_REVIEW` · `SPACED_TOPIC` · `TOPIC` · `LEARNER`, este último reservado para a etapa 2), `template` (id do modelo de frase, ex.: `explain_to_review`, `recall_topic`, `when_to_use`), `topic` (texto que preencheu o modelo, opcional).
- **`ActiveSession`** ganha `questions: tuple[RecallQuestion, ...] = ()`.
- **`start_session(content_id, now, questions=())`**: numa revisão, guarda exatamente as perguntas recebidas (o caso de uso garante 3). Em estudo, ignora.
- **`RecallGrade`**: `MISSED` · `PARTIAL` · `RECALLED`. **`RecallAnswer`**: `question_id`, `answer` (texto, pode ser vazio, ≤ 5 000), `grade`, `useful: bool | None`.
- **`finish_session(notes, now, recall, answers=())`**: se a sessão ativa tem perguntas, exige **uma resposta corrigida para cada pergunta** (mesmos ids, sem sobrar nem faltar) → senão `RecallTestRequiredError` (422, como a autoavaliação). Sessão sem perguntas (aberta antes do deploy, ou de estudo) não exige.
- **`Content.last_to_review: str | None`**: atualizado com `notes.to_review` a cada sessão finalizada (pontuada ou não), se não vazio.
- **`StudySessionFinished`** ganha `recall_test: tuple[dict, ...] = ()` — um item por pergunta com `question_id, text, source, template, topic, position, answer, grade, useful`. Campo novo com default: o evento continua na mesma versão (mudança aditiva).

### Escolha das perguntas (application + composição)

- Port **`QuestionPicker`** (em `learning/application`): `pick(content, plan, now) -> tuple[RecallQuestion, ...]` (3 itens). É o ponto onde a IA (degraus 1 e 2) vai entrar.
- Implementação inicial por **regra fixa**, na raiz (composição, como `daily_plan.py`, pois junta `learning` + `curriculum`): `review_questions.py`. Candidatas, nesta ordem, sem repetir texto, completando até 3:
  1. **"Preciso revisar"** (`TO_REVIEW`, modelo `explain_to_review`): *"Explique sem consultar: {last_to_review}"*.
  2. **Tópicos espaçados** (`SPACED_TOPIC`, modelo `recall_topic`): os `warmup` do dia atual do cronograma (tópicos vistos há 1, 3 e 7 dias) → *"O que você lembra de {tópico}? Explique com um exemplo seu."*
  3. **Tópicos da matéria** (`TOPIC`, modelos em rodízio `recall_topic` / `when_to_use` / `teach_beginner`) a partir de `entry.topics` do catálogo, começando pelo tópico do dia e seguindo em ordem → *"Quando usar {tópico} e quando não usar?"*, *"Explique {tópico} para quem está começando."*
  - Conteúdo fora do catálogo: o cronograma já gera tópico genérico ("visão geral de X"); sempre há candidatas.
- `StartSession` recebe o `QuestionPicker` (injetado pelo composition root) e só o chama quando o tipo da sessão é revisão.

### Persistência

- Mongo `study_plans`: `schema_version` 3 → **4** com upcaster lazy (`last_to_review: None` em cada conteúdo; `active_session.questions: []`). Validador `$jsonSchema` aceita os campos novos.
- Histórico (`insights`): `SessionRecord` ganha `recall_test` (lista) lido do evento; documentos antigos sem o campo → `[]`. É o dataset que a IA vai usar.

### HTTP

- `ActiveSessionOut` ganha `questions: [{id, text, source}]` e `last_to_review: str | None`; `ContentOut` ganha `last_to_review`.
- `FinishSessionIn` ganha `answers: [{question_id, answer, grade, useful}]` (default `[]`).
- `SessionOut` (histórico) ganha `recall_test`.

### Tela

- Topo de qualquer sessão: **"🔁 Da última vez você anotou para revisar: …"** (se houver).
- Revisão, em três passos no mesmo painel:
  1. **Teste:** as 3 perguntas, cada uma com campo de resposta. Caderno e "preciso revisar" **escondidos**. Botão **"Conferir respostas"**.
  2. **Conferir:** aparecem o caderno e o último "preciso revisar"; em cada pergunta, botões **Errei / Parcial / Acertei** e 👍/👎. As respostas ficam só para leitura.
  3. **Fechar a sessão:** a nota 1 a 4 e os 3 campos de anotação, como hoje. "Finalizar sessão" só habilita com as 3 correções e a nota.
- Respostas digitadas e o passo atual são guardados no `localStorage` do navegador (chave = início da sessão) para sobreviver a recarregar; limpos ao finalizar/cancelar.
- Histórico mostra o teste de cada revisão (pergunta, resposta, correção).

### Testes

- BDD `teste_de_memoria.feature` (pt): revisão começa com 3 perguntas; ordem de origem (preciso revisar → espaçados → tópicos); sem repetir; finalizar sem corrigir todas é recusado; errar tudo ainda pontua se o resto da regra for cumprido; estudo não tem teste; sessão aberta antes (sem perguntas) finaliza sem teste; "preciso revisar" volta na próxima sessão; o evento carrega o teste.
- Unit do domínio (100% de branches), contrato do Mongo com upcaster v3→v4, HTTP, Vitest do painel (esconde o material antes de conferir, exige correções, sobrevive a recarregar), e2e de uma revisão completa.

## Decisões que tomei (pode corrigir)

- 👍/👎 é **opcional** (menos atrito); a correção é obrigatória.
- Resposta pode ficar **vazia** ("não lembrei" é uma resposta válida, corrigida como Errei).
- Sem teste → **recusa finalizar** (como já acontece sem a nota 1 a 4), em vez de finalizar sem ponto. Quem não quiser fazer o teste pode cancelar a sessão.
- As perguntas são **fixadas ao iniciar** a revisão (não mudam ao recarregar).
- Texto dos modelos de frase em português, como acima.
- **"Preciso revisar" longo ou com vários itens:** é dividido por linha/marcador (`-`, `•`, `1.`); cada item vira uma pergunta (texto cortado em 400 caracteres com "…"). No máximo **2** perguntas vêm daí, para sempre sobrar ao menos 1 de tópico espaçado/da matéria. O `topic` guarda o item original (até 500).
- **Sessão cancelada ou expirada:** o teste não é registrado (cancelar é desistir; expirar é raro) e o `last_to_review` não muda. O dataset só recebe testes de sessões finalizadas.
- **Caderno durante o teste:** escondido **só no painel da sessão** (confiança: quem burla engana a si mesmo); a aba Caderno e o card continuam acessíveis. No passo "Conferir", o caderno aparece **editável com autosave** — corrigir a anotação na hora é parte do aprendizado.
- **Conteúdos que já existem:** um script único (`make backfill-to-review`) preenche o `last_to_review` de cada conteúdo com o último "preciso revisar" não vazio do histórico (`study_sessions`). Sem ele, as primeiras revisões depois do deploy começariam sem a pergunta mais valiosa.

## O que fica para quem construir

Nomes internos, layout fino do painel, quantos modelos de frase extras além dos três citados, e o formato exato do item no evento (desde que traga os campos listados).
