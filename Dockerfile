FROM python:3.14-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# usuário sem privilégios; /data guarda o SQLite e static/images os uploads
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /code/static/images \
    && chown -R app:app /data /code

COPY --chown=app:app src/ .

USER app

EXPOSE 8000

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
