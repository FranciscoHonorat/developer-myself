# ADR-0006: Eventos de domínio via outbox embutido + RabbitMQ

**Status:** Proposto
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

Gravar o agregado e publicar o evento são duas operações em sistemas diferentes. Sem cuidado, o resultado é o *dual write*: o banco grava e o broker cai, então o evento se perde, ou o contrário. Os consumidores (histórico de sessões, estatísticas, ingestão de ML) não podem bloquear o comando do usuário.

## Decisão

### Outbox **embutido no documento do agregado**

1. O agregado acumula eventos em memória.
2. `repository.save()` grava o estado **e** faz `$push` dos eventos em `outbox`, com `has_outbox: true`, **na mesma escrita atômica** ([ADR-0005](ADR-0005-mongodb.md)).
3. O **relay** (processo `worker`) busca planos com `has_outbox: true`, publica com *publisher confirms* e **só depois** faz `$pull` dos eventos confirmados.

O resultado é entrega **at-least-once** sem transação distribuída e sem transação multi-documento.

### Topologia RabbitMQ (4.x)

```
exchange  learning.events (topic, durable)
  ├─ rk: learning.study_session_finished.v1 ─▶ queue insights.session-history (quorum)
  └─ rk: learning.#                         ─▶ queue insights.ml-ingest       (quorum, futuro)
DLX: learning.dlx ─▶ <queue>.dlq   (parking lot)
```

- **Quorum queues**: as filas clássicas espelhadas foram removidas no RabbitMQ 4. As quorum queues têm um `delivery-limit` que segura mensagens venenosas, mandando-as para a DLQ.
- **Consumer**: `ack` manual, `prefetch=10`, e o `ack` só acontece **depois** de gravar.
- **Idempotência**: insert em `processed_events` (índice único em `event_id`). Se der `DuplicateKeyError`, a mensagem é descartada com `ack`.

### Envelope (contrato público, versionado)

```json
{ "event_id": "uuid7", "type": "study_session_finished", "version": 1,
  "occurred_at": "…Z", "learner_id": "…", "correlation_id": "…", "payload": {} }
```

Mudanças compatíveis mantêm `v1`. Uma mudança incompatível gera `v2` em paralelo, e os dois coexistem até a migração dos consumers.

## Opções consideradas

| | In-process apenas | Outbox + RabbitMQ ✅ | Change streams como barramento | Kafka |
|---|---|---|---|---|
| Garantia | Perde no crash | At-least-once | At-least-once | At-least-once + replay |
| Ops | Zero | Médio | Baixo | Alto |
| Replay p/ ML | Não | Via RabbitMQ Streams | Limitado (oplog) | Nativo |

Ponto de atenção (YAGNI): para um usuário, despachar em processo bastaria. O RabbitMQ entra **junto com o primeiro consumer real** (o histórico de sessões) e não antes. Se o ML pedir replay, a evolução natural é **RabbitMQ Streams**, sem trocar de broker.

## Consequências

- ✅ O comando do usuário não depende de o broker estar no ar.
- ⚠️ Os consumers **precisam** ser idempotentes, e a ordem só é garantida por fila.
- 🔁 Trocar o polling do relay por change streams quando a latência importar.
