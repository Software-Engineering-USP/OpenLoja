#!/usr/bin/env bash
# Roda localmente as mesmas verificações do CI (.github/workflows/ci.yml):
# lint, testes e build + smoke test da imagem Docker.
# Só precisa de Docker; nada é instalado na máquina.
#
# Uso: scripts/ci.sh            # tudo
#      scripts/ci.sh --no-docker  # só lint e testes
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_IMAGE="python:3.12-slim"
PIP_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/pip"
mkdir -p "$PIP_CACHE"

echo "==> Lint e testes ($PYTHON_IMAGE)"
# roda com o seu usuário para não deixar arquivos de root no repositório
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PIP_CACHE:/tmp/.cache/pip" \
  -v "$PWD:/w" -w /w \
  "$PYTHON_IMAGE" sh -euc '
    pip install --user -q --disable-pip-version-check --default-timeout=120 \
      -r requirements-dev.txt
    python -m ruff check --no-cache src tests
    python -m ruff format --no-cache --check src tests
    python -m pytest -q -p no:cacheprovider
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
