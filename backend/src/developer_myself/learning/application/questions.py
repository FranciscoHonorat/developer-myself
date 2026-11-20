"""Port de quem escolhe as perguntas do teste de memória (regra hoje; IA depois)."""

from datetime import datetime
from typing import Protocol

from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import RecallQuestion


class QuestionPicker(Protocol):
    def pick(self, plan: StudyPlan, content: Content, now: datetime) -> tuple[RecallQuestion, ...]:
        """As perguntas da revisão que está começando, na ordem em que aparecem."""
        ...
