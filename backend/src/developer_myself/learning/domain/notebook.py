"""Caderno da matéria: bloco de notas livre, separado do `StudyPlan`.

Não pontua nem gera eventos; só guarda o que o aprendiz escreve com as próprias palavras.
"""

from dataclasses import dataclass
from datetime import datetime

from developer_myself.learning.domain.errors import InvalidValueError, NotebookConflictError
from developer_myself.learning.domain.value_objects import ContentId, LearnerId

NOTEBOOK_MAX_CHARS = 100_000


@dataclass(slots=True)
class Notebook:
    learner_id: LearnerId
    content_id: ContentId
    text: str = ""
    version: int = 0
    updated_at: datetime | None = None

    @classmethod
    def empty(cls, learner_id: LearnerId, content_id: ContentId) -> Notebook:
        return cls(learner_id, content_id)

    @property
    def chars(self) -> int:
        return len(self.text)

    def edit(self, text: str, expected_version: int, now: datetime) -> None:
        """Concorrência otimista: só edita quem viu a versão atual. O repositório incrementa."""
        if expected_version != self.version:
            raise NotebookConflictError(
                "O caderno foi alterado em outro lugar. Recarregue antes de editar."
            )
        if len(text) > NOTEBOOK_MAX_CHARS:
            raise InvalidValueError(f"O caderno aceita até {NOTEBOOK_MAX_CHARS} caracteres.")
        self.text = text
        self.updated_at = now
