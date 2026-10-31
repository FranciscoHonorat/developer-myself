# ADR-0012: Preparar dados agora para recomendação por ML depois

**Status:** Proposto (implementação adiada)
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

O objetivo futuro é avaliar a evolução do aprendiz e recomendar o que revisar usando redes neurais. **Um modelo só é tão bom quanto o histórico que existir quando ele nascer**, e esse histórico começa no primeiro dia.

## Decisão (agora)

1. **Os eventos de domínio são a fonte da verdade analítica.** São imutáveis, versionados e têm `occurred_at` ([ADR-0006](ADR-0006-eventos-outbox-rabbitmq.md)). Nunca apagamos histórico para "corrigir" estado.
2. Cada `StudySessionFinished` carrega os sinais úteis: duração real, tamanho das anotações, tipo (estudo ou revisão), dias desde o último contato com o conteúdo, nível antes e depois, e motivo de não pontuar.
3. O campo `to_review` das anotações é o sinal mais valioso: é o próprio aprendiz dizendo onde está a lacuna. Esse texto é a matéria-prima para o recomendador e para gerar desafios. Os eventos `ChallengeSolved` (com o tempo que levou desde `ChallengeAdded`) medem a aplicação prática, e não só o tempo de estudo.
4. A fila `insights.ml-ingest` só é criada quando o pipeline existir. Até lá, o `study_sessions` já é um dataset utilizável.

## Decisão (depois): progressão em degraus

| Degrau | Técnica | Por quê |
|---|---|---|
| 1 | Regras de repetição espaçada (intervalo cresce a cada revisão) | Sem dado nenhum já funciona |
| 2 | **FSRS** (modelo de memória que é o estado da arte em agendamento de revisões) | Ajusta parâmetros com poucas centenas de revisões |
| 3 | Rede neural (ex.: sequência de sessões → probabilidade de esquecimento) | Só quando houver dados de **muitos** aprendizes; com um único usuário, o modelo memoriza os dados em vez de aprender (overfitting) |

Cada degrau entra no sistema como um **adapter** de um port `ReviewRecommender`. O domínio não muda.

## Consequências

- ✅ Nenhum retrabalho de dados quando o ML chegar.
- ⚠️ É obrigatório ter consentimento e pseudonimização (LGPD, [ADR-0009](ADR-0009-appsec.md)) antes de usar dados de terceiros.
- 🔁 Replay de eventos em escala: avaliar RabbitMQ Streams ou um data lake em Parquet quando o degrau 3 for real.
