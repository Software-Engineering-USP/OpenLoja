FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    DATABASE_URL=sqlite:////data/database.db \
    UPLOAD_DIR=/data/images

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# usuário sem privilégios; /data guarda o banco SQLite e as imagens enviadas
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data/images \
    && chown -R app:app /data

COPY --chown=app:app src/ ./src/

USER app

EXPOSE 8000

CMD ["uvicorn", "openloja.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
