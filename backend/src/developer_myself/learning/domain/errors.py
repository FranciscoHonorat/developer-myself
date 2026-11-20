"""Erros de domínio do contexto `learning`."""


class DomainError(Exception):
    """Base: violação de regra de negócio."""


class InvalidValueError(DomainError):
    """Um value object recusou o valor."""


class ContentNotFoundError(DomainError):
    pass


class ChallengeNotFoundError(DomainError):
    pass


class ContentLockedError(DomainError):
    """I3: não é possível iniciar sessão (ou resolver desafio) em conteúdo bloqueado."""


class SessionAlreadyActiveError(DomainError):
    """I2: no máximo uma sessão ativa por aprendiz."""


class NoActiveSessionError(DomainError):
    pass


class InvalidTransitionError(DomainError):
    """Transição de estado não permitida para o conteúdo."""


class ChallengeAlreadySolvedError(DomainError):
    pass


class DuplicateContentError(DomainError):
    pass


class ConcurrencyError(Exception):
    """Optimistic lock: o agregado mudou entre a leitura e a gravação."""


class MasteryNotReachedError(DomainError):
    """Só é possível concluir um conteúdo no nível máximo."""


class RecallRatingRequiredError(InvalidValueError):
    """Toda revisão precisa da autoavaliação (rótulo real para a rede neural)."""


class RecallTestRequiredError(InvalidValueError):
    """Revisão com teste de memória só finaliza com as perguntas respondidas e corrigidas."""


class ContentHasProgressError(DomainError):
    """Remover apagaria histórico de pontos, sessões ou desafios: não é permitido."""


class NotebookConflictError(DomainError):
    """O caderno mudou desde que foi aberto (outra aba)."""


class StudyPlanNotFoundError(DomainError):
    pass
