"""Entrada da API: `uvicorn developer_myself.main:app`."""

from developer_myself.bootstrap import create_app

app = create_app()
