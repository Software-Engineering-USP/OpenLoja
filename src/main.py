# imports necessários para o funcionamento do projeto
from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    status,
    Cookie,
    Response,
    UploadFile,
    File,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.orm import selectinload
from itsdangerous import URLSafeTimedSerializer, BadSignature
from models import (
    Vendedor,
    Cliente,
    Produto,
    Reserva,
    ReservaProdutoLink,
    Avaliacao,
    Usuario,
    Carrinho,
    CarrinhoProdutoLink,
    ReservaCreate,
    ReservaUpdate,
    ValorEfetivoUpdate,
    Loja,
    AvaliacaoCreate,
)
from pathlib import Path
from datetime import datetime
import os
import shutil
import json

# variavel para manter cwd na testagem
BASE_DIR = Path(__file__).resolve().parent

# setup do Fastapi
app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# chave secreta usada para assinar os cookies de sessão
# se for de fato usar o app, defina "SECRET_KEY" aleatoriamente no ambiente
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    import secrets as _secrets

    SECRET_KEY = _secrets.token_hex(32)
    print(
        "AVISO: variável de ambiente SECRET_KEY não definida",
        "Usando uma chave temporária gerada agora",
    )

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="session-cookie")

# duração máxima de uma sessão, em segundos (7 dias)
SESSION_MAX_AGE = 60 * 60 * 24 * 7

# constantes para evitar duplicação
RESERVE_NOT_FOUND = "Reserva não encontrada"
CLIENT_NOT_FOUND = "Cliente não encontrado"
PRODUCT_NOT_FOUND = "Produto não encontrado"
STATIC_IMAGES_DIR = "static/images"

# setup do SQL
arquivo_sqlite = "database.db"
url_sqlite = f"sqlite:///{arquivo_sqlite}"
engine = create_engine(url_sqlite)


def create_db():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if session.exec(select(Loja)).first() is None:
            session.add(Loja())
            session.commit()


@app.on_event("startup")
def on_startup() -> None:
    create_db()


# formata um valor float como real
def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# decodifica e valida o cookie de sessão assinado.
# retorna None se o cookie não existir, estiver expirado ou inválido
def ler_sessao(session: str | None) -> dict | None:
    if not session:
        return None

    try:
        dados = serializer.loads(session, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None

    if not isinstance(dados, dict) or "nome" not in dados or "tipo" not in dados:
        return None

    return dados


# função auxiliar que retorna o usuário logado, se houver, sem exigir autenticação
def get_optional_user(session: Annotated[str | None, Cookie()] = None):
    dados = ler_sessao(session)

    if not dados:
        return None

    with Session(engine) as db:
        if dados["tipo"] == "vendedor":
            user = db.exec(
                select(Vendedor).where(Vendedor.nome == dados["nome"])
            ).first()
        elif dados["tipo"] == "cliente":
            user = db.exec(select(Cliente).where(Cliente.nome == dados["nome"])).first()
        else:
            return None

    return user


# função auxiliar que captura o usuário logado no cookie
def get_active_user(session: Annotated[str | None, Cookie()] = None):
    dados = ler_sessao(session)

    if not dados:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado: você não está logado.",
        )

    with Session(engine) as db:
        if dados["tipo"] == "vendedor":
            user = db.exec(
                select(Vendedor).where(Vendedor.nome == dados["nome"])
            ).first()
        elif dados["tipo"] == "cliente":
            user = db.exec(select(Cliente).where(Cliente.nome == dados["nome"])).first()
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
def get_active_type(session: Annotated[str | None, Cookie()] = None):
    dados = ler_sessao(session)

    if not dados:
        return None

    return dados["tipo"]


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
@app.post(
    "/criarusuario",
    responses={404: {"description": "Usuário já existente"}},
)
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
@app.post(
    "/login",
    responses={404: {"description": "Usuário ou senha incorretos ou inexistente"}},
)
def logar(nome: str, senha: str, response: Response):
    with Session(engine) as session:
        vendedor = session.exec(select(Vendedor).where(Vendedor.nome == nome)).first()

        if vendedor:
            if vendedor.senha != senha:
                raise HTTPException(404, "Senha incorreta")

            token = serializer.dumps({"nome": nome, "tipo": "vendedor"})
            response.set_cookie(
                "session",
                token,
                httponly=True,
                samesite="lax",
                max_age=SESSION_MAX_AGE,
            )

            return {"message": "Logado", "tipo": "vendedor"}

        cliente = session.exec(select(Cliente).where(Cliente.nome == nome)).first()

        if cliente:
            if cliente.senha != senha:
                raise HTTPException(404, "Senha incorreta")

            token = serializer.dumps({"nome": nome, "tipo": "cliente"})
            response.set_cookie(
                "session",
                token,
                httponly=True,
                samesite="lax",
                max_age=SESSION_MAX_AGE,
            )

            return {"message": "Logado", "tipo": "cliente"}

        raise HTTPException(404, "Usuário não encontrado")


# rota para deslogar (apaga o cookie de sessão)
@app.post("/logout")
def deslogar(response: Response):
    response.delete_cookie("session")
    return {"message": "Deslogado"}


# rota para o acesso à home do lojista
@app.get("/home")
def show_profile(request: Request, admin: Vendedor = Depends(get_admin)):
    agora = datetime.now()
    ano_mes_atual = (agora.year, agora.month)

    with Session(engine) as session:
        produtos = session.exec(select(Produto)).all()
        reservas = session.exec(select(Reserva).where(Reserva.concluida)).all()

        itens_em_estoque = sum(p.quantidade_em_estoque for p in produtos)
        valor_em_estoque = sum(p.preco * p.quantidade_em_estoque for p in produtos)

        receita_mensal = 0.0
        vendas_mes = 0
        primeira_compra_por_cliente: dict[int, datetime] = {}

        for r in reservas:
            if (r.data_conclusao.year, r.data_conclusao.month) == ano_mes_atual:
                valor = r.valor_efetivo if r.valor_efetivo is not None else r.valor
                receita_mensal += valor
                vendas_mes += 1

            data_registrada = primeira_compra_por_cliente.get(r.cliente_id)
            if data_registrada is None or r.data_conclusao < data_registrada:
                primeira_compra_por_cliente[r.cliente_id] = r.data_conclusao

        # "novos clientes" = clientes cuja primeira compra concluída foi neste mês
        novos_clientes = sum(
            1
            for data in primeira_compra_por_cliente.values()
            if (data.year, data.month) == ano_mes_atual
        )

    return templates.TemplateResponse(
        request=request,
        name="homeOwner.html",
        context={
            "receita_mensal_fmt": formatar_moeda(receita_mensal),
            "itens_em_estoque": itens_em_estoque,
            "valor_em_estoque_fmt": formatar_moeda(valor_em_estoque),
            "vendas_mes": vendas_mes,
            "novos_clientes": novos_clientes,
        },
    )


# rota para o acesso à home do cliente
@app.get("/homeCliente")
def home_cliente(
    request: Request,
    user: Cliente | Vendedor | None = Depends(get_optional_user),
):
    with Session(engine) as session:
        produtos = session.exec(select(Produto)).all()
        loja = session.exec(select(Loja)).first()

        tags = set()

        for produto in produtos:
            if produto.tag:
                for tag in produto.tag.split(","):
                    tags.add(tag.strip())

    return templates.TemplateResponse(
        request=request,
        name="frontpage.html",
        context={
            "usuario": user,
            "produtos": produtos,
            "tags": sorted(tags),
            "loja": loja,
        },
    )


# monta a visão (lista de pedidos + resumo) de um cliente, reaproveitada
# tanto na página "Minha Conta" do próprio cliente quanto no perfil que
# o vendedor vê em /clientes/{id}
def montar_historico_cliente(session: Session, cliente_id: int) -> dict:
    reservas = session.exec(
        select(Reserva).where(Reserva.cliente_id == cliente_id)
    ).all()

    produtos = session.exec(select(Produto)).all()
    links = session.exec(select(ReservaProdutoLink)).all()

    produtos_por_id = {p.id: p for p in produtos}
    links_por_reserva: dict[int, list[ReservaProdutoLink]] = {}
    for link in links:
        links_por_reserva.setdefault(link.reserva_id, []).append(link)

    reservas_view = []
    total_pedidos = 0
    total_pendentes = 0
    total_gasto = 0.0

    for r in sorted(reservas, key=lambda r: r.id, reverse=True):
        itens = []
        for link in links_por_reserva.get(r.id, []):
            produto = produtos_por_id.get(link.produto_id)
            if produto:
                itens.append(
                    {
                        "produto_id": produto.id,
                        "nome": produto.nome,
                        "quantidade": link.quantidade,
                        "preco": produto.preco,
                    }
                )

        reservas_view.append(
            {
                "id": r.id,
                "valor": r.valor,
                "concluida": r.concluida,
                "valor_efetivo": r.valor_efetivo,
                "data_conclusao": r.data_conclusao,
                "itens": itens,
            }
        )

        total_pedidos += 1
        if not r.concluida:
            total_pendentes += 1

        if r.concluida:
            total_gasto += r.valor_efetivo if r.valor_efetivo else r.valor

    return {
        "reservas": reservas_view,
        "total_pedidos": total_pedidos,
        "total_pendentes": total_pendentes,
        "total_gasto": total_gasto,
    }


# rota para a página pessoal do cliente
@app.get(
    "/cliente",
    response_class=HTMLResponse,
    responses={404: {"description": CLIENT_NOT_FOUND}},
)
def cliente_page(request: Request, user: Annotated[Cliente, Depends(get_active_user)]):
    with Session(engine) as session:
        cliente = session.get(Cliente, user.id)
        if not cliente:
            raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND)

        historico = montar_historico_cliente(session, user.id)

    return templates.TemplateResponse(
        request=request,
        name="clientPage.html",
        context={
            "cliente": cliente,
            **historico,
        },
    )


# rota para o vendedor listar todos os clientes cadastrados
@app.get("/clientes", response_class=HTMLResponse)
def listar_clientes_page(
    request: Request,
    admin: Annotated[Vendedor, Depends(get_admin)],
):
    with Session(engine) as session:
        clientes = session.exec(select(Cliente)).all()
        reservas = session.exec(select(Reserva)).all()

        resumo_por_cliente: dict[int, dict] = {}
        for c in clientes:
            resumo_por_cliente[c.id] = {"pedidos": 0, "total_gasto": 0.0}

        for r in reservas:
            resumo = resumo_por_cliente.get(r.cliente_id)
            if resumo is None:
                continue
            resumo["pedidos"] += 1
            if r.concluida:
                resumo["total_gasto"] += r.valor_efetivo if r.valor_efetivo else r.valor

        clientes_view = [
            {
                "id": c.id,
                "nome": c.nome,
                "pedidos": resumo_por_cliente[c.id]["pedidos"],
                "total_gasto": resumo_por_cliente[c.id]["total_gasto"],
            }
            for c in clientes
        ]

    return templates.TemplateResponse(
        request=request,
        name="clientsList.html",
        context={"clientes": clientes_view},
    )


# rota para o vendedor ver o perfil e o histórico de compras de um cliente
@app.get(
    "/clientes/{cliente_id}",
    response_class=HTMLResponse,
    responses={404: {"description": CLIENT_NOT_FOUND}},
)
def perfil_cliente_page(
    request: Request,
    cliente_id: int,
    admin: Annotated[Vendedor, Depends(get_admin)],
):
    with Session(engine) as session:
        cliente = session.get(Cliente, cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND)

        historico = montar_historico_cliente(session, cliente_id)

    return templates.TemplateResponse(
        request=request,
        name="clientProfile.html",
        context={
            "cliente": cliente,
            **historico,
        },
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


@app.get("/loja")
def buscar_loja(admin: Annotated[Vendedor, Depends(get_admin)]):
    with Session(engine) as session:
        loja = session.exec(select(Loja)).first()

        if loja is None:
            loja = Loja()
            session.add(loja)
            session.commit()
            session.refresh(loja)

        return loja


@app.put("/loja")
def atualizar_loja(dados: Loja, admin: Annotated[Vendedor, Depends(get_admin)]):
    with Session(engine) as session:
        loja = session.exec(select(Loja)).first()

        if loja is None:
            loja = Loja()
            session.add(loja)

        loja.sqlmodel_update(dados.model_dump(exclude_unset=True))

        session.add(loja)
        session.commit()
        session.refresh(loja)

        return loja


@app.get("/settings")
def settings(
    request: Request,
    admin: Annotated[Vendedor, Depends(get_admin)],
):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
    )


# rota de pedidos (reservas) do dono da loja
@app.get("/orders")
def orders(request: Request, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        clientes = session.exec(select(Cliente)).all()
        produtos = session.exec(select(Produto)).all()
        reservas = session.exec(select(Reserva)).all()
        links = session.exec(select(ReservaProdutoLink)).all()

        produtos_por_id = {p.id: p for p in produtos}
        links_por_reserva: dict[int, list[ReservaProdutoLink]] = {}
        for link in links:
            links_por_reserva.setdefault(link.reserva_id, []).append(link)

        reservas_view = []
        for r in reservas:
            itens = []
            for link in links_por_reserva.get(r.id, []):
                produto = produtos_por_id.get(link.produto_id)
                if produto:
                    itens.append(
                        {
                            "produto_id": produto.id,
                            "nome": produto.nome,
                            "quantidade": link.quantidade,
                            "preco": produto.preco,
                        }
                    )

            reservas_view.append(
                {
                    "id": r.id,
                    "cliente_id": r.cliente_id,
                    "cliente_nome": r.cliente.nome if r.cliente else "—",
                    "valor": r.valor,
                    "concluida": r.concluida,
                    "valor_efetivo": r.valor_efetivo,
                    "data_conclusao": r.data_conclusao,
                    "itens": itens,
                    "itens_json": json.dumps(itens),
                }
            )

    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={
            "reservas": reservas_view,
            "clientes": clientes,
            "produtos": produtos,
        },
    )


# rota para o gráfico de receita mensal do painel de estatísticas
@app.get("/estatisticas/receita-mensal")
def receita_mensal(admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        reservas = session.exec(
            select(Reserva)
            .where(Reserva.concluida)
            .where(Reserva.data_conclusao is not None)
        ).all()

        receita_agrupada = {}
        for r in reservas:
            ano_mes = r.data_conclusao.strftime("%Y-%m")
            valor = r.valor_efetivo if r.valor_efetivo is not None else r.valor
            receita_agrupada[ano_mes] = receita_agrupada.get(ano_mes, 0.0) + valor

        labels = []
        valores = []
        for ano_mes in sorted(receita_agrupada.keys()):
            dt = datetime.strptime(ano_mes, "%Y-%m")
            meses_pt = {
                1: "Jan",
                2: "Fev",
                3: "Mar",
                4: "Abr",
                5: "Mai",
                6: "Jun",
                7: "Jul",
                8: "Ago",
                9: "Set",
                10: "Out",
                11: "Nov",
                12: "Dez",
            }
            label_br = f"{meses_pt[dt.month]}/{dt.year}"
            labels.append(label_br)
            valores.append(round(receita_agrupada[ano_mes], 2))

        return {"labels": labels, "valores": valores}


# rota de estatísticas do dono da loja
@app.get("/statistics")
def statistics(request: Request, admin: Vendedor = Depends(get_admin)):
    estatisticas = {"receita_mensal": 0, "vendas_mes": 0, "nota_media": 0}
    top_produtos = []
    avaliacoes_recentes = []

    agora = datetime.now()
    ano_mes_atual = (agora.year, agora.month)

    with Session(engine) as session:
        produtos = session.exec(select(Produto)).all()
        produto_ids = [p.id for p in produtos]

        reservas = session.exec(select(Reserva).where(Reserva.concluida)).all()

        # apenas reservas efetivadas e concluídas neste mês
        reservas_mes_atual = [
            r
            for r in reservas
            if r.data_conclusao is not None
            and (r.data_conclusao.year, r.data_conclusao.month) == ano_mes_atual
        ]

        estatisticas["vendas_mes"] = len(reservas_mes_atual)

        estatisticas["receita_mensal"] = sum(
            r.valor_efetivo if r.valor_efetivo is not None else r.valor
            for r in reservas_mes_atual
        )

        vendas_por_produto: dict[int, int] = {}
        links_vendidos = session.exec(select(ReservaProdutoLink)).all()
        for link in links_vendidos:
            if link.produto_id is not None:
                vendas_por_produto[link.produto_id] = (
                    vendas_por_produto.get(link.produto_id, 0) + link.quantidade
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
@app.get(
    "/product/{produto_id}",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def product(
    request: Request,
    produto_id: int,
    user: Cliente | Vendedor | None = Depends(get_optional_user),
):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)
        if not produto:
            raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND)

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


# -----------------------------------------------------------------
# TEMA DA LOJA
# -----------------------------------------------------------------
# função usada pelos templates (via Jinja global "loja_atual") para
# pegar os dados da loja em QUALQUER página, sem precisar que cada
# rota busque e passe "loja" manualmente no context
def obter_loja_atual() -> Loja:
    with Session(engine) as session:
        loja = session.exec(select(Loja)).first()
        return loja if loja else Loja()


templates.env.globals["loja_atual"] = obter_loja_atual


# gera um .css dinâmico com as cores escolhidas pelo vendedor como
# variáveis CSS (--cor-primaria, --cor-secundaria, --cor-destaque).
# esse arquivo é importado em <head> ANTES dos outros .css, então
# qualquer regra que use var(--cor-primaria) etc. já reflete a loja
@app.get("/theme.css")
def theme_css():
    loja = obter_loja_atual()

    css = f"""/* gerado automaticamente a partir das configurações da loja */
:root {{
  --cor-primaria: {loja.cor_primaria};
  --cor-secundaria: {loja.cor_secundaria};
  --cor-destaque: {loja.cor_destaque};
}}
"""

    return Response(
        content=css,
        media_type="text/css",
        headers={"Cache-Control": "no-cache"},
    )


# upload da logo da loja
@app.post("/loja/logo")
def enviar_logo(
    logo: Annotated[UploadFile, File(...)],
    admin: Annotated[Vendedor, Depends(get_admin)],
):
    with Session(engine) as session:
        loja = session.exec(select(Loja)).first()
        if loja is None:
            loja = Loja()

        os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)

        nome_arquivo = os.path.basename(logo.filename)
        caminho = f"images/loja_logo_{nome_arquivo}"

        with open(f"static/{caminho}", "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)

        loja.logo = caminho

        session.add(loja)
        session.commit()

    return {"ok": True, "logo": caminho}


# upload do banner da loja
@app.post("/loja/banner")
def enviar_banner(
    banner: Annotated[UploadFile, File(...)],
    admin: Annotated[Vendedor, Depends(get_admin)],
):
    with Session(engine) as session:
        loja = session.exec(select(Loja)).first()
        if loja is None:
            loja = Loja()

        os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)

        nome_arquivo = os.path.basename(banner.filename)
        caminho = f"images/loja_banner_{nome_arquivo}"

        with open(f"static/{caminho}", "wb") as buffer:
            shutil.copyfileobj(banner.file, buffer)

        loja.banner = caminho

        session.add(loja)
        session.commit()

    return {"ok": True, "banner": caminho}


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
@app.get(
    "/produtos/{produto_id}",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def buscar_produto(produto_id: int):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, PRODUCT_NOT_FOUND)

        return produto


# rota para modificação de produto especificado por ID
@app.put(
    "/produtos/{produto_id}",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def atualizar_produto(
    produto_id: int, dados: Produto, admin: Vendedor = Depends(get_admin)
):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, PRODUCT_NOT_FOUND)

        produto.sqlmodel_update(dados.model_dump(exclude_unset=True))

        session.add(produto)
        session.commit()
        session.refresh(produto)

        return produto


@app.post(
    "/produtos/{produto_id}/imagem",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def enviar_imagem(
    produto_id: int,
    imagem: UploadFile = File(...),
    admin: Vendedor = Depends(get_admin),
):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, PRODUCT_NOT_FOUND)

        os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)

        nome_imagem = os.path.basename(imagem.filename)
        caminho = f"images/{produto_id}_{nome_imagem}"

        with open(f"static/{caminho}", "wb") as buffer:
            shutil.copyfileobj(imagem.file, buffer)

        produto.imagem = caminho

        session.add(produto)
        session.commit()

    return {"ok": True}


# rota para deleção de produtos no db
@app.delete(
    "/produtos/{produto_id}",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def deletar_produto(produto_id: int, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if produto is None:
            raise HTTPException(404, PRODUCT_NOT_FOUND)

        session.delete(produto)
        session.commit()

        return {"message": "Produto removido"}


# rota para criar reserva
@app.post(
    "/reservas",
    responses={
        404: {"description": "Produto ou cliente não encontrado"},
        400: {"description": "Reserva inválida"},
    },
)
def criar_reserva(
    dados: ReservaCreate,
    user: Annotated[Cliente | Vendedor, Depends(get_active_user)],
):
    if not dados.itens:
        raise HTTPException(400, "A reserva precisa ter ao menos um produto.")

    with Session(engine) as session:
        if isinstance(user, Vendedor):
            if dados.cliente_id is None:
                raise HTTPException(
                    400, "Informe o cliente para quem a reserva será criada."
                )
            cliente = session.get(Cliente, dados.cliente_id)
            if cliente is None:
                raise HTTPException(404, CLIENT_NOT_FOUND)
            cliente_id = cliente.id
        else:
            cliente_id = user.id

        produto_ids = [item.produto_id for item in dados.itens]
        produtos = session.exec(
            select(Produto).where(Produto.id.in_(produto_ids))
        ).all()
        produtos_por_id = {p.id: p for p in produtos}

        faltando = set(produto_ids) - produtos_por_id.keys()
        if faltando:
            raise HTTPException(
                404, f"Produto(s) não encontrado(s): {sorted(faltando)}"
            )

        valor_total = sum(
            produtos_por_id[item.produto_id].preco * item.quantidade
            for item in dados.itens
        )

        reserva = Reserva(cliente_id=cliente_id, valor=valor_total)
        session.add(reserva)
        session.commit()
        session.refresh(reserva)

        for item in dados.itens:
            session.add(
                ReservaProdutoLink(
                    reserva_id=reserva.id,
                    produto_id=item.produto_id,
                    quantidade=item.quantidade,
                )
            )

        session.commit()
        session.refresh(reserva)

        return reserva


# rota para listar todas as reservas
@app.get("/reservas")
def listar_reservas(admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        return session.exec(select(Reserva)).all()


# rota para buscar uma reserva específica pelo ID
@app.get(
    "/reservas/{reserva_id}",
    responses={404: {"description": RESERVE_NOT_FOUND}},
)
def buscar_reserva(reserva_id: int, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        reserva = session.get(Reserva, reserva_id)

        if reserva is None:
            raise HTTPException(404, RESERVE_NOT_FOUND)

        return reserva


# rota para editar uma reserva (cliente e/ou produtos associados)
@app.put(
    "/reservas/{reserva_id}",
    responses={
        404: {"description": "Reserva, cliente ou produto não encontrado"},
        400: {"description": "Reserva já concluída ou inválida"},
    },
)
def editar_reserva(
    reserva_id: int, dados: ReservaUpdate, admin: Vendedor = Depends(get_admin)
):
    with Session(engine) as session:
        reserva = session.get(Reserva, reserva_id)

        if reserva is None:
            raise HTTPException(404, RESERVE_NOT_FOUND)

        if reserva.concluida:
            raise HTTPException(400, "Reserva já concluída não pode ser editada")

        if dados.cliente_id is not None:
            cliente = session.get(Cliente, dados.cliente_id)
            if cliente is None:
                raise HTTPException(404, CLIENT_NOT_FOUND)
            reserva.cliente_id = dados.cliente_id

        if dados.itens is not None:
            if not dados.itens:
                raise HTTPException(400, "A reserva precisa ter ao menos um produto.")

            produto_ids = [item.produto_id for item in dados.itens]
            produtos = session.exec(
                select(Produto).where(Produto.id.in_(produto_ids))
            ).all()
            produtos_por_id = {p.id: p for p in produtos}

            faltando = set(produto_ids) - produtos_por_id.keys()
            if faltando:
                raise HTTPException(
                    404, f"Produto(s) não encontrado(s): {sorted(faltando)}"
                )

            links_antigos = session.exec(
                select(ReservaProdutoLink).where(
                    ReservaProdutoLink.reserva_id == reserva_id
                )
            ).all()
            for link in links_antigos:
                session.delete(link)
            session.flush()

            for item in dados.itens:
                session.add(
                    ReservaProdutoLink(
                        reserva_id=reserva_id,
                        produto_id=item.produto_id,
                        quantidade=item.quantidade,
                    )
                )

            reserva.valor = sum(
                produtos_por_id[item.produto_id].preco * item.quantidade
                for item in dados.itens
            )

        session.add(reserva)
        session.commit()
        session.refresh(reserva)

        return reserva


# rota para deletar uma reserva
@app.delete(
    "/reservas/{reserva_id}", responses={404: {"description": RESERVE_NOT_FOUND}}
)
def deletar_reserva(reserva_id: int, admin: Vendedor = Depends(get_admin)):
    with Session(engine) as session:
        reserva = session.get(Reserva, reserva_id)

        if reserva is None:
            raise HTTPException(404, RESERVE_NOT_FOUND)

        links = session.exec(
            select(ReservaProdutoLink).where(
                ReservaProdutoLink.reserva_id == reserva_id
            )
        ).all()

        # se a reserva já tinha sido efetivada (estoque já havia sido descontado),
        # repõe o estoque antes de excluir
        if reserva.concluida:
            for link in links:
                produto = session.get(Produto, link.produto_id)
                if produto:
                    produto.quantidade_em_estoque += link.quantidade
                    session.add(produto)

        for link in links:
            session.delete(link)

        session.delete(reserva)
        session.commit()

        return {"message": "Reserva removida"}


# rota para concluir uma reserva
@app.put(
    "/reservas/{reserva_id}/completar",
    responses={
        404: {"description": "Reserva ou produto não encontrados"},
        400: {
            "description": "Reserva já concluída, valor efetivo inválido ou produto sem estoque suficiente"
        },
    },
)
def concluir_reserva(
    reserva_id: int,
    dados: ValorEfetivoUpdate = ValorEfetivoUpdate(),
    admin: Vendedor = Depends(get_admin),
):
    with Session(engine) as session:
        reserva = session.get(Reserva, reserva_id)

        if reserva is None:
            raise HTTPException(404, RESERVE_NOT_FOUND)

        if reserva.concluida:
            raise HTTPException(400, "Reserva já está concluída")

        if dados.valor_efetivo is not None and dados.valor_efetivo < 0:
            raise HTTPException(400, "Valor efetivo não pode ser negativo")

        links = session.exec(
            select(ReservaProdutoLink).where(
                ReservaProdutoLink.reserva_id == reserva_id
            )
        ).all()

        # verifica se há estoque suficiente para todos os itens antes de efetivar
        for link in links:
            produto = session.get(Produto, link.produto_id)
            if not produto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produto com ID {link.produto_id} não encontrado.",
                )
            if produto.quantidade_em_estoque < link.quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para '{produto.nome}'. Disponível: {produto.quantidade_em_estoque}, Solicitado: {link.quantidade}",
                )

        # só reduz o estoque agora que a venda está sendo efetivada
        for link in links:
            produto = session.get(Produto, link.produto_id)
            produto.quantidade_em_estoque -= link.quantidade
            session.add(produto)

        reserva.concluida = True
        reserva.valor_efetivo = (
            dados.valor_efetivo if dados.valor_efetivo is not None else reserva.valor
        )
        reserva.data_conclusao = datetime.now()

        session.add(reserva)
        session.commit()
        session.refresh(reserva)

        return reserva


@app.put(
    "/reservas/{reserva_id}/valor-efetivo",
    responses={
        404: {"description": RESERVE_NOT_FOUND},
        400: {"description": "Reserva não concluída ou valor efetivo inválido"},
    },
)
def editar_valor_efetivo(
    reserva_id: int, dados: ValorEfetivoUpdate, admin: Vendedor = Depends(get_admin)
):
    if dados.valor_efetivo is None:
        raise HTTPException(400, "Informe o novo valor efetivo.")

    if dados.valor_efetivo < 0:
        raise HTTPException(400, "O valor efetivo não pode ser negativo.")

    with Session(engine) as session:
        reserva = session.get(Reserva, reserva_id)

        if reserva is None:
            raise HTTPException(404, RESERVE_NOT_FOUND)

        if not reserva.concluida:
            raise HTTPException(
                400, "A reserva precisa estar efetivada para ajustar o valor."
            )

        reserva.valor_efetivo = dados.valor_efetivo

        session.add(reserva)
        session.commit()
        session.refresh(reserva)

        return reserva


# Helpers para rotas de carrinho
def _get_or_create_carrinho(session: Session, cliente_id: int) -> Carrinho:
    carrinho = session.exec(
        select(Carrinho).where(Carrinho.cliente_id == cliente_id)
    ).first()
    if not carrinho:
        carrinho = Carrinho(cliente_id=cliente_id)
        session.add(carrinho)
        session.commit()
        session.refresh(carrinho)
    return carrinho


def _get_carrinho_or_404(session: Session, cliente_id: int) -> Carrinho:
    carrinho = session.exec(
        select(Carrinho).where(Carrinho.cliente_id == cliente_id)
    ).first()
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    return carrinho


def _get_carrinho_produto_link(
    session: Session, carrinho_id: int, produto_id: int
) -> CarrinhoProdutoLink | None:
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

        total = 0
        itens_formatados = []
        for produto, quantidade in itens:
            total += produto.preco * quantidade

            itens_formatados.append(
                {
                    "id": produto.id,
                    "nome": produto.nome,
                    "preco": produto.preco,
                    "imagem": produto.imagem,
                    "quantidade": quantidade,
                }
            )

        return {
            "id": carrinho.id,
            "cliente_id": user.id,
            "itens": itens_formatados,
            "total": total,
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
@app.patch(
    "/carrinho/item",
    responses={404: {"description": "Carrinho ou item não encontrado"}},
)
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
@app.delete(
    "/carrinho/item/{produto_id}",
    responses={404: {"description": "Carrinho ou item não encontrado"}},
)
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
def sincronizar_carrinho(
    itens: list[CarrinhoProdutoLink], user: Annotated[Cliente, Depends(get_active_user)]
):
    with Session(engine) as session:
        carrinho = _get_or_create_carrinho(session, user.id)

        for item in itens:
            link = session.exec(
                select(CarrinhoProdutoLink).where(
                    CarrinhoProdutoLink.carrinho_id == carrinho.id,
                    CarrinhoProdutoLink.produto_id == item.produto_id,
                )
            ).first()

            if link:
                link.quantidade += item.quantidade
            else:
                session.add(
                    CarrinhoProdutoLink(
                        carrinho_id=carrinho.id,
                        produto_id=item.produto_id,
                        quantidade=item.quantidade,
                    )
                )

        session.commit()
        return {"ok": True}


# rota para finalizar a compra transformando o carrinho em reserva
@app.post(
    "/checkout",
    responses={400: {"description": "Carrinho vazio ou estoque insuficiente"}},
)
def checkout(user: Annotated[Cliente, Depends(get_active_user)]):
    with Session(engine) as session:
        carrinho = _get_or_create_carrinho(session, user.id)

        links = session.exec(
            select(CarrinhoProdutoLink).where(
                CarrinhoProdutoLink.carrinho_id == carrinho.id
            )
        ).all()

        if not links:
            raise HTTPException(status_code=400, detail="O carrinho está vazio.")

        valor_total = 0.0
        for link in links:
            produto = session.get(Produto, link.produto_id)
            if not produto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produto com ID {link.produto_id} não encontrado.",
                )
            if produto.quantidade_em_estoque < link.quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para '{produto.nome}'. Disponível: {produto.quantidade_em_estoque}, Solicitado: {link.quantidade}",
                )
            valor_total += produto.preco * link.quantidade

        reserva = Reserva(cliente_id=user.id, valor=valor_total, concluida=False)
        session.add(reserva)
        session.commit()
        session.refresh(reserva)

        itens_formatados = []
        for link in links:
            produto = session.get(Produto, link.produto_id)

            session.add(
                ReservaProdutoLink(
                    reserva_id=reserva.id,
                    produto_id=link.produto_id,
                    quantidade=link.quantidade,
                )
            )

            itens_formatados.append(
                {
                    "nome": produto.nome,
                    "preco": produto.preco,
                    "quantidade": link.quantidade,
                }
            )

            session.delete(link)

        session.commit()
        return {
            "msg": "Compra finalizada com sucesso!",
            "reserva_id": reserva.id,
            "itens": itens_formatados,
            "total": valor_total,
        }


# rota para obter avaliações:
@app.get("/produtos/{produto_id}/avaliacoes")
def listar_avaliacoes(produto_id: int):
    with Session(engine) as session:
        avaliacoes = session.exec(
            select(Avaliacao)
            .where(Avaliacao.produto_id == produto_id)
            .options(selectinload(Avaliacao.cliente))
            .order_by(Avaliacao.id.desc())
        ).all()

    return [
        {
            "id": avaliacao.id,
            "nota": avaliacao.nota,
            "texto": avaliacao.texto,
            "dia": avaliacao.dia,
            "mes": avaliacao.mes,
            "ano": avaliacao.ano,
            "horario": avaliacao.horario,
            "cliente": avaliacao.cliente.nome if avaliacao.cliente else "Cliente",
        }
        for avaliacao in avaliacoes
    ]


# rota para criar avaliações:
@app.post("/produtos/{produto_id}/avaliacoes")
def criar_avaliacao(
    produto_id: int,
    dados: AvaliacaoCreate,
    user: Annotated[Cliente, Depends(get_active_user)],
):
    with Session(engine) as session:
        produto = session.get(Produto, produto_id)

        if not produto:
            raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND)

        if dados.nota < 0 or dados.nota > 5:
            raise HTTPException(
                status_code=400, detail="A nota deve estar entre 0 e 5."
            )

        avaliacao = Avaliacao(
            cliente_id=user.id,
            produto_id=produto_id,
            nota=dados.nota,
            texto=dados.texto,
            dia=datetime.now().day,
            mes=datetime.now().month,
            ano=datetime.now().year,
            horario=datetime.now().hour * 100 + datetime.now().minute,
        )

        session.add(avaliacao)
        session.commit()
        session.refresh(avaliacao)

        return avaliacao


# permite rodar o servidor diretamente com "python main.py"
# (alternativa a "uvicorn main:app --reload")
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
