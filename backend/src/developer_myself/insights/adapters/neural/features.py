"""Engenharia de features: transforma um candidato em números na faixa [0, 1].

Redes neurais aprendem mal com escalas muito diferentes (dias vão a 365, nível vai a 2),
por isso tudo é normalizado. Contagens e dias usam log: a diferença entre 1 e 7 dias
importa mais que a diferença entre 200 e 206.

v2: 4 → 9 features. As novas descrevem a HISTÓRIA do conteúdo, não só o estado atual.
"""

import math

from developer_myself.insights.application.recommender import ReviewCandidate

FEATURE_NAMES = (
    "log_days_since_last",
    "points",
    "level",
    "challenges",
    "log_review_count",
    "log_knowledge_age",
    "last_recall_known",  # 0 = nunca revisado (a nota abaixo vira neutra)
    "last_recall",
    "log_avg_notes_chars",
)
MAX_DAYS = 365
MAX_AGE_DAYS = 730
MAX_REVIEWS = 50
MAX_NOTES_CHARS = 2_000


def _log_scale(value: float, maximum: float) -> float:
    return math.log1p(min(max(value, 0.0), maximum)) / math.log1p(maximum)


def to_features(c: ReviewCandidate) -> list[float]:
    known = c.last_recall_rating is not None
    return [
        _log_scale(c.days_since_last_session, MAX_DAYS),
        min(c.points, 60) / 60,
        c.level_rank / 2,
        min(c.challenges_solved, 9) / 9,
        _log_scale(c.review_count, MAX_REVIEWS),
        _log_scale(c.days_since_first_session, MAX_AGE_DAYS),
        1.0 if known else 0.0,
        (c.last_recall_rating - 1) / 3 if c.last_recall_rating is not None else 0.5,
        _log_scale(c.avg_notes_chars, MAX_NOTES_CHARS),
    ]
