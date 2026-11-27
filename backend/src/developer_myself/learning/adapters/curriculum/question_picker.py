"""Perguntas do teste de memória por regra fixa: compõe a trilha (learning) e os
cronogramas (curriculum). É o primeiro `QuestionPicker`; a IA própria virá depois.

Ordem das candidatas, sem repetir texto, até `count` (revisão 3, aquecimento 2):
1. perguntas que o aprendiz deixou para o "eu do futuro" (mais antiga primeiro);
2. itens do último "preciso revisar" (no máximo 2);
3. tópicos espaçados do dia (aquecimento do cronograma: 1, 3 e 7 dias atrás);
4. tópicos da matéria a partir do tópico do dia, com modelos de frase em rodízio.
As origens 1 e 2 juntas ocupam no máximo `count - 1` vagas: sempre sobra uma para tópico.
"""

import re
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.schedule import Schedule, today_for
from developer_myself.learning.application.questions import QUESTIONS_PER_REVIEW
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    QUESTION_MAX_LENGTH,
    QuestionSource,
    RecallQuestion,
)

MAX_FROM_TO_REVIEW = 2
ITEM_MAX_LENGTH = 400

TEMPLATES = {
    "learner_question": "{}",
    "explain_to_review": "Explique sem consultar: {}",
    "recall_topic": "O que você lembra de {}? Explique com um exemplo seu.",
    "when_to_use": "Quando usar {} e quando não usar?",
    "teach_beginner": "Explique {} para quem está começando.",
}
TOPIC_ROTATION = ("recall_topic", "when_to_use", "teach_beginner")

_BULLET = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s*")
_DAYS_AGO = re.compile(r"\s*\(\d+ dias? atrás\)$")

type Candidate = tuple[QuestionSource, str, str]  # origem, modelo, tópico
_PERSONAL = {QuestionSource.LEARNER, QuestionSource.TO_REVIEW}


def _cut(text: str) -> str:
    return text if len(text) <= ITEM_MAX_LENGTH else text[:ITEM_MAX_LENGTH] + "…"


def to_review_items(text: str | None) -> list[str]:
    """Itens do "preciso revisar": um por linha, sem marcadores, sem vazios."""
    items = (_BULLET.sub("", line).strip() for line in (text or "").splitlines())
    return [item for item in items if item]


@dataclass(frozen=True, slots=True)
class RuleQuestionPicker:
    schedules: Callable[[str], Schedule] = field(default=schedule_for)

    def pick(
        self,
        plan: StudyPlan,  # noqa: ARG002 - parte do port (a IA vai usar)
        content: Content,
        now: datetime,  # noqa: ARG002 - parte do port (a IA vai usar)
        count: int = QUESTIONS_PER_REVIEW,
    ) -> tuple[RecallQuestion, ...]:
        questions = list(self._learner(content, count - 1))
        seen = {q.text for q in questions}
        for source, template, topic in self._candidates(content):
            personal = sum(1 for q in questions if q.source in _PERSONAL)
            if source in _PERSONAL and personal >= count - 1:
                continue
            text = TEMPLATES[template].format(_cut(topic))
            if text in seen:
                continue
            seen.add(text)
            questions.append(
                RecallQuestion(
                    id=uuid.uuid7(),
                    text=text,
                    source=source,
                    template=template,
                    topic=topic[:QUESTION_MAX_LENGTH],
                )
            )
            if len(questions) == count:
                break
        return tuple(questions)

    @staticmethod
    def _learner(content: Content, limit: int) -> Iterator[RecallQuestion]:
        for lq in content.learner_questions[:limit]:
            yield RecallQuestion(
                id=lq.id,
                text=lq.text,
                source=QuestionSource.LEARNER,
                template="learner_question",
                expected_answer=lq.answer,
            )

    def _candidates(self, content: Content) -> Iterator[Candidate]:
        for item in to_review_items(content.last_to_review)[:MAX_FROM_TO_REVIEW]:
            yield QuestionSource.TO_REVIEW, "explain_to_review", item
        schedule = self.schedules(content.title.value)
        day = schedule.day(today_for(content.points.value))
        for warm in day.warmup:
            yield QuestionSource.SPACED_TOPIC, "recall_topic", _DAYS_AGO.sub("", warm)
        topics = schedule.entry.topics or (f"visão geral de {schedule.entry.title}",)
        start = next((i for i, t in enumerate(topics) if t in day.focus), 0)
        for turn in range(len(TOPIC_ROTATION)):
            for offset in range(len(topics)):
                topic = topics[(start + offset) % len(topics)]
                template = TOPIC_ROTATION[(turn + offset) % len(TOPIC_ROTATION)]
                yield QuestionSource.TOPIC, template, topic
