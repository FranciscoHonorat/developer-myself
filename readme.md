# Developer Myself

Esse é um projeto criado para organizar e gerenciar o desenvolvimento de hardskill e softskill utilizando conceitos como repetiçao espaçada, gameficação, aprendizado ativo e microlearning. O objetivo é criar um ambiente de aprendizado contínuo e eficiente, permitindo que os desenvolvedores aprimorem suas habilidades de forma estruturada e motivadora.

## Funcionalidades

- **Gerenciamento de Hardskill e Softskill**: Permite aos usuários registrar, acompanhar e avaliar suas habilidades técnicas e comportamentais.
- **Repetição Espaçada**: Implementa técnicas de revisão espaçada para otimizar a retenção de conhecimento.
- **Gamificação**: Introduz elementos de jogo, como pontos, níveis e conquistas, para aumentar o engajamento e a motivação dos usuários.
- **Aprendizado Ativo**: Incentiva a prática ativa e a aplicação do conhecimento adquirido em situações reais.
- **Microlearning**: Oferece conteúdos curtos e focados, facilitando o aprendizado em pequenas doses e promovendo a assimilação gradual de informações.
- **Interface Intuitiva**: Fornece uma interface amigável e fácil de usar, permitindo que os usuários naveguem e interajam com o sistema de forma eficiente.
- **Relatórios e Estatísticas**: Gera relatórios detalhados sobre o progresso do usuário, permitindo a análise de desempenho e identificação de áreas de melhoria.

## Regras do jogo

As regras vivem em [`backend/tests/features/*.feature`](backend/tests/features) (Gherkin em português) e são a documentação executável do sistema ([ADR-0002](Docs/ADR/ADR-0002-modelo-de-dominio.md)).

| Regra | Como funciona |
|---|---|
| Ponto | Sessão de **25 min a 4 h** + anotações (*estudei / entendi / preciso revisar*, os três preenchidos, ≥ 50 caracteres sem espaços) = **1 ponto** |
| Revisão diária | Se existe conteúdo consolidado, é preciso **revisar antes** de estudar o atual no mesmo dia (local) para pontuar |
| Foco | Só **1** conteúdo em andamento; os novos entram numa **fila** (FIFO) |
| Nível | Intermediário = **10 pts + 3 desafios** de Intermediário; Avançado = **30 pts + 3 desafios** de Avançado |
| Desbloqueio | Ao chegar a Intermediário (ou concluir), o conteúdo é consolidado e o próximo da fila é liberado |
| Cronograma | Cada conteúdo tem 30 dias: 1 sessão pontuada = 1 dia; dia 10 = Intermediário, dia 30 = Avançado. A tela mostra **📅 Hoje** (revisões + estudo) |
| Competências | Aba **Competências**: nível por skill (Aprendiz → Especialista), meta do mapa, XP e nível geral. Sem revisar ou resolver desafios por **3 semanas**, a skill **enferruja** (os pontos ficam) |
| Autoavaliação | Toda revisão pergunta "quanto você lembrava?" (1 Esqueci · 2 Difícil · 3 Bem · 4 Fácil); é o que ensina a rede neural |
| Caderno | Bloco livre por matéria para escrever conceitos com as suas palavras, salvo sozinho enquanto você digita; **não pontua** e não substitui as 3 anotações. Abra na aba **Caderno** ou no botão 📓 do card |
| Teste de memória | Toda revisão começa com 3 perguntas respondidas sem consultar; você confere, marca Errei/Parcial/Acertei e só então finaliza. Seu último "preciso revisar" aparece no topo de cada sessão |
| Anti-trapaça | O servidor marca o tempo; 1 sessão ativa por vez; sessão > 4 h é abandonada e nunca pontua |

## Como usar

Pré-requisitos: [mise](https://mise.jdx.dev) (lê o `.tool-versions`) e Docker.

```bash
make install   # dependências do backend, frontend e Chromium do e2e
make up        # sobe API + worker + MongoDB + RabbitMQ → http://localhost:8000
make down      # derruba (os dados ficam nos volumes do Docker)
```

Na primeira vez, o `make up` cria o `.env` a partir do `.env.example`. **Troque a senha do RabbitMQ.**

### Desenvolvimento

```bash
# API em memória (sem Docker) + Vite com hot reload
cd backend && DM_STORAGE=memory DM_COOKIE_SECURE=false poetry run uvicorn developer_myself.entrypoints.api:app --reload
cd frontend && npm run dev     # http://localhost:5173 (proxy /api → :8000)
```

| Comando | O que faz |
|---|---|
| `make check` | Tudo que o CI roda: lint, tipos, unit, BDD, HTTP, arquitetura, Vitest, integração |
| `make test-bdd` | Só os cenários Gherkin, com a saída verbosa |
| `make test-int` | Mongo e RabbitMQ reais via Testcontainers |
| `make e2e` | Smoke e2e em BDD (`playwright-bdd`) no Chromium |
| `make deploy` | Sobe a imagem publicada pelo CD se mudou: verifica atestação, health check e rollback (`TAG=<sha>` fixa versão) |
| `make autodeploy-on` / `-off` | Liga/desliga o deploy contínuo (timer do systemd a cada 5 min) |
| `make autodeploy-logs` | Histórico dos deploys automáticos |
| `make verify-image` | Confere a atestação de proveniência da imagem (`gh attestation verify`) |
| `make audit` | `pip-audit` + `npm audit` |
| `make train` | Treina o modelo-base da rede (só dados sintéticos, vai no `model.json`) |
| `make retrain` | Retreina agora com suas autoavaliações (o worker também faz sozinho, de hora em hora) |
| `make models` | Lista os modelos treinados, qual está ativo e as métricas |
| `make schedule-doc` | Gera `Docs/Cronograma de estudos.md` (30 dias por conteúdo, na ordem da sua fila) |
| `make help` | Lista todos os alvos |

## Arquitetura

Hexagonal com *bounded contexts* ([ADR-0003](Docs/ADR/ADR-0003-arquitetura-hexagonal.md)). A raiz do pacote não tem módulos soltos: o teste de arquitetura garante isso ([ADR-0013](Docs/ADR/ADR-0013-organizacao-do-pacote.md)).

```
backend/src/developer_myself/
├── learning/     core: StudyPlan (agregado), políticas, casos de uso, adapters http/mongo/rabbitmq/memory
├── curriculum/   catálogo, competências, cronograma de 30 dias, semana-modelo
├── identity/     cadastro, login, cookie de sessão opaco, Argon2id
├── insights/     projeção do histórico de sessões e estatísticas (alimentada por eventos)
│   └── adapters/neural/  primeira rede neural (MLP do zero): chance de lembrar cada conteúdo
├── planning/     orquestração: hoje, semana, projeção, recomendação e competências
│                 (lê domain/application dos outros contextos, nunca adapters)
├── accounts/     rotas que cruzam contextos por IDs: área de admin e exportação (LGPD)
├── shared/       Clock, envelope de evento, settings, logging, peças HTTP comuns
├── composition/  composition root: único lugar que conhece todos os adapters (memória e Mongo)
└── entrypoints/  api.py (uvicorn), worker.py (outbox + consumer), cli/ (train, retrain, schedule-doc, backfill)
frontend/src/    React + TanStack Query; `api/` é o único módulo que chama fetch
```

Fluxo de um comando: `HTTP → caso de uso → StudyPlan (domínio puro) → Mongo (estado + outbox na mesma escrita) → relay → RabbitMQ → consumer → study_sessions`.

## Tecnologias Utilizadas

Python 3.15 · FastAPI · MongoDB 8.2 · RabbitMQ 4 · pytest + pytest-bdd · React 19 + TypeScript · TanStack Query · Vite · Vitest · Playwright + playwright-bdd · Ruff · mypy · Biome · Docker Compose
