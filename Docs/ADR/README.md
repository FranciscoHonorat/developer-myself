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

## Notas de implementação (2026-11-01)

Todos os passos 0–11 foram implementados. Pontos em que a realidade ajustou o plano:

- **ADR-0004**: a condição de saída não foi acionada; `pydantic-core`, `pymongo` e `argon2-cffi` têm wheels para o 3.15.
- **ADR-0005**: a imagem do Mongo é a **8.2**, porque o 8.0 se recusa a iniciar em kernel Linux ≥ 6.19 (SERVER-121912).
- **ADR-0005**: não há autenticação no Mongo no compose local (replica set com auth exige keyFile). As portas ficam expostas só em `127.0.0.1`. Ativar antes de qualquer deploy público.
- **ADR-0006**: a idempotência do consumer usa `_id = event_id` na própria `study_sessions`, além de `processed_events`, para não perder o registro se o processo cair entre as duas escritas. Sem RabbitMQ (modo `memory`), os eventos são despachados em processo.
- **ADR-0008**: o smoke e2e também é BDD (Gherkin pt via `playwright-bdd`).
- **ADR-0010**: o `/readyz` da API verifica só o Mongo. A API não depende do broker (essa é a razão do outbox); quem fala com o RabbitMQ é o worker.
- **ADR-0011**: em produção/local, a própria API serve o build do React (`DM_STATIC_DIR`) na mesma origem. O Vite com proxy fica para o desenvolvimento.
- Comandos extras: cancelar sessão (`StudySessionAbandoned{CANCELLED}`), exportar dados e excluir conta (LGPD).
- **ADR-0012 (adiantado)**: a primeira rede neural já existe em `insights/adapters/neural/`. É um MLP 4→8→1 escrito em Python puro, que implementa o port `ReviewRecommender` e é usado em `GET /api/recommendations`. Ela foi **treinada com dados sintéticos** de uma curva de esquecimento (cold start), porque ainda não há rótulo real de "lembrei/esqueci". Sem o `model.json`, o sistema cai para a regra do degrau 1. Próximo passo para dados reais: pedir uma autoavaliação ("lembrei bem? 1–4") ao iniciar uma revisão e treinar com ela (`make train`).
- **ADR-0012 v2 (2026-11-01)**: a rede passou a aprender com dados reais.
  - **Rótulo:** toda revisão exige autoavaliação 1–4 (Esqueci/Difícil/Bem/Fácil). "Lembrou" = nota ≥ 2, como no FSRS.
  - **Sinais:** `StudySessionFinished` carrega os sinais de **antes** da sessão (tempo sem contato, pontos, revisões, idade do conhecimento, última nota, média das anotações).
  - **Features e schema:** 9 features. O `Content` ganhou contadores, com schema Mongo v2 e upcaster lazy v1→v2.
  - **Treino:** Adam, mini-batch, L2, pesos por amostra (real = 5× sintético) e early stopping. A avaliação inclui Brier e calibração (ECE).
  - **Retreino:** o worker retreina a cada hora quando há ≥ 5 rótulos novos. O desafiante só vira ativo se não for pior que o campeão no mesmo conjunto de validação; todos os modelos ficam em `ml_models`. A API recarrega o modelo ativo a cada 60 s, sem reiniciar.
- **Contexto `curriculum` (2026-11-01)**: catálogo com os blocos do *Mapa de conteúdos* (`Docs/`) e os conteúdos próprios da trilha. Cada conteúdo tem um **cronograma de 30 dias** casado com as regras do `learning`: 1 sessão pontuada = 1 dia; dias 1 a 10 levam a Intermediário (desafios nos dias 8 a 10); dias 11 a 30 viram revisões até Avançado (desafios nos dias 26 a 28); cada tópico novo volta de memória em 1, 3 e 7 dias.
  - `GET /api/today` compõe estudo + revisões, com a ordem das revisões decidida pela rede neural.
  - `make schedule-doc` gera `Docs/Cronograma de estudos.md`.
  - O domínio ganhou `remove_content`, que só aceita conteúdo sem progresso, e `rename_content`. Com eles a trilha foi reconciliada com o mapa: 2 repetidos removidos, 3 títulos corrigidos e 32 blocos adicionados.
- **Ficha de competências (2026-11-01)**: 16 competências em 6 áreas do mapa. Cada conteúdo do catálogo tem pesos explícitos por competência (ex.: Gin = 50% Go + 50% Backend). As regras ficam em `curriculum/domain/progression.py`:
  - **Score** = média do progresso dos conteúdos, ponderada pela profundidade do mapa (Profundo 3, Funcional 2, Noção 1).
  - **Faixas:** Aprendiz, Praticante (25), Proficiente (50), Especialista (75). A **meta** de cada competência vem do mapa.
  - **Ferrugem:** depois de 21 dias sem revisão ou desafio, a contribuição do conteúdo cai 1% ao dia, até um piso de 50%, e volta na hora com uma revisão ou um desafio resolvido. **Pontos nunca diminuem** (I4); só a competência efetiva cai, e o pico mostra o que dá para recuperar.
  - **Visualização:** barras ranqueadas no lugar de pizza. Com 16 competências a pizza fica ilegível, e numa pizza uma fatia cresce às custas das outras. O esforço aparece numa barra segmentada com as 6 áreas, em cores fixas validadas para daltonismo.
- **Perfil em T e estudo em paralelo (2026-11-02)**:
  - **Trilha:** +20 conteúdos (Windows por dentro, PowerShell, Assembly/PE/ELF, Estatística, 4 de Inteligência e 12 de DFIR) e 6 competências novas. A trilha tem 83 conteúdos.
  - **Paralelo:** até 3 em andamento, de competências diferentes, com desbloqueio por afinidade (`UnlockPolicy` injetada).
  - **Novos comandos:** `reorder_queue` e preferências de estudo (minutos por dia e folgas), com schema Mongo v3.
  - **Semana planejada:** pomodoros de 30 min, revisões primeiro, simulada dia a dia com as regras reais (`simulation.py`), em `GET /api/week` e na tela Semana.
  - **Documentos:** a projeção de datas virou simulação (`projection.py`), e a proposta de reorganização está em `Docs/Organização da trilha.md`, ainda não aplicada.
