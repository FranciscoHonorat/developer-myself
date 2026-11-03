"""Agregado `StudyPlan`: um por aprendiz, protege as invariantes I1 a I8 (ADR-0002)."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from developer_myself.learning.domain.content import Challenge, Content
from developer_myself.learning.domain.errors import (
    ContentHasProgressError,
    ContentLockedError,
    ContentNotFoundError,
    DuplicateContentError,
    InvalidTransitionError,
    InvalidValueError,
    MasteryNotReachedError,
    NoActiveSessionError,
    RecallRatingRequiredError,
    SessionAlreadyActiveError,
)
from developer_myself.learning.domain.events import (
    ChallengeAdded,
    ChallengeSolved,
    ContentAdded,
    ContentFinished,
    ContentQueued,
    ContentRemoved,
    ContentRenamed,
    ContentUnlocked,
    DomainEvent,
    MasteryLevelReached,
    PointAwarded,
    PointWithheld,
    QueueReordered,
    StudyPreferencesChanged,
    StudySessionAbandoned,
    StudySessionFinished,
    StudySessionStarted,
)
from developer_myself.learning.domain.policies import (
    DefaultMasteryPolicy,
    DefaultScoringPolicy,
    MasteryPolicy,
    ScoringContext,
    ScoringPolicy,
    ScoringResult,
    SingleTrackUnlockPolicy,
    UnlockPolicy,
)
from developer_myself.learning.domain.value_objects import (
    AbandonReason,
    ChallengeId,
    ContentId,
    ContentKind,
    ContentStatus,
    Duration,
    Evidence,
    LearnerId,
    MasteryLevel,
    Notes,
    RecallRating,
    SessionKind,
    StudyPreferences,
    Timezone,
    Title,
    WithheldReason,
)

SESSION_EXPIRY = timedelta(hours=4)
# Escolha da vaga: olha os próximos LOOKAHEAD elegíveis da fila; cada posição a mais custa
# AGING de afinidade, para a ordem de chegada continuar valendo e nada ficar esquecido.
LOOKAHEAD = 5
AGING = 0.25
SECONDS_PER_DAY = 86_400
LEVEL_NAMES = {
    MasteryLevel.BEGINNER: "Iniciante",
    MasteryLevel.INTERMEDIATE: "Intermediário",
    MasteryLevel.ADVANCED: "Avançado",
}
CHALLENGE_DESCRIPTION_MAX = 2_000


@dataclass(frozen=True, slots=True)
class ActiveSession:
    content_id: ContentId
    started_at: datetime


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    """Resposta de `finish_session`: o que o domínio decidiu (a UI só exibe)."""

    content_id: ContentId
    kind: SessionKind
    duration: Duration
    awarded: bool
    reason: WithheldReason | None
    total_points: int
    level: MasteryLevel
    unlocked: ContentId | None


@dataclass(slots=True)
class StudyPlan:
    id: LearnerId
    timezone: Timezone
    contents: list[Content] = field(default_factory=list)
    active_session: ActiveSession | None = None
    last_review_on: date | None = None  # dia LOCAL da última revisão qualificada
    version: int = 0
    scoring_policy: ScoringPolicy = field(default_factory=DefaultScoringPolicy)
    mastery_policy: MasteryPolicy = field(default_factory=DefaultMasteryPolicy)
    unlock_policy: UnlockPolicy = field(default_factory=SingleTrackUnlockPolicy)
    preferences: StudyPreferences = field(default_factory=StudyPreferences)
    _events: list[DomainEvent] = field(default_factory=list, repr=False, init=False)

    # ================================================================== fábrica
    @classmethod
    def create(cls, learner_id: LearnerId, timezone: Timezone) -> StudyPlan:
        return cls(id=learner_id, timezone=timezone)

    # ================================================================== eventos
    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

    @property
    def pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    # ================================================================== consultas
    def content(self, content_id: ContentId) -> Content:
        for content in self.contents:
            if content.id == content_id:
                return content
        raise ContentNotFoundError(f"Conteúdo {content_id} não encontrado.")

    def find_by_title(self, title: str) -> Content | None:
        wanted = title.strip().casefold()
        return next((c for c in self.contents if c.title.value.casefold() == wanted), None)

    @property
    def in_progress_contents(self) -> list[Content]:
        return [c for c in self.contents if c.status is ContentStatus.IN_PROGRESS]

    def competency_of(self, content: Content) -> str:
        return self.unlock_policy.competency_of(content.title.value)

    @property
    def queue(self) -> list[Content]:
        """Fila de bloqueio em ordem de chegada (I5)."""
        locked = [c for c in self.contents if c.status is ContentStatus.LOCKED]
        return sorted(locked, key=lambda c: c.queued_at)

    @property
    def max_level(self) -> MasteryLevel:
        """O nível mais alto que a política define (hoje, Avançado)."""
        return max(self.mastery_policy.requirements(), key=lambda level: level.rank)

    def requires_review(self, now: datetime) -> bool:
        """Regra 2: há algo para revisar HOJE? Quem foi consolidado hoje só conta amanhã
        (o aprendiz acabou de estudá-lo; exigir revisão dele puniria quem segue o plano)."""
        today = self.timezone.local_date(now)
        return any(
            c.is_reviewable
            and (c.consolidated_at is None or self.timezone.local_date(c.consolidated_at) < today)
            for c in self.contents
        )

    def level_of(self, content: Content) -> MasteryLevel:
        """O nível é derivado a cada consulta, nunca armazenado como verdade."""
        return self.mastery_policy.level_for(content.points, content.solved_challenge_levels)

    def reviewed_today(self, now: datetime) -> bool:
        return self.last_review_on == self.timezone.local_date(now)

    def is_expired(self, now: datetime) -> bool:
        return self.active_session is not None and (
            now - self.active_session.started_at > SESSION_EXPIRY
        )

    # ================================================================== comandos
    def add_content(
        self, content_id: ContentId, title: Title, kind: ContentKind, now: datetime
    ) -> Content:
        if self.find_by_title(title.value) is not None:
            raise DuplicateContentError(f"Já existe um conteúdo chamado {title.value!r}.")
        content = Content(
            id=content_id, title=title, kind=kind, status=ContentStatus.LOCKED, queued_at=now
        )
        self.contents.append(content)
        self._record(
            ContentAdded(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content_id.value,
                title=title.value,
                kind=kind,
            )
        )
        self._unlock_next(now)
        blocker = self._blocker(content)
        if content.status is ContentStatus.LOCKED and blocker is not None:
            self._record(
                ContentQueued(
                    learner_id=self.id.value,
                    occurred_at=now,
                    content_id=content_id.value,
                    blocked_by=blocker.id.value,
                    position=self.queue.index(content) + 1,
                )
            )
        return content

    def refresh_queue(self, now: datetime) -> list[ContentId]:
        """Ocupa as vagas livres (ex.: depois que a política passou a permitir mais)."""
        return self._unlock_available(now)

    def start_session(self, content_id: ContentId, now: datetime) -> SessionKind:
        self._expire_stale_session(now)
        if self.active_session is not None:
            raise SessionAlreadyActiveError("Já existe uma sessão em andamento. Finalize-a antes.")
        content = self.content(content_id)
        kind = content.session_kind
        if kind is None:
            raise ContentLockedError(self.lock_reason(content))
        self.active_session = ActiveSession(content_id=content_id, started_at=now)
        self._record(
            StudySessionStarted(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content_id.value,
                kind=kind,
                started_at=now,
            )
        )
        return kind

    def finish_session(
        self, notes: Notes, now: datetime, recall: RecallRating | None = None
    ) -> SessionOutcome:
        session = self._require_active_session()
        content = self.content(session.content_id)
        kind = content.session_kind or SessionKind.STUDY
        duration = Duration.between(session.started_at, now)
        if kind is SessionKind.REVIEW and recall is None:
            raise RecallRatingRequiredError(
                "Diga quanto você lembrava antes desta revisão (1 a 4)."
            )
        rating = recall if kind is SessionKind.REVIEW else None

        if self.is_expired(now):
            return self._abandon_on_finish(content, kind, duration, now)

        level_before = self.level_of(content)
        today = self.timezone.local_date(now)
        result: ScoringResult = self.scoring_policy.evaluate(
            ScoringContext(
                kind=kind,
                duration=duration,
                notes=notes,
                has_reviewable_content=self.requires_review(now),
                last_review_on=self.last_review_on,
                today=today,
            )
        )
        start = session.started_at
        last_contact = (
            (start - content.last_session_at).total_seconds() / SECONDS_PER_DAY
            if content.last_session_at is not None
            else None
        )
        first_contact = (
            (start - content.first_session_at).total_seconds() / SECONDS_PER_DAY
            if content.first_session_at is not None
            else None
        )
        points_before = content.points.value
        challenges_before = len(content.solved_challenge_levels)
        sessions_before = content.session_count
        reviews_before = content.review_count
        avg_notes_before = content.avg_notes_chars
        last_rating_before = int(content.last_recall_rating) if content.last_recall_rating else None
        self.active_session = None
        content._register_session(now, kind, notes.char_count, rating)

        if result.awarded:
            content._award_point()
            if kind is SessionKind.REVIEW:
                self.last_review_on = today
            self._record(
                PointAwarded(
                    learner_id=self.id.value,
                    occurred_at=now,
                    content_id=content.id.value,
                    total_points=content.points.value,
                )
            )
        else:
            self._record(
                PointWithheld(
                    learner_id=self.id.value,
                    occurred_at=now,
                    content_id=content.id.value,
                    reason=result.reason or WithheldReason.TOO_SHORT,
                )
            )

        level_after = self.level_of(content)
        self._record(
            StudySessionFinished(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content.id.value,
                content_title=content.title.value,
                kind=kind,
                started_at=session.started_at,
                finished_at=now,
                duration_seconds=duration.total_seconds,
                notes_studied=notes.studied,
                notes_understood=notes.understood,
                notes_to_review=notes.to_review,
                notes_char_count=notes.char_count,
                days_since_last_contact=round(last_contact) if last_contact is not None else None,
                level_before=level_before,
                level_after=level_after,
                awarded=result.awarded,
                withheld_reason=result.reason,
                recall_rating=int(rating) if rating is not None else None,
                last_contact_days=last_contact,
                points_before=points_before,
                challenges_solved_before=challenges_before,
                session_count_before=sessions_before,
                review_count_before=reviews_before,
                days_since_first_session=first_contact,
                avg_notes_chars_before=avg_notes_before,
                last_recall_rating_before=last_rating_before,
            )
        )
        unlocked = self._on_level_change(content, level_before, now)
        return SessionOutcome(
            content_id=content.id,
            kind=kind,
            duration=duration,
            awarded=result.awarded,
            reason=result.reason,
            total_points=content.points.value,
            level=level_after,
            unlocked=unlocked,
        )

    def cancel_session(self, now: datetime) -> None:
        session = self._require_active_session()
        content = self.content(session.content_id)
        self._abandon(content, AbandonReason.CANCELLED, now)

    def add_challenge(
        self,
        content_id: ContentId,
        challenge_id: ChallengeId,
        description: str,
        target_level: MasteryLevel,
        now: datetime,
    ) -> Challenge:
        content = self.content(content_id)
        cleaned = description.strip()
        if not cleaned:
            raise InvalidValueError("A descrição do desafio não pode ser vazia.")
        if len(cleaned) > CHALLENGE_DESCRIPTION_MAX:
            raise InvalidValueError("Descrição do desafio longa demais.")
        if target_level is MasteryLevel.BEGINNER:
            raise InvalidValueError("Desafios miram Intermediário ou Avançado.")
        challenge = Challenge(
            id=challenge_id, description=cleaned, target_level=target_level, created_at=now
        )
        content.challenges.append(challenge)
        self._record(
            ChallengeAdded(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content_id.value,
                challenge_id=challenge_id.value,
                description=cleaned,
                target_level=target_level,
            )
        )
        return challenge

    def solve_challenge(
        self, content_id: ContentId, challenge_id: ChallengeId, evidence: Evidence, now: datetime
    ) -> MasteryLevel:
        content = self.content(content_id)
        if content.status is ContentStatus.LOCKED:
            raise ContentLockedError(self.lock_reason(content))
        challenge = content.challenge(challenge_id)
        level_before = self.level_of(content)
        challenge._solve(evidence, now)
        self._record(
            ChallengeSolved(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content_id.value,
                challenge_id=challenge_id.value,
                target_level=challenge.target_level,
                evidence=evidence.value,
                seconds_to_solve=int((now - challenge.created_at).total_seconds()),
            )
        )
        self._on_level_change(content, level_before, now)
        return self.level_of(content)

    def finish_content(self, content_id: ContentId, now: datetime) -> ContentId | None:
        content = self.content(content_id)
        if self.active_session is not None and self.active_session.content_id == content_id:
            raise SessionAlreadyActiveError("Finalize a sessão em andamento antes de concluir.")
        current_level = self.level_of(content)
        if current_level is not self.max_level and content.status is not ContentStatus.LOCKED:
            raise MasteryNotReachedError(
                f"{content.title} só pode ser concluído no nível "
                f"{LEVEL_NAMES[self.max_level]} (atual: {LEVEL_NAMES[current_level]})."
            )
        content._finish(now)
        self._record(
            ContentFinished(learner_id=self.id.value, occurred_at=now, content_id=content_id.value)
        )
        return self._unlock_next(now)

    def remove_content(self, content_id: ContentId, now: datetime) -> ContentId | None:
        """Tira da trilha um conteúdo SEM progresso (ex.: repetido) e libera o próximo."""
        content = self.content(content_id)
        if content.has_progress:
            raise ContentHasProgressError(
                f"{content.title} já tem progresso (pontos, sessões ou desafios) e não pode sair."
            )
        if self.active_session is not None and self.active_session.content_id == content_id:
            raise SessionAlreadyActiveError("Cancele a sessão em andamento antes de remover.")
        self.contents.remove(content)
        self._record(
            ContentRemoved(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content_id.value,
                title=content.title.value,
            )
        )
        return self._unlock_next(now)

    def reorder_queue(self, order: list[ContentId], now: datetime) -> None:
        """Os conteúdos dados vão para a frente da fila, nessa ordem; os demais seguem atrás.

        Só a ordem muda (os mesmos horários de chegada são redistribuídos), então o
        desbloqueio continua sendo decidido pelas regras I1 e I5.
        """
        if len(set(order)) != len(order):
            raise InvalidValueError("A nova ordem repete um conteúdo.")
        chosen = [self.content(content_id) for content_id in order]
        for content in chosen:
            if content.status is not ContentStatus.LOCKED:
                raise InvalidTransitionError(
                    f"{content.title} não está na fila e não pode ser reordenado."
                )
        current = self.queue
        new_order = chosen + [c for c in current if c not in chosen]
        # Mesmos horários, redistribuídos; empates viram 1 µs de diferença para a ordem
        # ficar explícita (vários conteúdos podem ter chegado no mesmo instante).
        slots: list[datetime] = []
        for moment in sorted(c.queued_at for c in current):
            slots.append(max(moment, slots[-1] + timedelta(microseconds=1)) if slots else moment)
        for content, slot in zip(new_order, slots, strict=True):
            content.queued_at = slot
        self._record(
            QueueReordered(
                learner_id=self.id.value,
                occurred_at=now,
                order=tuple(c.id.value for c in new_order),
            )
        )

    def rename_content(self, content_id: ContentId, title: Title, now: datetime) -> None:
        content = self.content(content_id)
        existing = self.find_by_title(title.value)
        if existing is not None and existing.id != content_id:
            raise DuplicateContentError(f"Já existe um conteúdo chamado {title.value!r}.")
        if content.title == title:
            return
        old = content.title
        content.title = title
        self._record(
            ContentRenamed(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content_id.value,
                old_title=old.value,
                new_title=title.value,
            )
        )

    def change_preferences(self, preferences: StudyPreferences, now: datetime) -> None:
        if preferences == self.preferences:
            return
        self.preferences = preferences
        self._record(
            StudyPreferencesChanged(
                learner_id=self.id.value,
                occurred_at=now,
                minutes_per_day=preferences.minutes_per_day,
                rest_days=tuple(sorted(preferences.rest_days)),
            )
        )

    def change_timezone(self, timezone: Timezone) -> None:
        self.timezone = timezone

    # ================================================================== internos
    def _require_active_session(self) -> ActiveSession:
        if self.active_session is None:
            raise NoActiveSessionError("Não há sessão em andamento.")
        return self.active_session

    def _expire_stale_session(self, now: datetime) -> None:
        """I7: verificação lazy — o próximo comando detecta a sessão abandonada."""
        if self.active_session is not None and self.is_expired(now):
            content = self.content(self.active_session.content_id)
            self._abandon(content, AbandonReason.EXPIRED, now)

    def _abandon(self, content: Content, reason: AbandonReason, now: datetime) -> None:
        session = self._require_active_session()
        self.active_session = None
        self._record(
            StudySessionAbandoned(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content.id.value,
                content_title=content.title.value,
                kind=content.session_kind or SessionKind.STUDY,
                started_at=session.started_at,
                reason=reason,
            )
        )

    def _abandon_on_finish(
        self, content: Content, kind: SessionKind, duration: Duration, now: datetime
    ) -> SessionOutcome:
        self._abandon(content, AbandonReason.EXPIRED, now)
        self._record(
            PointWithheld(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content.id.value,
                reason=WithheldReason.EXPIRED,
            )
        )
        return SessionOutcome(
            content_id=content.id,
            kind=kind,
            duration=duration,
            awarded=False,
            reason=WithheldReason.EXPIRED,
            total_points=content.points.value,
            level=self.level_of(content),
            unlocked=None,
        )

    def _on_level_change(
        self, content: Content, level_before: MasteryLevel, now: datetime
    ) -> ContentId | None:
        level_after = self.level_of(content)
        if level_after.rank <= level_before.rank:
            return None
        self._record(
            MasteryLevelReached(
                learner_id=self.id.value,
                occurred_at=now,
                content_id=content.id.value,
                level=level_after,
            )
        )
        if content.status is ContentStatus.IN_PROGRESS and level_after.at_least(
            MasteryLevel.INTERMEDIATE
        ):
            content._consolidate(now)
            return self._unlock_next(now)
        return None

    def _unlock_next(self, now: datetime) -> ContentId | None:
        unlocked = self._unlock_available(now)
        return unlocked[0] if unlocked else None

    def _unlock_available(self, now: datetime) -> list[ContentId]:
        """I1 + I5: enche as vagas (até `max_in_progress`), uma competência por vaga.

        Entre os próximos elegíveis da fila, vence o que mais se interliga com os que já
        estão em andamento; a ordem de chegada pesa (AGING) e desempata.
        """
        unlocked: list[ContentId] = []
        policy = self.unlock_policy
        while len(self.in_progress_contents) < policy.max_in_progress:
            busy = {self.competency_of(c) for c in self.in_progress_contents}
            eligible = [c for c in self.queue if self.competency_of(c) not in busy][:LOOKAHEAD]
            if not eligible:
                break

            def score(item: tuple[int, Content], busy: set[str] = busy) -> tuple[float, int]:
                position, candidate = item
                comp = self.competency_of(candidate)
                affinity = sum(policy.affinity(comp, other) for other in busy)
                return affinity - AGING * position, -position

            _, nxt = max(enumerate(eligible), key=score)
            nxt._unlock()
            self._record(
                ContentUnlocked(learner_id=self.id.value, occurred_at=now, content_id=nxt.id.value)
            )
            unlocked.append(nxt.id)
        return unlocked

    def _blocker(self, content: Content) -> Content | None:
        """Quem segura este conteúdo: o da mesma competência ou, sem vaga, o primeiro."""
        active = self.in_progress_contents
        comp = self.competency_of(content)
        same = next((c for c in active if self.competency_of(c) == comp), None)
        return same or (active[0] if active else None)

    def lock_reason(self, content: Content) -> str:
        active = self.in_progress_contents
        comp = self.competency_of(content)
        same = next((c for c in active if self.competency_of(c) == comp), None)
        if same is not None:
            return (
                f"{content.title} está bloqueado: conclua {same.title} "
                "ou chegue a Intermediário nele."
            )
        if len(active) >= self.unlock_policy.max_in_progress:
            return (
                f"{content.title} está na fila: já há {len(active)} conteúdos em andamento; "
                "chegue a Intermediário em um deles para abrir uma vaga."
            )
        return f"{content.title} está bloqueado."
