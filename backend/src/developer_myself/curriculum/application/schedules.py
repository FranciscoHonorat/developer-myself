"""Consulta de cronogramas: catálogo → cronograma de 30 dias (com cache)."""

from functools import lru_cache

from developer_myself.curriculum.domain.catalog import find_entry
from developer_myself.curriculum.domain.schedule import Schedule, build_schedule, generic_entry


@lru_cache(maxsize=512)
def schedule_for(title: str) -> Schedule:
    """Cronograma do conteúdo; fora do catálogo, um cronograma genérico por módulos."""
    return build_schedule(find_entry(title) or generic_entry(title))
