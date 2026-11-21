"""Tradução learning → insights (só dados primitivos): quem pode ser revisado e com que sinais."""

from datetime import datetime

from developer_myself.insights.application.recommender import ReviewCandidate
from developer_myself.learning.domain.study_plan import StudyPlan

SECONDS_PER_DAY = 86_400


def review_candidates(plan: StudyPlan, now: datetime) -> list[ReviewCandidate]:
    candidates = []
    for content in plan.contents:
        if not content.is_reviewable:
            continue
        last = content.last_session_at or content.finished_at or content.queued_at
        candidates.append(
            ReviewCandidate(
                content_id=str(content.id),
                title=content.title.value,
                days_since_last_session=max(0.0, (now - last).total_seconds() / SECONDS_PER_DAY),
                points=content.points.value,
                level_rank=plan.level_of(content).rank,
                challenges_solved=len(content.solved_challenge_levels),
                review_count=content.review_count,
                days_since_first_session=(
                    (now - content.first_session_at).total_seconds() / SECONDS_PER_DAY
                    if content.first_session_at
                    else 0.0
                ),
                last_recall_rating=(
                    int(content.last_recall_rating) if content.last_recall_rating else None
                ),
                avg_notes_chars=content.avg_notes_chars,
            )
        )
    return candidates
