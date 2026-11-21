"""Entrada da API: `uvicorn developer_myself.entrypoints.api:app`."""

from developer_myself.composition.container import create_app

app = create_app()
