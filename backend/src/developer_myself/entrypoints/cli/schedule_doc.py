"""Gera `Docs/Cronograma de estudos.md` a partir da trilha real: `make schedule-doc`.

As datas vêm da projeção simulada (`planning/application/projection.py`): as regras reais do
domínio, até 3 em paralelo e o ritmo escolhido. Inclui a semana-modelo.
"""

import asyncio
import sys
import uuid
from zoneinfo import ZoneInfo

from developer_myself.composition.mongo import build_mongo_container
from developer_myself.curriculum.adapters.markdown import TrailItem, render
from developer_myself.learning.domain.value_objects import ContentId
from developer_myself.planning.application.projection import project
from developer_myself.planning.application.weekly_plan import weekly_plan
from developer_myself.shared.adapters.mongo_setup import make_client
from developer_myself.shared.settings import Settings


async def main() -> None:

    container = await build_mongo_container(Settings())
    try:
        # Uso pessoal: a (única) trilha do banco.
        settings = Settings()
        client = make_client(settings.mongo_url.get_secret_value())
        doc = await client[settings.mongo_db].study_plans.find_one({}, {"_id": 1})
        await client.close()
        if doc is None:
            raise SystemExit("Nenhuma trilha encontrada.")
        plan = await container.learning.get_plan(doc["_id"])
        now = container.clock.now()
        recommender = await container.recommender.current()
        active = [c for c in plan.contents if c.status.value != "LOCKED"]
        ordered = active + plan.queue
        items = [TrailItem(c.title.value, c.status.value, c.points.value) for c in ordered]
        today = now.astimezone(ZoneInfo(plan.timezone.name)).date()
        projection = project(plan, today)
        starts = {
            plan.content(ContentId(uuid.UUID(k))).title.value: m.started
            for k, m in projection.milestones.items()
        }
        week = weekly_plan(plan, recommender, now)
        sys.stdout.write(
            render(
                items,
                today,
                starts=starts,
                week=week,
                finish=projection.last("advanced"),
                max_in_progress=plan.unlock_policy.max_in_progress,
            )
        )
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
