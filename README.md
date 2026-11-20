# OpenLoja
Projeto final de MAC0350/26.<br>

O OpenLoja consiste em um site de vendas e controle de estoque genérico de fácil customização para diferentes tipos de produtos. Buscamos congregar simplicidade de comunicação vendedor-cliente, gerência e disponibilidade de produtos gratuitamente.

## Funcionalidades

- Vitrine pública com filtro por tags, carrinho e avaliações de produtos
- Painel do vendedor: estoque, pedidos, clientes, estatísticas e aparência da loja
- **Vendas presenciais**: em *Pedidos → + Venda Presencial*, o vendedor registra
  uma venda só com o nome do comprador, sem precisar de um cliente cadastrado,
  e pode efetivá-la na hora (descontando o estoque)

## Estrutura

```
src/openloja/
├── main.py           # cria a aplicação e registra as rotas
├── config.py         # configurações via variáveis de ambiente
├── database.py       # engine, sessão por requisição e migrações do SQLite
├── models.py         # tabelas (SQLModel)
├── schemas.py        # modelos de entrada/saída da API
├── security.py       # hash de senhas e cookie de sessão
├── dependencies.py   # autenticação/autorização (vendedor, cliente)
├── templating.py     # Jinja2 e helpers dos templates
├── routers/          # rotas agrupadas por assunto
│   ├── auth.py         contas, login e logout
│   ├── painel.py       home do vendedor e estatísticas
│   ├── clientes.py     "Minha Conta" e gestão de clientes
│   ├── produtos.py     vitrine, estoque, produtos e avaliações
│   ├── reservas.py     pedidos e vendas presenciais
│   ├── carrinho.py     carrinho e checkout
│   └── loja.py         configurações, tema e "Sobre"
├── services/         # regras de negócio usadas pelas rotas
├── static/           # CSS e JavaScript
└── templates/        # páginas HTML (Jinja2)
tests/                # testes (pytest), um arquivo por assunto
```

## Ambiente de Desenvolvimento

As dependências são gerenciadas com o [uv](https://docs.astral.sh/uv/):
declaradas no `pyproject.toml` e com as versões exatas travadas no `uv.lock`
(usado igualmente no CI e na imagem Docker).

```sh
uv sync                                   # cria o .venv com as dependências do lock
uv run fastapi dev src/openloja/main.py   # app em http://localhost:8000
uv run pytest                             # testes
```

Para mudar dependências, use `uv add <pacote>` / `uv remove <pacote>`
(`--dev` para as de desenvolvimento) e `uv lock --upgrade` para atualizar
as versões; em todos os casos faça commit do `uv.lock` junto.

Ou com Docker Compose:

```sh
cp .env.example .env         # defina SECRET_KEY
docker compose up -d --build # app em http://localhost:8000
docker compose watch         # modo desenvolvimento: reinicia ao editar src/
docker compose down          # para (os dados ficam no volume)
```

No Docker, o banco SQLite e as imagens enviadas ficam no volume `data`
(montado em `/data`), então sobrevivem a rebuilds. `docker compose down -v` apaga o volume.

### Variáveis de ambiente

| Variável        | Padrão                         | Uso                                             |
|-----------------|--------------------------------|-------------------------------------------------|
| `SECRET_KEY`    | gerada a cada início           | assina os cookies de sessão                     |
| `DATABASE_URL`  | `sqlite:///database.db`        | banco de dados                                  |
| `UPLOAD_DIR`    | `src/openloja/static/images`   | onde ficam as imagens enviadas                  |
| `COOKIE_SECURE` | `false`                        | `true` quando o site estiver atrás de HTTPS     |

Bancos criados por versões anteriores são atualizados automaticamente ao iniciar,
e senhas antigas (em texto puro) passam a ser guardadas com hash no próximo login.

### CI

A cada push e pull request, o GitHub Actions (`.github/workflows/ci.yml`) roda o
lint (ruff), os testes e um build + smoke test da imagem Docker. Para rodar as
mesmas verificações localmente (só precisa de Docker):

```sh
scripts/ci.sh              # lint, testes e imagem Docker
scripts/ci.sh --no-docker  # só lint e testes
```

Também há hooks de pre-commit (`pre-commit install`) para lint a cada commit.
