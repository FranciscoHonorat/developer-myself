"""Script único: preenche o "preciso revisar" das matérias que já existiam antes do campo,
com o último `notes_to_review` não vazio do histórico (`study_sessions`).

Idempotente: só preenche quem ainda não tem; rodar de novo não muda nada.
Uso: `make backfill-to-review` (stack no ar).
"""

import asyncio
import uuid

from developer_myself.insights.application.history import SessionHistoryStore
from developer_myself.learning.domain.repository import StudyPlanRepository
from developer_myself.learning.domain.value_objects import LearnerId

HISTORY_LIMIT = 100_000


async def backfill_last_to_review(
    plans: StudyPlanRepository, history: SessionHistoryStore, learner_id: uuid.UUID
) -> int:
    """Devolve quantos conteúdos foram preenchidos; salva o plano uma vez, se mudou."""
    plan = await plans.get(LearnerId(learner_id))
    if plan is None:
        return 0
    latest: dict[str, str] = {}
    # `list_for` vem do mais recente para o mais antigo: o primeiro não vazio vence.
    for record in await history.list_for(str(learner_id), HISTORY_LIMIT):
        if record.type == "study_session_finished" and record.notes_to_review.strip():
            latest.setdefault(record.content_id, record.notes_to_review)
    changed = sum(
        plan.backfill_last_to_review(c.id, latest[str(c.id)])
        for c in plan.contents
        if str(c.id) in latest
    )
    if changed:
        await plans.save(plan)
    return changed


async def _main() -> None:  # pragma: no cover - roda contra o Mongo do compose
    from developer_myself.insights.adapters.mongo.store import (  # noqa: PLC0415
        MongoSessionHistoryStore,
    )
    from developer_myself.learning.adapters.mongo.repository import (  # noqa: PLC0415
        MongoStudyPlanRepository,
    )
    from developer_myself.shared.adapters.mongo_setup import make_client  # noqa: PLC0415
    from developer_myself.shared.settings import Settings  # noqa: PLC0415

    settings = Settings()
    client = make_client(settings.mongo_url.get_secret_value())
    db = client[settings.mongo_db]
    plans = MongoStudyPlanRepository(db.study_plans)
    history = MongoSessionHistoryStore(db.study_sessions, db.processed_events)
    total = 0
    async for doc in db.study_plans.find({}, {"_id": 1}):
        total += await backfill_last_to_review(plans, history, doc["_id"])
    await client.close()
    print(f"Preenchi o 'preciso revisar' de {total} conteúdo(s).")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())
