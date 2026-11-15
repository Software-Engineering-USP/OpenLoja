"""Ponto de entrada: cria a aplicação FastAPI e registra as rotas.

Rodar localmente (a partir da raiz do repositório):
    fastapi dev src/openloja/main.py
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR, settings
from .database import init_db
from .routers import auth, carrinho, clientes, loja, painel, produtos, reservas


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="OpenLoja", lifespan=lifespan)

    # uploads ficam fora do código (UPLOAD_DIR) e são servidos em
    # /static/images; montado antes de /static para ter prioridade
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static/images", StaticFiles(directory=settings.upload_dir), name="images"
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    for modulo in (auth, painel, clientes, produtos, reservas, carrinho, loja):
        app.include_router(modulo.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
