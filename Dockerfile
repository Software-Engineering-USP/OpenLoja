# ---- build: instala as dependências do uv.lock (versões exatas, iguais às do CI)
FROM python:3.14-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# só os arquivos de dependências: a camada fica em cache enquanto eles não mudam
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# ---- imagem final: só o Python, o .venv e o código (sem o uv)
FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/app/.venv/bin:$PATH \
    DATABASE_URL=sqlite:////data/database.db \
    UPLOAD_DIR=/data/images

# usuário sem privilégios; /data guarda o banco SQLite e as imagens enviadas
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data/images \
    && chown -R app:app /data

COPY --from=build /app/.venv /app/.venv
COPY --chown=app:app src/ ./src/

USER app

EXPOSE 8000

CMD ["uvicorn", "openloja.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
