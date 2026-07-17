# imports necessários para o funcionamento do projeto
from fastapi import FastAPI, Request, Depends, HTTPException, status, Cookie, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select
from models import Vendedor, Cliente, Produto, Reserva, Avaliacao

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
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="createAccount.html")


# rota para login
@app.get("/paginalogin", response_class=HTMLResponse)
async def paginalogin(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


# rota para criação de usuários no database
@app.post("/criarusuario")
async def criar_usuario(user: Vendedor):
    with Session(engine) as session:
        busca = session.exec(select(Vendedor).where(Vendedor.nome == user.nome)).first()
        if busca:
            raise HTTPException(status_code=404, detail="Usuário já existente.")

        session.add(user)
        session.commit()
        session.refresh(user)

    return {"usuario": user.nome}


# rota para login com usuário e senha
@app.post("/login")
def logar(nome: str, senha: str, response: Response):
    with Session(engine) as session:
        user = select(Vendedor).where(Vendedor.nome == nome)
        usuario_encontrado = session.exec(user).first()
        if not usuario_encontrado:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if usuario_encontrado.senha != senha:
            raise HTTPException(status_code=404, detail="Senha incorreta")
        response.set_cookie(key="session_user", value=nome)
    return {"message": "Logado com sucesso"}


# função auxiliar que captura o usuário logado no cookie
def get_active_user(session_user: Annotated[str | None, Cookie()] = None):
    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado: você não está logado.",
        )

    with Session(engine) as session:
        busca = select(Vendedor).where(Vendedor.nome == session_user)
        user = session.exec(busca).first()

    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    return user



# rota para o acesso à home do lojista
@app.get("/home")
def show_profile(request: Request, user: Vendedor = Depends(get_active_user)):
    return templates.TemplateResponse(request=request, name="homeOwner.html")


# rota de estoque do dono da loja
@app.get("/stock")
def stock(request: Request, user: Vendedor = Depends(get_active_user)):
    with Session(engine) as session:
        produtos = session.exec(select(Produto)).all() if user else []

    return templates.TemplateResponse(
        request=request, name="stock.html", context={"produtos": produtos}
    )


# rota de estatísticas do dono da loja
@app.get("/statistics")
def statistics(request: Request, user: Vendedor = Depends(get_active_user)):
    estatisticas = {"receita_mensal": 0, "vendas_mes": 0, "nota_media": 0}
    top_produtos = []
    avaliacoes_recentes = []

    with Session(engine) as session:
        if user:
            produtos = session.exec(select(Produto)).all()
            produto_ids = [p.id for p in produtos]

            reservas = session.exec(select(Reserva)).all()
            estatisticas["vendas_mes"] = len(reservas)

            produtos_por_id = {p.id: p for p in produtos}
            estatisticas["receita_mensal"] = sum(
                produtos_por_id[r.produto_id].preco
                for r in reservas
                if r.produto_id in produtos_por_id
            )

            vendas_por_produto: dict[int, int] = {}
            for r in reservas:
                if r.produto_id is not None:
                    vendas_por_produto[r.produto_id] = (
                        vendas_por_produto.get(r.produto_id, 0) + 1
                    )

            top_produtos = sorted(
                (
                    {"nome": p.nome, "vendas": vendas_por_produto.get(p.id, 0)}
                    for p in produtos
                ),
                key=lambda item: item["vendas"],
                reverse=True,
            )[:5]

            avaliacoes = (
                session.exec(
                    select(Avaliacao).where(Avaliacao.produto_id.in_(produto_ids))
                ).all()
                if produto_ids
                else []
            )

            if avaliacoes:
                estatisticas["nota_media"] = round(
                    sum(a.nota for a in avaliacoes) / len(avaliacoes), 1
                )

            avaliacoes_recentes = sorted(
                avaliacoes, key=lambda a: (a.dia, a.horario), reverse=True
            )[:5]

    return templates.TemplateResponse(
        request=request,
        name="stat.html",
        context={
            "estatisticas": estatisticas,
            "top_produtos": top_produtos,
            "avaliacoes_recentes": avaliacoes_recentes,
        },
    )


# rota de visualização de um produto
@app.get("/product/{produto_id}")
def product(
    request: Request, produto_id: int, user: Vendedor = Depends(get_active_user)
):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        avaliacoes = session.exec(
            select(Avaliacao).where(Avaliacao.produto_id == produto_id)
        ).all()

    return templates.TemplateResponse(
        request=request,
        name="product.html",
        context={
            "produto": produto,
            "avaliacoes": avaliacoes,
        },
    )


# rota auxiliar para visualizar os usuários criados
@app.get("/db")
def visualizar_db():
    with Session(engine) as session:
        return {
            "clientes": session.exec(select(Cliente)).all(),
            "vendedores": session.exec(select(Vendedor)).all(),
            "produtos": session.exec(select(Produto)).all(),
            "reservas": session.exec(select(Reserva)).all(),
            "avaliacoes": session.exec(select(Avaliacao)).all(),
        }

# rota para adição/criação de produtos no db
@app.post("/produtos")
def criar_produto(produto: Produto):
    with Session(engine) as session:
        session.add(produto)
        session.commit()
        session.refresh(produto)
        return produto
    

# rota para listar todos produtos do db
@app.get("/produtos")
def listar_produtos():
    with Session(engine) as session:
        return session.exec(select(Produto)).all()
    

# rota para buscar por produto especificado pelo ID
@app.get("/produtos/{produto_id}")
def buscar_produto(produto_id: int):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, "Produto não encontrado")

        return produto 


# rota para modificação de produto especificado por ID
@app.put("/produtos/{produto_id}")
def atualizar_produto(produto_id: int, dados: Produto):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, "Produto não encontrado")

        produto.sqlmodel_update(dados.model_dump(exclude_unset=True))

        session.add(produto)
        session.commit()
        session.refresh(produto)

        return produto
    

# rota para deleção de produtos no db
@app.delete("/produtos/{produto_id}")
def deletar_produto(produto_id: int):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, "Produto não encontrado")

        session.delete(produto)
        session.commit()

        return {"message": "Produto removido"}


