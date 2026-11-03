"""Ports de infraestrutura usados pelos casos de uso."""

from developer_myself.learning.domain.repository import StudyPlanRepository
from developer_myself.shared.clock import Clock

__all__ = ["Clock", "StudyPlanRepository"]
