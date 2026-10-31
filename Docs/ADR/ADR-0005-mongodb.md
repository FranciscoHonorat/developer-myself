# ADR-0005: MongoDB como persistência do agregado

**Status:** Proposto. Substitui a parte de banco do [ADR-0001](ADR%20-0001-tech.md) (PostgreSQL).
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

O agregado `StudyPlan` ([ADR-0002](ADR-0002-modelo-de-dominio.md)) é uma árvore lida e gravada inteira. No MongoDB, **a escrita em um único documento é atômica**. Se o agregado cabe em um documento, não precisamos de transações multi-documento.

## Decisão

### Modelagem: 1 agregado = 1 documento

```js
// study_plans
{ _id: UUID(learner_id),            // 1 trilha por aprendiz: o próprio _id garante a unicidade
  schema_version: 1, version: 42,   // migração lazy + optimistic lock
  timezone: "America/Sao_Paulo", last_review_on: "2026-10-31",
  active_session: { content_id: UUID, started_at: ISODate } | null,
  contents: [{ id: UUID, title, kind, status, points, queued_at }],
  outbox: [{ event_id, type, version, occurred_at, payload }]   // ADR-0006
}
```

Coleções: `study_plans`, `study_sessions` (histórico, só recebe inserções, preenchido por consumer), `users`, `auth_sessions`, `processed_events`.

### Concorrência otimista

```python
result = await col.update_one({"_id": id, "version": v}, {"$set": {...}, "$inc": {"version": 1}})
if result.matched_count == 0: raise ConcurrencyError
```

Se duas abas finalizarem a mesma sessão ao mesmo tempo, só uma vence. Isso mantém a invariante I2 mesmo sob corrida.

### Detalhes que mordem

| Item | Decisão | Por quê |
|---|---|---|
| UUID | `AsyncMongoClient(uuidRepresentation="standard")` | O padrão do PyMongo 4 é `unspecified`, que **recusa** gravar `uuid.UUID` |
| Topologia | *Replica set* mesmo com 1 nó (`--replSet rs0`) | Habilita change streams (relay futuro) e `w: majority` |
| Durabilidade | `w="majority"`, `readConcern="majority"` | Não perder uma escrita confirmada no failover |
| Schema | `$jsonSchema` validator por coleção | Defesa em profundidade: o banco recusa documentos malformados mesmo que um bug passe |
| TTL | `auth_sessions.expires_at`, `processed_events.seen_at` | Expiração automática feita pelo próprio banco |
| Índices | `study_sessions {learner_id:1, finished_at:-1}`; parcial `study_plans {has_outbox:1}` onde `has_outbox: true` | Consultas do histórico e do relay sem varrer a coleção (*collection scan*) |
| ODM | **Nenhum** (sem Beanie/ODMantic) | O mapeamento fica no adapter; o domínio não conhece BSON |

## Opções consideradas

| | MongoDB ✅ | PostgreSQL + JSONB |
|---|---|---|
| Fit agregado-documento | Natural | Bom (coluna JSONB) |
| Atomicidade do agregado | 1 documento | 1 linha |
| Integridade referencial | Na aplicação | FK no banco |
| Consultas analíticas | Aggregation pipeline | SQL (superior) |
| Objetivo de aprendizado | ✅ (requisito) | — |

Avaliação honesta: o Postgres também atenderia bem. O Mongo vence pelo formato do agregado e pelo objetivo de estudo. O custo é perder FK e SQL analítico, e a análise vai para o ML ([ADR-0012](ADR-0012-dados-para-ml.md)).

## Consequências

- ✅ Nenhuma transação multi-documento no caminho principal.
- ⚠️ Evoluir o schema exige `schema_version` e um *upcaster* no adapter, que atualiza o documento ao ler.
- 🔁 O limite de 16 MB por documento só é um risco com dezenas de milhares de conteúdos.
