"""Liga os arquivos .feature (documentação viva) aos step definitions do conftest."""

from pytest_bdd import scenarios

scenarios(
    "pontuacao.feature",
    "desbloqueio.feature",
    "sessoes.feature",
    "desafios.feature",
    "conclusao.feature",
    "autoavaliacao.feature",
    "gerenciar.feature",
    "paralelo.feature",
    "reordenar.feature",
)
