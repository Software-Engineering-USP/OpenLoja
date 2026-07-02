
# imports necessários para o funcionamento do projeto
from fastapi import FastAPI, Request,Depends, HTTPException, status, Cookie, Response, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select

# setup do Fastapi 
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# setup do SQL
arquivo_sqlite = "database.db"
url_sqlite = f"sqlite:///{arquivo_sqlite}"
engine = create_engine(url_sqlite)

def create_db():
    SQLModel.metadata.create_all(engine)
    
@app.on_event("startup")
def on_startup() -> None:
    create_db()

# rota inicial para criação de contas
@app.get("/")
async def root(request : Request):
    return templates.TemplateResponse(
        request=request, name="createAccount.html"
    )
