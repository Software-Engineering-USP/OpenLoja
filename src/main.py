# imports necessários para o funcionamento do projeto
from fastapi import FastAPI, Request, Depends, HTTPException, status, Cookie, Response , UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select
from models import Vendedor, Cliente, Produto, Reserva, Avaliacao, Usuario, Carrinho, CarrinhoProdutoLink
from datetime import datetime
import os
import shutil

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

# função auxiliar que retorna o usuário logado, se houver, sem exigir autenticação
def get_optional_user(
    session_user: Annotated[str | None, Cookie()] = None,
    tipo: Annotated[str | None, Cookie()] = None
):
    if not session_user:
        return None

    with Session(engine) as session:
        if tipo == "vendedor":
            user = session.exec(
                select(Vendedor).where(Vendedor.nome == session_user)
            ).first()
        elif tipo == "cliente":
            user = session.exec(
                select(Cliente).where(Cliente.nome == session_user)
            ).first()

    if not user:
        return None

    return user


# função auxiliar que captura o usuário logado no cookie
def get_active_user(
    session_user: Annotated[str | None, Cookie()] = None,
    tipo: Annotated[str | None, Cookie()] = None,
):
    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado: você não está logado.",
        )

    with Session(engine) as session:
        if tipo == "vendedor":
            user = session.exec(
                select(Vendedor).where(Vendedor.nome == session_user)
            ).first()
        elif tipo == "cliente":
            user = session.exec(
                select(Cliente).where(Cliente.nome == session_user)
            ).first()
        else:
            raise HTTPException(401, "Tipo de usuário inválido.")

    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    return user

def get_admin(user: Annotated[Cliente | Vendedor, Depends(get_active_user)]):
    if not isinstance(user, Vendedor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas vendedores podem acessar esta rota.",
        )

    return user

# função auxiliar que captura o TIPO do usuário logado no cookie
def get_active_type(tipo: Annotated[str | None, Cookie()] = None):
    if not tipo:
        return None

    return tipo


# rota inicial para acesso a criação da conta admin ou acesso
@app.get("/")
async def root(
    request: Request,
    tipo: str | None = Depends(get_active_type),
):
    with Session(engine) as session:
        existe_vendedor = session.exec(select(Vendedor)).first() is not None

    if not existe_vendedor:
        return templates.TemplateResponse(
            request=request,
            name="createAccount.html",
            context={"primeiroVendedor": True},
        )

    if tipo == "vendedor":
        return RedirectResponse(url="/home", status_code=303)

    return RedirectResponse(url="/homeCliente", status_code=303)

# rota para login
@app.get("/paginalogin", response_class=HTMLResponse)
async def paginalogin(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/paginacria", response_class=HTMLResponse)
async def paginacriar(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="createAccount.html",
        context={"primeiroVendedor": False},
    )


# rota para criação de usuários no database
@app.post("/criarusuario")
async def criar_usuario(user: Usuario):
    with Session(engine) as session:
        existeVendedor = session.exec(select(Vendedor)).first()

        if existeVendedor:
            vendedor = session.exec(
                select(Vendedor).where(Vendedor.nome == user.nome)
            ).first()
            cliente = session.exec(
                select(Cliente).where(Cliente.nome == user.nome)
            ).first()

            if vendedor or cliente:
                raise HTTPException(status_code=404, detail="Usuário já existente.")

            usuario = Cliente(nome=user.nome, senha=user.senha)

        else:
            usuario = Vendedor(nome=user.nome, senha=user.senha)

        session.add(usuario)
        session.commit()
        session.refresh(usuario)

    return {"usuario": usuario.nome}


# rota para logar com o usuário e setar o cookie
@app.post("/login")
def logar(nome: str, senha: str, response: Response):
    with Session(engine) as session:
        vendedor = session.exec(select(Vendedor).where(Vendedor.nome == nome)).first()

        if vendedor:
            if vendedor.senha != senha:
                raise HTTPException(404, "Senha incorreta")

            response.set_cookie("session_user", nome)
            response.set_cookie("tipo", "vendedor")

            return {"message": "Logado", "tipo": "vendedor"}

        cliente = session.exec(select(Cliente).where(Cliente.nome == nome)).first()

        if cliente:
            if cliente.senha != senha:
                raise HTTPException(404, "Senha incorreta")

            response.set_cookie("session_user", nome)
            response.set_cookie("tipo", "cliente")

            return {"message": "Logado", "tipo": "cliente"}

        raise HTTPException(404, "Usuário não encontrado")


# rota para o acesso à home do lojista
@app.get("/home")
def show_profile(request: Request, admin: Vendedor = Depends(get_admin)):
    return templates.TemplateResponse(request=request, name="homeOwner.html")


# rota para o acesso à home do cliente
@app.get("/homeCliente")
def home_cliente(
    request: Request,
    user: Cliente | Vendedor | None = Depends(get_optional_user),
):
    return templates.TemplateResponse(
        request=request,
        name="frontpage.html",
        context={"usuario": user},
    )


# rota de estoque do dono da loja
@app.get("/stock")
def stock(request: Request, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        produtos = session.exec(select(Produto)).all()

    return templates.TemplateResponse(
        request=request,
        name="stock.html",
        context={"produtos": produtos},
    )


# rota de estatísticas do dono da loja
@app.get("/statistics")
def statistics(request: Request, admin: Vendedor = Depends(get_admin)):
    estatisticas = {"receita_mensal": 0, "vendas_mes": 0, "nota_media": 0}
    top_produtos = []
    avaliacoes_recentes = []

    with Session(engine) as session:
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
    request: Request,
    produto_id: int,
    user: Cliente | Vendedor | None = Depends(get_optional_user),
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
def visualizar_db(admin: Vendedor = Depends(get_admin)):
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
def criar_produto(produto: Produto, admin: Vendedor = Depends(get_admin)):
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
def atualizar_produto(produto_id: int, dados: Produto, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, "Produto não encontrado")

        produto.sqlmodel_update(dados.model_dump(exclude_unset=True))

        session.add(produto)
        session.commit()
        session.refresh(produto)

        return produto


@app.post("/produtos/{produto_id}/imagem",responses={404: {"description": "Produto não encontrado"}})
def enviar_imagem(
    produto_id: int,
    imagem: UploadFile = File(...),
    admin: Vendedor = Depends(get_admin)
):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, "Produto não encontrado")

        os.makedirs("static/images", exist_ok=True)

        nome_imagem = os.path.basename(imagem.filename)
        caminho = f"images/{produto_id}_{nome_imagem}"

        with open(f"static/{caminho}", "wb") as buffer:
            shutil.copyfileobj(imagem.file, buffer)

        produto.imagem = caminho

        session.add(produto)
        session.commit()

    return {"ok": True}


# rota para deleção de produtos no db
@app.delete("/produtos/{produto_id}")
def deletar_produto(produto_id: int, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, "Produto não encontrado")

        session.delete(produto)
        session.commit()

        return {"message": "Produto removido"}


# rota para concluir uma reserva
@app.put("/reservas/{reserva_id}/completar")
def concluir_reserva(reserva_id: int, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        reserva = session.get(Reserva, reserva_id)

        if reserva is None:
            raise HTTPException(404, "Reserva não encontrada")

        if reserva.concluida:
            raise HTTPException(400, "Reserva já está concluída")

        reserva.concluida = True
        reserva.valor_efetivo = reserva.valor
        reserva.data_conclusao = datetime.now()

        session.add(reserva)
        session.commit()
        session.refresh(reserva)

        return reserva


# Helpers para rotas de carrinho
def _get_or_create_carrinho(session: Session, cliente_id: int) -> Carrinho:
    carrinho = session.exec(select(Carrinho).where(Carrinho.cliente_id == cliente_id)).first()
    if not carrinho:
        carrinho = Carrinho(cliente_id=cliente_id)
        session.add(carrinho)
        session.commit()
        session.refresh(carrinho)
    return carrinho

def _get_carrinho_or_404(session: Session, cliente_id: int) -> Carrinho:
    carrinho = session.exec(select(Carrinho).where(Carrinho.cliente_id == cliente_id)).first()
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    return carrinho

def _get_carrinho_produto_link(session: Session, carrinho_id: int, produto_id: int) -> CarrinhoProdutoLink | None:
    return session.exec(
        select(CarrinhoProdutoLink).where(
            (CarrinhoProdutoLink.carrinho_id == carrinho_id)
            & (CarrinhoProdutoLink.produto_id == produto_id)
        )
    ).first()


# rota para criar ou obter o carrinho de um cliente
@app.get("/carrinho")
def get_carrinho(user: Annotated[Cliente, Depends(get_active_user)]):
    with Session(engine) as session:
        carrinho = _get_or_create_carrinho(session, user.id)

        resultados = (
            select(Produto, CarrinhoProdutoLink.quantidade)
            .join(CarrinhoProdutoLink, CarrinhoProdutoLink.produto_id == Produto.id)
            .where(CarrinhoProdutoLink.carrinho_id == carrinho.id)
        )
        itens = session.exec(resultados).all()

        total = 0;
        itens_formatados = []
        for produto, quantidade in itens:

            total += produto.preco
            
            itens_formatados.append({
                "id": produto.id,
                "nome": produto.nome,
                "preco": produto.preco,
                "imagem": produto.imagem,
                "quantidade": quantidade
            })

        return {
            "id": carrinho.id,
            "cliente_id": user.id,
            "itens": itens_formatados,
            "total": total
        }


# rota para adicionar um produto ao carrinho
@app.post("/carrinho/add")
def add_produto(
    user: Annotated[Cliente, Depends(get_active_user)],
    produto_id: int,
    quantidade: int = 1,
):
    with Session(engine) as session:
        carrinho = _get_or_create_carrinho(session, user.id)
    
        link = _get_carrinho_produto_link(session, carrinho.id, produto_id)
        if link:
            link.quantidade += quantidade
        else:
            link = CarrinhoProdutoLink(
                carrinho_id=carrinho.id, produto_id=produto_id, quantidade=quantidade
            )
            session.add(link)
        session.commit()
        return {"msg": "produto adicionado", "carrinho_id": carrinho.id}


# rota para alterar a quantidade de um produto no carrinho
@app.patch("/carrinho/item", responses={404: {"description": "Carrinho ou item não encontrado"}})
def update_item(
    produto_id: int,
    nova_quantidade: int,
    user: Annotated[Cliente, Depends(get_active_user)],
):
    with Session(engine) as session:
        carrinho = _get_carrinho_or_404(session, user.id)
    
        link = _get_carrinho_produto_link(session, carrinho.id, produto_id)
        if not link:
            raise HTTPException(status_code=404, detail="Item não está no carrinho")
    
        if nova_quantidade <= 0:
            session.delete(link)
        else:
            link.quantidade = nova_quantidade
    
        session.commit()
        return {"msg": "quantidade atualizada"}


# rota para remover um produto do carrinho
@app.delete("/carrinho/item/{produto_id}", responses={404: {"description": "Carrinho ou item não encontrado"}})
def remove_item(
    produto_id: int,
    user: Annotated[Cliente, Depends(get_active_user)],
):
    with Session(engine) as session:
        carrinho = _get_carrinho_or_404(session, user.id)
    
        link = _get_carrinho_produto_link(session, carrinho.id, produto_id)
        if link:
            session.delete(link)
            session.commit()
        return {"msg": "item removido"}


# rota para sincronizar o carrinho local com o carrinho no banco de dados de um cliente após login
@app.post("/carrinho/sincronizar")
def sincronizar_carrinho(itens: list[CarrinhoProdutoLink], user: Annotated[Cliente, Depends(get_active_user)]):
    with Session(engine) as session:
        carrinho = _get_or_create_carrinho(session, user.id);

        for item in itens:
            link = session.exec(select(CarrinhoProdutoLink).where( 
                CarrinhoProdutoLink.carrinho_id == carrinho.id,
                CarrinhoProdutoLink.produto_id == item.produto_id
            )).first()
            
            if link:
                link.quantidade += item.quantidade
            else:
                session.add(CarrinhoProdutoLink(
                    carrinho_id=carrinho.id,
                    produto_id=item.produto_id,
                    quantidade=item.quantidade
                ))

        session.commit()
        return {"ok": True}
                            
            
