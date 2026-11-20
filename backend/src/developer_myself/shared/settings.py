"""Configuração 12-factor: tudo vem do ambiente (ADR-0010)."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DM_", env_file=".env", extra="ignore")

    storage: Literal["memory", "mongo"] = "memory"
    mongo_url: SecretStr = SecretStr("mongodb://localhost:27017/?replicaSet=rs0")
    mongo_db: str = "developer_myself"
    rabbit_url: SecretStr | None = None

    cookie_name: str = "dm_session"
    cookie_secure: bool = True
    session_ttl_days: int = 14

    default_timezone: str = "America/Sao_Paulo"
    static_dir: str | None = None
    log_level: str = "INFO"
    log_json: bool = True

    relay_interval_seconds: float = 1.0

    # Rate limit por IP em /api/* (ADR-0009). 0 desliga a regra.
    # Escritas: o caderno salva sozinho a cada ~1 s parado, então 120/min deixa folga.
    rate_limit_reads_per_minute: int = 600
    rate_limit_writes_per_minute: int = 120
    rate_limit_registers_per_hour: int = 5
    rate_limit_exports_per_minute: int = 5

    # Trilha: quantos conteúdos podem estar em andamento ao mesmo tempo (ADR-0002, I1)
    max_parallel_contents: int = 3

    # Rede neural (ADR-0012)
    retrain_interval_seconds: float = 3_600.0
    retrain_min_new_labels: int = 5
    model_reload_seconds: float = 60.0
