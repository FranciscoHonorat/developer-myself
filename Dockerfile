# syntax=docker/dockerfile:1
# Imagem única para `api` e `worker` (mesmo código, comandos diferentes — ADR-0010).
# Digests fixos: atualize com `docker pull <imagem>` + `docker image inspect`.

# ---------- 1. build do frontend
FROM node:26-slim@sha256:e4db4c914bf8ad241bd24804fc25d272d89bad97e68cdc8a1414862790a02c39 AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npx tsc -b && npx vite build

# ---------- 2. dependências Python (só main)
FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913 AS build
ENV POETRY_VIRTUALENVS_IN_PROJECT=true POETRY_NO_INTERACTION=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir "poetry==2.5.1"
WORKDIR /app
COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry sync --only main --no-root
COPY backend/src ./src
RUN poetry sync --only main

# ---------- 3. runtime
FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    DM_STATIC_DIR=/app/web FORWARDED_ALLOW_IPS=127.0.0.1
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/src ./src
COPY --from=web /web/dist ./web
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"]
CMD ["uvicorn", "developer_myself.entrypoints.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
