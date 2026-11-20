"""Escolha das 3 perguntas do teste de memória por regra fixa."""

from datetime import UTC, datetime

from developer_myself.curriculum.domain.schedule import CatalogEntry, Depth, build_schedule
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    LearnerId,
    Points,
    Timezone,
    Title,
)
from developer_myself.review_questions import RuleQuestionPicker

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)
PLAN = StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))


def content(title: str = "Learning Go", points: int = 10, to_review: str | None = None) -> Content:
    c = PLAN.add_content(ContentId.new(), Title(title), ContentKind.BOOK, NOW)
    PLAN.contents.remove(c)  # só o objeto importa; o plano não é consultado pela regra
    c.points = Points(points)
    c.last_to_review = to_review
    return c


def pick(c: Content, picker: RuleQuestionPicker | None = None) -> list[tuple[str, str]]:
    questions = (picker or RuleQuestionPicker()).pick(PLAN, c, NOW)
    assert len(questions) == 3
    assert len({q.text for q in questions}) == 3
    return [(q.source.value, q.text) for q in questions]


def test_to_review_items_come_first_split_by_line() -> None:
    got = pick(content(to_review="- canais\n- select"))
    assert got[:2] == [
        ("TO_REVIEW", "Explique sem consultar: canais"),
        ("TO_REVIEW", "Explique sem consultar: select"),
    ]


def test_at_most_two_from_to_review() -> None:
    got = pick(content(to_review="1. a\n2) b\n* c\n• d\ne"))
    assert [s for s, _ in got].count("TO_REVIEW") == 2
    assert got[0][1] == "Explique sem consultar: a"
    assert got[1][1] == "Explique sem consultar: b"


def test_long_item_is_cut_at_400() -> None:
    item = "x" * 450
    questions = RuleQuestionPicker().pick(PLAN, content(to_review=item), NOW)
    first = questions[0]
    assert first.text == "Explique sem consultar: " + "x" * 400 + "…"
    assert first.topic == item
    assert first.template == "explain_to_review"


def test_blank_bullets_make_no_question() -> None:
    got = pick(content(to_review="- \n•  \n"))
    assert "TO_REVIEW" not in [s for s, _ in got]


def test_spaced_topics_follow() -> None:
    # 11 pontos → dia 12: aquecimento com "goroutines e canais" (1 dia) e "generics" (7 dias).
    got = pick(content(points=11, to_review="canais"))
    assert got == [
        ("TO_REVIEW", "Explique sem consultar: canais"),
        (
            "SPACED_TOPIC",
            "O que você lembra de goroutines e canais? Explique com um exemplo seu.",
        ),
        ("SPACED_TOPIC", "O que você lembra de generics? Explique com um exemplo seu."),
    ]


def test_topics_start_at_the_topic_of_the_day() -> None:
    # 10 pontos → dia 11 ("goroutines e canais"), aquecimento só com "erros…".
    got = pick(content(points=10))
    assert got[0][0] == "SPACED_TOPIC"
    assert got[1] == (
        "TOPIC",
        "O que você lembra de goroutines e canais? Explique com um exemplo seu.",
    )
    assert got[2] == ("TOPIC", "Quando usar context: cancelamento e prazos e quando não usar?")


def test_always_three_distinct_even_with_one_topic() -> None:
    entry = CatalogEntry("Só um", "Teste", Depth.FUNCIONAL, ("canais",))
    picker = RuleQuestionPicker(schedules=lambda _: build_schedule(entry))
    # 7 pontos → dia 8, desafio: o aquecimento traz "canais (7 dias atrás)".
    got = pick(content("Só um", points=7), picker)
    assert got == [
        ("SPACED_TOPIC", "O que você lembra de canais? Explique com um exemplo seu."),
        ("TOPIC", "Quando usar canais e quando não usar?"),
        ("TOPIC", "Explique canais para quem está começando."),
    ]


def test_without_catalog_topics_uses_overview() -> None:
    entry = CatalogEntry("Vazio", "Teste", Depth.FUNCIONAL, ())
    picker = RuleQuestionPicker(schedules=lambda _: build_schedule(entry))
    got = pick(content("Vazio", points=29), picker)
    assert all("visão geral de Vazio" in text for _, text in got)


def test_ids_are_unique() -> None:
    questions = RuleQuestionPicker().pick(PLAN, content(), NOW)
    assert len({q.id for q in questions}) == 3
