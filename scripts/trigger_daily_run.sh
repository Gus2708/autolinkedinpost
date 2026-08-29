#!/usr/bin/env bash
#
# Dispara el workflow diario vía la API de GitHub (workflow_dispatch).
#
# El evento `schedule` de GitHub Actions es best-effort: los disparos se retrasan
# o se descartan bajo carga. Este script existe para que un scheduler externo con
# garantías reales sea el que decida cuándo corre la publicación.
#
# Uso:
#   GH_PAT=ghp_xxx REPO=usuario/repo ./scripts/trigger_daily_run.sh
#
# Variables:
#   GH_PAT  (requerida) Personal Access Token con permiso `actions: write`.
#   REPO    (requerida) Repositorio en formato owner/name.
#   DAYS    (opcional)  Días hacia atrás a revisar. Default: 1.
#   FORCE   (opcional)  "true" para publicar aunque ya haya habido una corrida
#                       reciente. Default: false.
set -euo pipefail

: "${GH_PAT:?Falta GH_PAT (token con permiso actions:write)}"
: "${REPO:?Falta REPO (formato owner/name)}"
DAYS="${DAYS:-1}"
FORCE="${FORCE:-false}"
WORKFLOW="daily_linkedin_post.yml"

echo "[trigger] Disparando ${WORKFLOW} en ${REPO} (days=${DAYS}, force=${FORCE})..."

http_code=$(curl -sS -o /tmp/trigger_resp.txt -w '%{http_code}' \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GH_PAT}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
  -d "{\"ref\":\"main\",\"inputs\":{\"days\":\"${DAYS}\",\"force\":\"${FORCE}\"}}")

# La API devuelve 204 sin cuerpo cuando acepta el disparo.
if [ "$http_code" = "204" ]; then
  echo "[trigger] OK: workflow encolado."
  exit 0
fi

echo "[trigger] ERROR: la API respondió HTTP ${http_code}" >&2
cat /tmp/trigger_resp.txt >&2
exit 1
