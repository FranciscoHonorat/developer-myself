"""Gera `Docs/Cronograma de estudos.md` a partir da trilha real: `make schedule-doc`.

As datas vêm da projeção simulada (`planning/application/projection.py`): as regras reais do
domínio, até 3 em paralelo e o ritmo escolhido. Inclui a semana-modelo.
"""

import argparse
import asyncio
import sys
import uuid
from zoneinfo import ZoneInfo

from developer_myself.composition.mongo import build_mongo_container
from developer_myself.curriculum.adapters.markdown import TrailItem, render
from developer_myself.identity.domain.model import Email, Username
from developer_myself.learning.domain.value_objects import ContentId
from developer_myself.planning.application.projection import project
from developer_myself.planning.application.weekly_plan import weekly_plan
from developer_myself.shared.adapters.mongo_setup import make_client
from developer_myself.shared.settings import Settings


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera o cronograma em Markdown de uma trilha.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--username", help="Username da conta (obrigatório se houver mais de uma).")
    group.add_argument("--email", help="E-mail da conta (obrigatório se houver mais de uma).")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = Settings()
    client = make_client(settings.mongo_url.get_secret_value())
    container = await build_mongo_container(settings, client=client)
    try:
        learner_id: uuid.UUID
        if args.username:
            user = await container.identity.users.get_by_username(Username(args.username))
            if user is None:
                raise SystemExit(f"Usuário {args.username!r} não encontrado.")
            learner_id = user.id.value
        elif args.email:
            user = await container.identity.users.get_by_email(Email(args.email))
            if user is None:
                raise SystemExit(f"Conta {args.email!r} não encontrada.")
            learner_id = user.id.value
        else:
            docs = await client[settings.mongo_db].study_plans.find({}, {"_id": 1}).to_list(2)
            if not docs:
                raise SystemExit("Nenhuma trilha encontrada.")
            if len(docs) > 1:
                raise SystemExit("Há mais de uma trilha no banco: passe --username ou --email.")
            learner_id = docs[0]["_id"]

        plan = await container.learning.get_plan(learner_id)
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
                max_in_progress=plan.effective_max_in_progress,
            )
        )
    finally:
        await container.close()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
