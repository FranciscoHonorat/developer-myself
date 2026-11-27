"""Política de desbloqueio da trilha: até N em andamento, competências diferentes e
preferência pelo que se INTERLIGA (afinidade) com o que já está em andamento.

Satisfaz o Protocol `UnlockPolicy` do `learning` por estrutura (sem importá-lo).
"""

from dataclasses import dataclass

from developer_myself.curriculum.domain.competencies import skills_for

STRONG, MEDIUM = 1.0, 0.5
# Hábito diário (2 pomodoros por dia na semana), fora das vagas: o Inglês.
DAILY_COMPETENCIES = frozenset({"ingles"})

# Pares de competências que se reforçam quando estudadas juntas.
AFFINITY_PAIRS: dict[frozenset[str], float] = {
    frozenset(pair): weight
    for weight, pairs in (
        (
            STRONG,
            (
                ("dfir", "windows"), ("dfir", "malware"), ("dfir", "threat_intel"),
                ("malware", "threat_intel"), ("threat_intel", "osint"), ("osint", "darkweb"),
                ("threat_intel", "darkweb"), ("go", "backend"), ("backend", "dados"),
                ("backend", "appsec"), ("appsec", "devsecops"), ("devops", "devsecops"),
                ("devops", "fundamentos"), ("python", "ia"), ("frontend", "backend"),
                ("engenharia", "backend"), ("ageis", "engenharia"), ("comunicacao", "ingles"),
                ("windows", "fundamentos"),
            ),
        ),
        (
            MEDIUM,
            (
                ("dfir", "fundamentos"), ("malware", "appsec"), ("go", "devops"),
                ("python", "dfir"), ("python", "backend"), ("go", "dfir"), ("dados", "python"),
                ("engenharia", "go"), ("ingles", "espanhol"), ("comunicacao", "ageis"),
                ("dfir", "devsecops"), ("threat_intel", "appsec"), ("malware", "windows"),
                ("fundamentos", "appsec"), ("python", "malware"),
            ),
        ),
    )
    for pair in pairs
}  # fmt: skip


def primary_competency(title: str) -> str:
    """A competência de maior peso do conteúdo (empate: a primeira listada)."""
    weights = skills_for(title)
    return max(weights, key=lambda kw: kw[1])[0]


def affinity(a: str, b: str) -> float:
    return 0.0 if a == b else AFFINITY_PAIRS.get(frozenset((a, b)), 0.0)


@dataclass(frozen=True, slots=True)
class CatalogUnlockPolicy:
    max_in_progress: int = 3
    daily_competencies: frozenset[str] = DAILY_COMPETENCIES

    def competency_of(self, title: str) -> str:
        return primary_competency(title)

    def affinity(self, a: str, b: str) -> float:
        return affinity(a, b)
