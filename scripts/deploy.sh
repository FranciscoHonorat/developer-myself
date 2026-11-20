#!/usr/bin/env bash
# Deploy contínuo por *pull* (ADR-0010): sobe a imagem publicada pelo CD se ela mudou.
#
#   scripts/deploy.sh            # latest (é o que o timer do systemd roda)
#   scripts/deploy.sh <sha>      # fixa uma versão / rollback manual
#
# Passos: pull → nada mudou? sai → verifica a atestação (proveniência do CI) →
# guarda a versão atual como :previous → sobe pelo digest → espera /readyz →
# se não ficar pronto, volta para :previous e falha.
#
# Imagem que falhou fica em .deploy/failed-image e o timer não tenta de novo
# (DM_FORCE=1 força). Se a imagem nova sobe o SCHEMA_VERSION, faz backup do Mongo
# antes e só volta para :previous se nenhum documento já foi regravado na versão
# nova (o código antigo recusa schema mais novo).
set -euo pipefail

REPO_SLUG="FranciscoHonorat/developer-myself"
IMAGE="ghcr.io/franciscohonorat/developer-myself"
TAG="${1:-latest}"
PREVIOUS="developer-myself:previous"
READY_URL="http://127.0.0.1:8000/readyz"
READY_TIMEOUT="${DM_READY_TIMEOUT:-90}"
STATE_DIR=".deploy"
FAILED_FILE="$STATE_DIR/failed-image"

cd "$(dirname "$0")/.."
log() { printf '%s deploy: %s\n' "$(date -Is)" "$*"; }
mkdir -p "$STATE_DIR"

# SCHEMA_VERSION do documento da trilha que o código da imagem grava (0 se não souber).
schema_of() {
  docker run --rm --entrypoint python "$1" -c \
    'from developer_myself.learning.adapters.mongo.repository import SCHEMA_VERSION as v; print(v)' \
    2>/dev/null || echo 0
}
mongo_db() {
  local db
  db=$(sed -n 's/^DM_MONGO_DB=//p' .env 2>/dev/null | tail -1)
  echo "${db:-developer_myself}"
}
# Quantas trilhas já foram regravadas numa versão acima de $1.
plans_above() {
  docker compose exec -T mongo mongosh --quiet "$(mongo_db)" --eval \
    "db.study_plans.countDocuments({schema_version: {\$gt: $1}})"
}

# Um deploy por vez (timer + `make deploy` manual ao mesmo tempo).
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/developer-myself-deploy.lock"
flock -n 9 || { log "outro deploy em andamento; saindo"; exit 0; }

if [[ ! -f .env ]]; then
  cp .env.example .env
  log "criei .env a partir de .env.example — troque a senha do RabbitMQ"
fi

docker pull --quiet "$IMAGE:$TAG" >/dev/null
new_id=$(docker image inspect --format '{{.Id}}' "$IMAGE:$TAG")
digest=$(docker image inspect --format '{{index .RepoDigests 0}}' "$IMAGE:$TAG")

running_cid=$(docker compose ps --quiet api 2>/dev/null || true)
running_id=""
if [[ -n "$running_cid" ]]; then
  running_id=$(docker inspect --format '{{.Image}}' "$running_cid")
fi

if [[ "$new_id" == "$running_id" ]]; then
  log "já está em $digest; nada a fazer"
  exit 0
fi

if [[ "${DM_FORCE:-0}" != "1" && -f "$FAILED_FILE" && "$(cat "$FAILED_FILE")" == "$new_id" ]]; then
  log "$digest já falhou antes; não tento de novo (DM_FORCE=1 força)"
  exit 0
fi

# Só sobe imagem que comprovadamente saiu do CI deste repositório.
if [[ "${DM_SKIP_VERIFY:-0}" != "1" ]]; then
  gh attestation verify "oci://$digest" --repo "$REPO_SLUG" >/dev/null
  log "atestação verificada: $digest"
fi

old_schema=0
new_schema=0
if [[ -n "$running_id" ]]; then
  docker tag "$running_id" "$PREVIOUS"
  old_schema=$(schema_of "$running_id")
  new_schema=$(schema_of "$new_id")
  if ((new_schema > old_schema)); then
    backup="$STATE_DIR/backup-$(date +%Y%m%dT%H%M%S)-schema$old_schema.archive.gz"
    docker compose exec -T mongo mongodump --quiet --archive --gzip --db "$(mongo_db)" >"$backup"
    log "schema $old_schema → $new_schema: backup do Mongo em $backup"
  fi
fi

log "subindo $digest"
DM_IMAGE="$digest" docker compose up -d --no-build api worker

for ((i = 0; i < READY_TIMEOUT; i += 3)); do
  if curl -fsS --max-time 2 "$READY_URL" >/dev/null 2>&1; then
    rm -f "$FAILED_FILE"
    log "no ar e pronto: $digest"
    exit 0
  fi
  sleep 3
done

log "não ficou pronto em ${READY_TIMEOUT}s"
echo "$new_id" >"$FAILED_FILE"
if [[ -n "$running_id" ]]; then
  if ((new_schema > old_schema)) && (( $(plans_above "$old_schema") > 0 )); then
    log "SEM rollback: há trilhas já em schema $new_schema e o código anterior não lê."
    log "Para voltar: restaure ${backup:-o backup} (mongorestore --drop) e rode scripts/deploy.sh <sha anterior>"
    exit 1
  fi
  log "rollback para a versão anterior"
  DM_IMAGE="$PREVIOUS" docker compose up -d --no-build api worker
fi
exit 1
