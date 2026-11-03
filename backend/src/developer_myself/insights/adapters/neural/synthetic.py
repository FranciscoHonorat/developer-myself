"""Dados sintéticos para o cold start (ADR-0012).

Enquanto há poucos rótulos reais, simulamos aprendizes com uma curva de esquecimento
de Ebbinghaus:

    P(lembrar) = exp(-dias / estabilidade)

A estabilidade cresce com prática (pontos), domínio (nível), aplicação (desafios),
revisões anteriores e profundidade das anotações; uma última revisão "Esqueci" a reduz.
A rede NÃO recebe essa fórmula: vê só exemplos (features → lembrou 0/1).

Conforme chegam rótulos reais (autoavaliação), eles entram no treino com peso maior e
a rede passa a se ajustar à memória de verdade do aprendiz.
"""

import math
import random

from developer_myself.insights.application.recommender import ReviewCandidate

RATING_EFFECT = {1: -4.0, 2: -1.0, 3: 2.0, 4: 5.0}


def true_recall_probability(c: ReviewCandidate) -> float:
    stability = (
        1.5
        + 0.5 * c.points
        + 5 * c.level_rank
        + 1.0 * c.challenges_solved
        + 2.0 * c.review_count
        + 0.01 * c.avg_notes_chars
        + (RATING_EFFECT[c.last_recall_rating] if c.last_recall_rating else 0.0)
    )
    return math.exp(-c.days_since_last_session / max(stability, 0.5))


def generate(n: int, seed: int = 7) -> list[tuple[ReviewCandidate, float]]:
    rng = random.Random(seed)
    samples = []
    for i in range(n):
        level = rng.choice([0, 1, 1, 2])
        points = max(0, int(rng.gauss(10 + 12 * level, 6)))
        challenges = min(9, 3 * level + rng.randint(0, 2))
        reviews = max(0, int(rng.expovariate(1 / (1 + 3 * level))))
        rating = rng.choice([1, 2, 3, 3, 4]) if reviews else None
        days = rng.expovariate(1 / 20)  # a maioria revisa em semanas; alguns somem por meses
        age = days + rng.expovariate(1 / 60)
        notes = max(50.0, rng.gauss(160, 60))
        candidate = ReviewCandidate(
            f"s{i}",
            f"sintético {i}",
            days,
            points,
            level,
            challenges,
            review_count=reviews,
            days_since_first_session=age,
            last_recall_rating=rating,
            avg_notes_chars=notes,
        )
        remembered = 1.0 if rng.random() < true_recall_probability(candidate) else 0.0
        samples.append((candidate, remembered))
    return samples
