"""Semana planejada: 7 dias SIMULADOS com as regras reais, a partir de hoje.

Cada dia é montado a partir do estado da trilha naquele dia (depois de jogar os dias
anteriores), então consolidações e vagas abrindo no meio da semana aparecem na hora certa.
"""

import copy
from datetime import datetime, timedelta

from developer_myself.curriculum.domain.week import WeekDay
from developer_myself.insights.application.recommender import ReviewRecommender
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.planning.application.simulation import day_blocks, local_day, morning, play

WEEK_DAYS = 7


def weekly_plan(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> list[WeekDay]:
    sim = copy.deepcopy(plan)
    sim.active_session = None
    today = local_day(plan, now)
    days: list[WeekDay] = []
    for offset in range(WEEK_DAYS):
        moment = now if offset == 0 else morning(sim, today + timedelta(days=offset))
        day = day_blocks(sim, recommender, moment)
        days.append(day)
        play(sim, day)
    return days
