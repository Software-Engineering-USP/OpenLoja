#!/usr/bin/env bash
# Roda localmente as mesmas verificações do CI (.github/workflows/ci.yml):
# lint, testes e build + smoke test da imagem Docker.
# Só precisa de Docker; nada é instalado na máquina.
#
# Uso: scripts/ci.sh            # tudo
#      scripts/ci.sh --no-docker  # só lint e testes
set -euo pipefail

cd "$(dirname "$0")/.."

UV_IMAGE="ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim"
UV_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/uv"
mkdir -p "$UV_CACHE"

echo "==> Lint e testes ($UV_IMAGE)"
# roda com o seu usuário para não deixar arquivos de root no repositório;
# o ambiente fica em /tmp/venv para não mexer no .venv local
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e UV_CACHE_DIR=/tmp/.cache/uv \
  -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
  -e UV_LINK_MODE=copy \
  -v "$UV_CACHE:/tmp/.cache/uv" \
  -v "$PWD:/w" -w /w \
  "$UV_IMAGE" sh -euc '
    uv sync --locked --quiet
    uv run --no-sync ruff check --no-cache src tests
    uv run --no-sync ruff format --no-cache --check src tests
    uv run --no-sync pytest -q -p no:cacheprovider
  '

if [[ "${1:-}" == "--no-docker" ]]; then
  echo "==> OK (build da imagem pulado)"
  exit 0
fi

echo "==> Build da imagem"
docker build -q -t openloja:ci . >/dev/null

echo "==> Smoke test"
container=$(docker run -d --rm -P -e SECRET_KEY=ci openloja:ci)
trap 'docker stop "$container" >/dev/null 2>&1 || true' EXIT
porta=$(docker port "$container" 8000/tcp | head -n1 | sed 's/.*://')

for _ in $(seq 30); do
  if curl -fs -o /dev/null "http://localhost:$porta/"; then
    echo "==> OK"
    exit 0
  fi
  sleep 1
done

docker logs "$container"
echo "==> Falhou: a aplicação não respondeu em 30s" >&2
exit 1
