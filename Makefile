# Única interface de comandos: pessoas, pre-commit e CI chamam os mesmos alvos (ADR-0007).
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Usa as versões do .tool-versions via mise, se ele estiver instalado.
RUN := $(if $(shell command -v mise 2>/dev/null),mise exec --,)
PY  := cd backend && $(RUN) poetry run
WEB := cd frontend && $(RUN)

# Imagem publicada pelo CD (job `publish` do CI). TAG = latest ou o SHA de um commit da master.
IMAGE_REPO := ghcr.io/franciscohonorat/developer-myself
TAG ?= latest
UNIT_DIR := $(HOME)/.config/systemd/user

.PHONY: help install fmt lint typecheck test test-unit test-bdd test-http test-arch test-int \
        test-web e2e audit check train retrain models schedule-doc backfill-to-review map-items up down logs \
        deploy verify-image autodeploy-on autodeploy-off autodeploy-logs

help: ## Lista os alvos
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências (backend + frontend + navegador do e2e)
	cd backend && $(RUN) poetry sync
	$(WEB) npm ci
	$(WEB) npx playwright install chromium

fmt: ## Formata o código
	$(PY) ruff format src tests
	$(PY) ruff check --fix src tests
	$(WEB) npx biome check --write .

lint: ## Lint (Ruff + Biome)
	$(PY) ruff format --check src tests
	$(PY) ruff check src tests
	$(WEB) npx biome check .

typecheck: ## mypy --strict + tsc
	$(PY) mypy
	$(WEB) npx tsc -b

test: test-unit test-bdd test-http test-arch ## Testes rápidos (sem Docker)

test-unit: ## Unitários do domínio, com gate de 100% de branches
	$(PY) pytest tests/unit tests/features -q \
	  --cov=developer_myself.learning.domain --cov=developer_myself.curriculum.domain --cov-branch --cov-report=term-missing:skip-covered \
	  --cov-fail-under=100

test-bdd: ## Cenários Gherkin (pt) via casos de uso
	$(PY) pytest tests/features -v

test-http: ## Adapter HTTP (em memória)
	$(PY) pytest tests/http -q

test-arch: ## Regra de dependência (AST)
	$(PY) pytest tests/architecture -q

test-int: ## Integração com Mongo e RabbitMQ reais (Testcontainers, precisa de Docker)
	$(PY) pytest tests/integration -q

test-web: ## Vitest + Testing Library
	$(WEB) npx vitest run

e2e: ## Smoke e2e em BDD (playwright-bdd) contra a API real em memória
	$(WEB) npx vite build
	$(WEB) npm run e2e

audit: ## Supply chain: pip-audit + npm audit
	$(PY) pip-audit --skip-editable
	$(WEB) npm audit --omit=dev

check: lint typecheck test test-web test-int ## Tudo que o CI roda

train: ## Treina a rede neural de recomendação de revisão (gera model.json)
	$(PY) python -m developer_myself.entrypoints.cli.train

retrain: ## Retreina AGORA com suas autoavaliações (stack no ar; o worker também faz sozinho)
	docker compose exec worker python -m developer_myself.entrypoints.cli.retrain --force

models: ## Lista os modelos do registro (ativo primeiro) com as métricas principais
	docker compose exec -T mongo mongosh --quiet developer_myself --eval 'db.ml_models.find({}, {active:1, created_at:1, "payload.metadata.real_samples":1, "payload.metadata.val_log_loss":1, "payload.metadata.promoted":1}).sort({created_at:-1}).limit(10).forEach(printjson)'

schedule-doc: ## Gera Docs/Cronograma de estudos.md a partir da sua trilha (stack no ar)
	docker compose exec -T api python -m developer_myself.entrypoints.cli.schedule_doc > "Docs/Cronograma de estudos.md"
	@echo "Gerado: Docs/Cronograma de estudos.md"

backfill-to-review: ## Preenche o "preciso revisar" das matérias a partir do histórico (stack no ar)
	docker compose exec -T api python -m developer_myself.entrypoints.cli.backfill_to_review

map-items: ## Re-extrai os itens do PDF do mapa (o teste de cobertura usa) — rode quando o PDF mudar
	pdftotext -layout "Docs/Mapa de conteúdos Fullstack, AppSec e DevOps.pdf" - \
	  | python3 backend/tests/fixtures/extract_map_items.py > backend/tests/fixtures/mapa_itens.txt
	@echo "Itens: $$(wc -l < backend/tests/fixtures/mapa_itens.txt). Rode: make test-unit"

up: ## Sobe tudo com Docker Compose (http://localhost:8000)
	@test -f .env || (cp .env.example .env && echo "Criei .env a partir de .env.example — troque a senha do RabbitMQ.")
	docker compose up -d --build
	@echo "Pronto: http://localhost:8000  (RabbitMQ: http://localhost:15672)"

deploy: ## Sobe a imagem do CD se mudou (verifica atestação, health check, rollback). TAG=<sha> fixa
	./scripts/deploy.sh $(TAG)

autodeploy-on: ## Liga o deploy contínuo: timer do systemd (usuário) roda o deploy a cada 5 min
	mkdir -p $(UNIT_DIR)
	sed 's|@REPO@|$(CURDIR)|g' deploy/systemd/developer-myself-deploy.service > $(UNIT_DIR)/developer-myself-deploy.service
	cp deploy/systemd/developer-myself-deploy.timer $(UNIT_DIR)/
	systemctl --user daemon-reload
	systemctl --user enable --now developer-myself-deploy.timer
	@echo "Ligado. Acompanhe: make autodeploy-logs  (sem login aberto: loginctl enable-linger $$USER)"

autodeploy-off: ## Desliga o deploy contínuo
	-systemctl --user disable --now developer-myself-deploy.timer
	rm -f $(UNIT_DIR)/developer-myself-deploy.service $(UNIT_DIR)/developer-myself-deploy.timer
	systemctl --user daemon-reload

autodeploy-logs: ## Histórico dos deploys automáticos
	systemctl --user list-timers developer-myself-deploy.timer --no-pager
	journalctl --user -u developer-myself-deploy.service -n 50 --no-pager

verify-image: ## Confere a proveniência (atestação SLSA) da imagem antes do deploy
	docker pull $(IMAGE_REPO):$(TAG)
	gh attestation verify oci://$(IMAGE_REPO):$(TAG) --repo FranciscoHonorat/developer-myself

down: ## Derruba os containers (os dados ficam nos volumes)
	docker compose down

logs: ## Logs da API e do worker
	docker compose logs -f api worker
