"""Garante que o catálogo cobre CADA item do "Mapa de conteúdos" (Docs/).

`tests/fixtures/mapa_itens.txt` é extraído do PDF por `extract_map_items.py`. Todo termo
relevante de cada item precisa aparecer em algum tópico do catálogo; se o mapa mudar,
re-extraia o arquivo e este teste aponta o que falta.
"""

import re
import unicodedata
from pathlib import Path

import pytest

from developer_myself.curriculum.domain.catalog import CATALOG

FIXTURES = Path(__file__).parents[1] / "fixtures"
ITEMS_FILE = FIXTURES / "mapa_itens.txt"
# Lista do perfil em T (fundamentos + inteligência + DFIR), colada pelo aprendiz em 2026-11-02.
T_PROFILE_FILE = FIXTURES / "perfil_t_itens.txt"

# Palavras de ligação ou de redação do PDF, que não são conteúdo a estudar.
FILLER = set(
    [
        "e",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "em",
        "o",
        "a",
        "os",
        "as",
        "com",
        "por",
        "para",
        "no",
        "na",
        "nos",
        "nas",
        "um",
        "uma",
        "ou",
        "que",
        "se",
        "sem",
        "seu",
        "sua",
        "como",
        "ao",
        "aos",
        "sobre",
        "entre",
        "agora",
        "faz",
        "parte",
        "desta",
        "categoria",
        "lista",
        "atual",
        "nova",
        "novo",
        "incluindo",
        "quando",
        "algo",
        "the",
        "and",
        "of",
        "or",
        "for",
        "vs",
        "seus",
        "suas",
        "mais",
    ]
)


def words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    found = re.findall(r"[a-z0-9][a-z0-9.+#/-]*[a-z0-9+#]|[a-z0-9]", text)
    return [w for w in found if w not in FILLER and len(w) > 1]


_TERMS = [w for e in CATALOG for t in (e.title, *e.topics, e.note) for w in words(t)]
# "node.js" também cobre "node"; "go.sum" cobre "go".
CATALOG_WORDS = set(_TERMS) | {part for w in _TERMS if "." in w for part in w.split(".") if part}


def _items(path: Path) -> list[list[str]]:
    return [line.split(" :: ", 1) for line in path.read_text().splitlines() if " :: " in line]


ITEMS = _items(ITEMS_FILE)
T_ITEMS = _items(T_PROFILE_FILE)


def test_fixture_has_every_block() -> None:
    assert len(ITEMS) >= 240
    assert len({block for block, _ in ITEMS}) >= 44


@pytest.mark.parametrize(("block", "item"), ITEMS, ids=[i[:60] for _, i in ITEMS])
def test_every_map_item_is_in_the_catalog(block: str, item: str) -> None:
    missing = sorted({w for w in words(item) if w not in CATALOG_WORDS})
    assert not missing, f"[{block}] {item}\n  termos fora do catálogo: {missing}"


@pytest.mark.parametrize(("block", "item"), T_ITEMS, ids=[i[:60] for _, i in T_ITEMS])
def test_every_t_profile_item_is_in_the_catalog(block: str, item: str) -> None:
    missing = sorted({w for w in words(item) if w not in CATALOG_WORDS})
    assert not missing, f"[{block}] {item}\n  termos fora do catálogo: {missing}"
