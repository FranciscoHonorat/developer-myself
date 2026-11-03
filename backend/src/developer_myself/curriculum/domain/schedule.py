"""Cronograma diário de um conteúdo: 30 dias, de Iniciante a Avançado.

Casamento com as regras do `learning` (ADR-0002):
- 1 sessão pontuada por dia = 1 ponto  →  o "dia de hoje" é `pontos + 1`.
- Dias 1 a 10: fundamentos + 3 desafios de Intermediário  →  Intermediário no dia 10
  (o conteúdo é consolidado e o próximo da fila é liberado).
- Dias 11 a 30: viram sessões de REVISÃO (aprofundar, praticar, ensinar) + 3 desafios de
  Avançado  →  Avançado no dia 30 (só então é possível concluir).

Método de estudo do mapa: checklist de 5 perguntas sem olhar a fonte; nota < 3 relê,
nota ≥ 3 vai para a prática; revisão de memória em 1 dia, 3 dias e 1 semana.
"""

import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum

TOTAL_DAYS = 30
INTERMEDIATE_DAY = 10
SPACED_REVIEW_OFFSETS = (1, 3, 7)  # revise de memória em 1 dia, 3 dias e 1 semana


class Depth(StrEnum):
    PROFUNDO = "Profundo"
    FUNCIONAL = "Funcional"
    NOCAO = "Noção"

    @property
    def goal(self) -> str:
        return {
            Depth.PROFUNDO: "Dominar e conseguir ensinar: explica trade-offs e resolve um "
            "problema real sem consultar.",
            Depth.FUNCIONAL: "Trabalhar com autonomia: faz a tarefa consultando a documentação.",
            Depth.NOCAO: "Saber que existe e quando usar: explica em duas frases e sabe quando "
            "chamar um especialista.",
        }[self]


class DayKind(StrEnum):
    STUDY = "STUDY"
    PRACTICE = "PRACTICE"
    CHALLENGE = "CHALLENGE"
    TEACH = "TEACH"
    REVIEW = "REVIEW"


class Phase(StrEnum):
    FUNDAMENTOS = "Fundamentos (rumo a Intermediário)"
    APROFUNDAMENTO = "Aprofundamento"
    DOMINIO = "Domínio (rumo a Avançado)"


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    title: str
    area: str
    depth: Depth
    topics: tuple[str, ...]
    practice: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    from_map: bool = True
    note: str = ""

    @property
    def keys(self) -> set[str]:
        return {normalize(self.title), *(normalize(a) for a in self.aliases)}


@dataclass(frozen=True, slots=True)
class DayPlan:
    day: int
    phase: Phase
    kind: DayKind
    focus: str
    activity: str
    warmup: tuple[str, ...] = ()
    target_level: str | None = None  # "INTERMEDIATE" | "ADVANCED" nos dias de desafio


@dataclass(frozen=True, slots=True)
class Schedule:
    entry: CatalogEntry
    days: tuple[DayPlan, ...] = field(default=())

    def day(self, number: int) -> DayPlan:
        return self.days[min(max(number, 1), TOTAL_DAYS) - 1]


def normalize(title: str) -> str:
    """Compara títulos ignorando caixa, acentos, marcadores e espaços extras."""
    text = unicodedata.normalize("NFKD", title.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("•", " ").replace("·", " ")
    return " ".join(text.split()).strip(" -:")


def today_for(points: int) -> int:
    """Cada sessão pontuada conclui um dia do cronograma."""
    return min(points + 1, TOTAL_DAYS)


# --------------------------------------------------------------------------- geração


def _chunks(topics: tuple[str, ...], slots: int) -> list[str]:
    """Distribui N tópicos em `slots` dias (junta tópicos quando há mais tópicos que dias)."""
    if not topics:
        return []
    if len(topics) <= slots:
        return list(topics)
    per = -(-len(topics) // slots)  # teto
    return [" + ".join(topics[i : i + per]) for i in range(0, len(topics), per)]


def _fill(items: list[str], fillers: list[str], size: int) -> list[str]:
    result = items[:size]
    i = 0
    while len(result) < size:
        result.append(fillers[i % len(fillers)])
        i += 1
    return result


def build_schedule(entry: CatalogEntry) -> Schedule:
    topics = entry.topics or (f"visão geral de {entry.title}",)
    half = (len(topics) + 1) // 2  # metade dos tópicos em cada fase de estudo
    first = _chunks(topics[:half], 7)
    second = _chunks(topics[half:], 7)
    # Completa os 7 dias de estudo de cada fase repetindo, em ciclo, a prática do que já
    # foi visto (poucos tópicos = mais prática; muitos tópicos = tópicos agrupados).
    study_a = _fill(first, [f"prática guiada: {t}" for t in first], 7)
    study_b = _fill(
        second or [f"a fundo: {t}" for t in topics],
        [f"casos reais e trade-offs: {t}" for t in topics],
        7,
    )

    days: list[DayPlan] = []
    studied_on: dict[int, str] = {}

    def warmups(day: int) -> tuple[str, ...]:
        return tuple(
            f"{studied_on[day - off]} ({off} {'dia' if off == 1 else 'dias'} atrás)"
            for off in SPACED_REVIEW_OFFSETS
            if day - off in studied_on
        )

    new_topics = set(topics)

    def add(day: int, phase: Phase, kind: DayKind, focus: str, activity: str,
            *, level: str | None = None) -> None:  # fmt: skip
        days.append(DayPlan(day, phase, kind, focus, activity, warmups(day), level))
        # Só o PRIMEIRO contato com um tópico agenda revisões de memória (1, 3 e 7 dias).
        if kind is DayKind.STUDY and (focus in new_topics or " + " in focus):
            studied_on[day] = focus
            new_topics.discard(focus)

    # ---- Fase 1: dias 1 a 10 → Intermediário
    for i, topic in enumerate(study_a, start=1):
        if i == 1:
            activity = (
                f"Panorama de {entry.title}: liste o que já sabe, depois estude {topic}. "
                "Feche com o checklist de 5 perguntas sem olhar a fonte."
            )
        else:
            activity = (
                f"Estude {topic}. Sem olhar a fonte: explique, dê um exemplo próprio, "
                "cite um trade-off, anote uma pergunta em aberto e dê nota de 0 a 5 "
                "(abaixo de 3: releia amanhã)."
            )
        kind = DayKind.PRACTICE if topic.startswith("prática guiada") else DayKind.STUDY
        add(i, Phase.FUNDAMENTOS, kind, topic, activity)
    for k, day in enumerate(range(8, 11), start=1):
        topic = topics[(k - 1) % len(topics)]
        add(day, Phase.FUNDAMENTOS, DayKind.CHALLENGE, f"Desafio de Intermediário {k}",
            f"Aplique {topic} num projeto seu que já existe e registre a evidência "
            "(link do commit, PR ou explicação). Cadastre e resolva o desafio na trilha.",
            level="INTERMEDIATE")  # fmt: skip

    # ---- Fase 2: dias 11 a 20 → aprofundar e praticar (sessões de revisão)
    for i, topic in enumerate(study_b, start=11):
        add(i, Phase.APROFUNDAMENTO, DayKind.STUDY, topic,
            f"Aprofunde {topic}: leia a documentação oficial ou um capítulo e compare com "
            "o que você explicou na fase 1. Anote o que mudou na sua compreensão.")  # fmt: skip
    labs = list(entry.practice) or [f"exercícios práticos de {entry.title}"]
    for k, day in enumerate(range(18, 21)):
        lab = labs[k % len(labs)]
        add(day, Phase.APROFUNDAMENTO, DayKind.PRACTICE, f"Laboratório: {lab}",
            f"Pratique em {lab}. Resolva sem consultar primeiro; consulte só ao travar "
            "e registre onde travou.")  # fmt: skip

    # ---- Fase 3: dias 21 a 30 → Avançado
    for k, day in enumerate(range(21, 24)):
        topic = topics[k % len(topics)]
        add(day, Phase.DOMINIO, DayKind.TEACH, f"Ensinar: {topic}",
            f"Técnica Feynman: escreva (ou grave) uma explicação de {topic} para alguém "
            "que está começando. Onde travar é lacuna: volte ao material.")  # fmt: skip
    add(24, Phase.DOMINIO, DayKind.PRACTICE, "Problema real sem consulta",
        f"Resolva um problema real de {entry.title} no seu projeto sem consultar a fonte. "
        f"Meta de profundidade: {entry.depth.goal}")  # fmt: skip
    add(25, Phase.DOMINIO, DayKind.STUDY, "Trade-offs e decisões",
        f"Escreva um ADR curto sobre uma decisão envolvendo {entry.title}: contexto, "
        "opções, escolha e consequências.")  # fmt: skip
    for k, day in enumerate(range(26, 29), start=1):
        topic = topics[-k % len(topics)]
        add(day, Phase.DOMINIO, DayKind.CHALLENGE, f"Desafio de Avançado {k}",
            f"Desafio mais difícil sobre {topic}: resolva sem consultar, explique os "
            "trade-offs e registre a evidência. Cadastre e resolva na trilha.",
            level="ADVANCED")  # fmt: skip
    add(29, Phase.DOMINIO, DayKind.REVIEW, "Revisão geral de memória",
        "Revise de memória TODOS os tópicos antes de abrir o material. Dê nota de 0 a 5 a "
        "cada um e releia os que ficaram abaixo de 3.")  # fmt: skip
    add(30, Phase.DOMINIO, DayKind.TEACH, "Síntese final",
        f"Apresente {entry.title} em 10 minutos (para alguém ou gravado), com um exemplo "
        "do seu projeto. Com 30 pontos e 3 desafios de Avançado, conclua o conteúdo.")  # fmt: skip
    return Schedule(entry=entry, days=tuple(days))


def generic_entry(title: str) -> CatalogEntry:
    """Conteúdo fora do catálogo: cronograma genérico guiado por módulos/capítulos."""
    return CatalogEntry(
        title=title,
        area="Personalizado",
        depth=Depth.FUNCIONAL,
        topics=tuple(f"módulo/capítulo {i} de {title}" for i in range(1, 8)),
        from_map=False,
        note="Conteúdo fora do mapa: o cronograma segue os módulos ou capítulos do material.",
    )
