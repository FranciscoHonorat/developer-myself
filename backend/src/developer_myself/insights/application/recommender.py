"""Port `ReviewRecommender` (ADR-0012): qual conteúdo revisar primeiro.

Cada "degrau" (regra simples → FSRS → rede neural) é só um adapter deste port.
Recebe primitivos, nunca o modelo do `learning` (contextos só se falam por IDs/dados).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReviewCandidate:
    content_id: str
    title: str
    days_since_last_session: float
    points: int
    level_rank: int  # 0 Iniciante, 1 Intermediário, 2 Avançado
    challenges_solved: int
    review_count: int = 0
    days_since_first_session: float = 0.0
    last_recall_rating: int | None = None  # 1..4; None = nunca revisado
    avg_notes_chars: float = 0.0


@dataclass(frozen=True, slots=True)
class Recommendation:
    content_id: str
    title: str
    recall_probability: float  # 0..1: chance estimada de ainda lembrar


class ReviewRecommender(Protocol):
    name: str
    metadata: dict[str, object]

    def recall_probability(self, candidate: ReviewCandidate) -> float: ...


def rank(recommender: ReviewRecommender, candidates: list[ReviewCandidate]) -> list[Recommendation]:
    """Menor chance de lembrar primeiro: é o que mais precisa de revisão."""
    scored = [
        Recommendation(c.content_id, c.title, recommender.recall_probability(c)) for c in candidates
    ]
    return sorted(scored, key=lambda r: r.recall_probability)
