# ADR-0002: Modelo de domínio — Trilha de estudo gamificada

**Status:** Aceito
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

Regras de negócio:

1. Uma sessão de **≥ 25 min com anotações** vale **1 ponto** no conteúdo estudado.
2. Se, no dia, o aprendiz estuda conteúdo novo **sem ter revisado antes**, a sessão não pontua.
3. Um conteúdo novo fica **bloqueado** até o atual ser concluído ou chegar ao domínio **Intermediário**.

As regras 2 e 3 são invariantes que **envolvem vários conteúdos do mesmo usuário**. Quando uma invariante envolve várias entidades, ela define onde o agregado começa e termina: tudo que precisa ficar consistente na mesma transação fica dentro de um único agregado.

## Decisão

### Bounded contexts

| Contexto | Tipo | Responsabilidade |
|---|---|---|
| `learning` | Core | trilha, sessões, pontos, domínio, desbloqueio |
| `identity` | Genérico | cadastro, login, sessão autenticada |
| `insights` | Suporte (futuro) | histórico, estatísticas, ML ([ADR-0012](ADR-0012-dados-para-ml.md)) |

Os contextos se comunicam **só por IDs e eventos**. Um contexto nunca importa o modelo de outro.

### Linguagem ubíqua (PT → código)

Aprendiz `Learner` · Trilha `StudyPlan` · Conteúdo `Content` · Sessão `StudySession` · Anotações `Notes` · Pontos `Points` · Nível de domínio `MasteryLevel` · Revisão `Review`.
O Gherkin fica em português e o código em inglês, porque o ecossistema e as bibliotecas usam inglês.

### Agregado `StudyPlan` (um por aprendiz, `id = LearnerId`)

```
StudyPlan (raiz)
├── contents: list[Content]            ← entidade (ContentId, Title, ContentKind, ContentStatus, Points)
│   └── challenges: list[Challenge]    ← entidade (ChallengeId, description, target_level, solved_at, evidence)
├── active_session: ActiveSession|None ← VO (content_id, started_at)
├── last_review_on: date|None          ← dia LOCAL da última revisão qualificada
└── timezone: Timezone                 ← VO; o "dia" é sempre o dia do aprendiz, não UTC
```

**Value Objects** (imutáveis, validam a si mesmos, igualdade por valor): `LearnerId`, `ContentId` (UUIDv7, nativo no Python 3.14), `Title`, `ContentKind` (BOOK, COURSE, ARTICLE, VIDEO, OTHER), `Points`, `MasteryLevel`, `Duration`, `Notes`, `Timezone`.

**`Notes` é estruturada.** O formulário é aberto ao finalizar a sessão e tem três campos: `studied` (o que estudei), `understood` (o que entendi) e `to_review` (o que preciso revisar). Ela é `is_substantive` quando **os três campos estão preenchidos** e somam **≥ 50 caracteres sem contar espaços**.

**`Challenge` é uma entidade, não um VO.** Ela tem identidade e ciclo de vida (criada → resolvida). Pertence a um `Content` e mira um nível (`target_level`). Resolver exige `evidence` não vazia, que pode ser um texto ou um link para o código ou a solução.

**Máquina de estados do `Content`:**

```
LOCKED ──unlock──▶ IN_PROGRESS ──(nível ≥ Intermediário)──▶ CONSOLIDATED ──finish (nível = Avançado)──▶ FINISHED
```

`finish` só é aceito no **nível máximo** da `MasteryPolicy` (hoje, Avançado). Antes disso o comando é recusado com `MasteryNotReachedError`. Na prática o caminho é sempre `IN_PROGRESS → CONSOLIDATED → FINISHED`, porque Intermediário consolida o conteúdo antes de chegar a Avançado.

**O tipo da sessão é derivado, não vem do usuário.** Se o conteúdo está `IN_PROGRESS`, é ESTUDO. Se está `CONSOLIDATED` ou `FINISHED`, é REVISÃO. Se está `LOCKED`, a sessão é rejeitada. Cada dado a menos vindo do cliente é uma superfície de trapaça a menos (veja o [ADR-0009](ADR-0009-appsec.md)).

### Invariantes (protegidas pela raiz)

| # | Invariante |
|---|---|
| I1 | No máximo **3** conteúdos `IN_PROGRESS` (configurável), **cada um de uma competência principal diferente**. Era 1 até 2026-11-02 |
| I2 | No máximo **1** sessão ativa por aprendiz |
| I3 | Não é possível iniciar uma sessão em conteúdo `LOCKED` |
| I4 | Pontos só mudam via `finish_session`, nunca por atribuição direta |
| I5 | Quando abre uma vaga, entra o conteúdo da fila (entre os próximos 5 elegíveis) que **mais se interliga** com os que já estão em andamento, segundo a afinidade entre competências. Cada posição a mais na fila custa 0,25 de afinidade, então a ordem de chegada continua pesando e desempata. A ordem pode ser ajustada com `reorder_queue` |
| I6 | `started_at` e `finished_at` vêm do **relógio do servidor**; o domínio recebe `now` como parâmetro |
| I7 | Uma sessão aberta há **> 4 h** é abandonada e **nunca** pontua. A verificação é *lazy*: o próximo comando (`start` ou `finish`) detecta e emite `StudySessionAbandoned`, então não precisa de scheduler |
| I8 | O nível só sobe com **pontos e desafios juntos**; o desafio só é resolvido com evidência |
| I9 | Um conteúdo só é concluído (`FINISHED`) no **nível máximo** (Avançado) |

### Políticas (Strategy, para atender ao princípio aberto/fechado do SOLID)

- `ScoringPolicy`: uma sessão pontua se `25min ≤ duration ≤ 4h` **e** `notes.is_substantive` **e** (`kind == REVIEW` **ou** não existe conteúdo revisável **ou** `last_review_on == hoje_local`).
- `MasteryPolicy`: `(Points, desafios resolvidos) → MasteryLevel`. Para atingir um nível, é preciso ter os pontos mínimos **e** 3 desafios resolvidos com `target_level` igual a esse nível.

| Nível | Pontos | Desafios resolvidos daquele nível |
|---|---|---|
| Iniciante | 0 | — |
| Intermediário | ≥ 10 | 3 |
| Avançado | ≥ 30 | 3 |

Ter 15 pontos e 1 desafio continua sendo **Iniciante**. Por isso o nível é **derivado** a cada mudança e nunca é armazenado como verdade.

Assim, trocar limites ou regras significa criar uma nova política, sem mexer no agregado.

### Eventos de domínio (no passado, imutáveis, versionados)

`ContentAdded` · `ContentQueued` · `ContentUnlocked` · `StudySessionStarted` · `StudySessionFinished` · `StudySessionAbandoned` · `PointAwarded` · `PointWithheld{reason: TOO_SHORT|NO_NOTES|NO_REVIEW|EXPIRED}` · `ChallengeAdded` · `ChallengeSolved` · `MasteryLevelReached` · `ContentFinished`

### Repositório de domínio (port)

```python
class StudyPlanRepository(Protocol):
    async def get(self, learner_id: LearnerId) -> StudyPlan | None: ...
    async def save(self, plan: StudyPlan) -> None: ...  # optimistic lock; levanta ConcurrencyError
```

A regra é um repositório **por agregado**, nunca por tabela ou coleção.

### Especificação executável (BDD)

```gherkin
# language: pt
Funcionalidade: Pontuar sessões de estudo

  Cenário: Sessão de 25 minutos com anotações pontua
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 25 minutos com anotações
    Então "Clean Code" tem 1 ponto

  Cenário: Sessão curta não pontua
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 24 minutos com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "TOO_SHORT"

  Cenário: Estudar sem revisar no dia não pontua
    Dado que "DDD" está consolidado
    E que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 30 minutos com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "NO_REVIEW"

  Cenário: Revisar antes libera a pontuação do dia
    Dado que "DDD" está consolidado
    E que "Clean Code" está em andamento
    Quando eu reviso "DDD" por 25 minutos com anotações
    E eu estudo "Clean Code" por 25 minutos com anotações
    Então "Clean Code" tem 1 ponto

Funcionalidade: Desbloqueio progressivo

  Cenário: Conteúdo novo entra bloqueado
    Dado que "Clean Code" está em andamento com 3 pontos
    Quando eu adiciono "Refactoring"
    Então "Refactoring" fica bloqueado
    E sou avisado de que preciso concluir "Clean Code" ou chegar a Intermediário

  Cenário: Pontos sem desafios não sobem de nível
    Dado que "Clean Code" está em andamento com 9 pontos
    E que resolvi 2 desafios de Intermediário em "Clean Code"
    E que "Refactoring" está bloqueado
    Quando eu ganho 1 ponto em "Clean Code"
    Então "Clean Code" continua Iniciante
    E "Refactoring" continua bloqueado

  Cenário: Pontos e 3 desafios desbloqueiam o próximo
    Dado que "Clean Code" está em andamento com 10 pontos
    E que resolvi 2 desafios de Intermediário em "Clean Code"
    E que "Refactoring" está bloqueado
    Quando eu resolvo o 3º desafio de Intermediário com evidência
    Então "Clean Code" fica Intermediário
    E "Refactoring" fica em andamento

Funcionalidade: Sessões abandonadas

  Cenário: Sessão aberta há mais de 4 horas não pontua
    Dado que iniciei uma sessão em "Clean Code"
    Quando eu finalizo a sessão 4 horas e 1 minuto depois com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "EXPIRED"
```

## Opções consideradas

| | A: `StudyPlan` agrega conteúdos ✅ | B: `Content` como agregado + serviço de domínio | C: `StudySession` como agregado |
|---|---|---|---|
| Consistência de I1/I2 | Forte, em 1 documento | Eventual; corrida pode deixar 2 em andamento | Eventual |
| Complexidade | Baixa | Média (saga/compensação) | Alta |
| Tamanho | Cresce com o nº de conteúdos (centenas, ok) | Pequeno | Ilimitado |

A opção B só faria sentido com milhares de conteúdos por usuário, o que não é o caso. O histórico de sessões, que cresce sem limite, **fica fora** do agregado: ele é uma projeção alimentada por eventos ([ADR-0006](ADR-0006-eventos-outbox-rabbitmq.md)).

## Consequências

- ✅ Todas as regras de negócio são testáveis em memória, sem I/O, em milissegundos.
- ✅ A trapaça "abrir duas sessões" fica impossível por construção (I2).
- ⚠️ Todo comando de um aprendiz serializa no mesmo documento. Para um usuário isso é irrelevante, mas exige optimistic locking.
- 🔁 Revisitar se surgir trilha compartilhada entre usuários (outro agregado).

## Decisões confirmadas (2026-10-31)

1. "Revisar" = uma sessão qualificada em conteúdo `CONSOLIDATED` ou `FINISHED`, no mesmo dia local, **antes** da sessão de estudo.
2. Anotações estruturadas (estudei / entendi / preciso revisar), ≥ 50 caracteres sem contar espaços.
3. Níveis: pontos (10/30) **e** 3 desafios resolvidos por nível; o próximo conteúdo é desbloqueado no Intermediário.
4. Uma sessão aberta há > 4 h, não fechada ou sem anotações, não pontua.
7. (2026-11-02) Um conteúdo consolidado **hoje** só passa a exigir revisão (regra 2) a partir de **amanhã**. Sem isso, chegar a Intermediário no meio do dia derrubava a pontuação dos outros estudos do dia (bug encontrado pela simulação da semana). O `Content` registra `consolidated_at`; consolidações antigas, sem essa data, seguem exigindo revisão.
6. (2026-11-02) Até 3 conteúdos em paralelo, de competências diferentes e que se interligam (pedido do aprendiz). O domínio recebe a competência e a afinidade por uma `UnlockPolicy` injetada (Protocol), para não depender do catálogo. O padrão do próprio domínio continua sendo 1 por vez.
5. (2026-11-01) Concluir exige o **nível máximo** (Avançado). Antes, `finish` era aceito em qualquer conteúdo em andamento, o que permitia "concluir sem concluir nada" (bug encontrado no uso).

## Em aberto

- **Quem cria os desafios?** Padrão adotado: o próprio aprendiz os cadastra e declara a resolução com evidência (autoavaliação). No futuro, o ML ou um LLM pode sugerir desafios, o que seria só um novo adapter de um port `ChallengeSuggester`.

## Itens de ação

1. [ ] VOs com TDD → `Content` → `Challenge` → `StudyPlan` → políticas → cenários BDD verdes
