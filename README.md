# OpenLoja
Projeto final de MAC0350/26.<br>

O OpenLoja consiste em um site de vendas e controle de estoque genérico de fácil customização para diferentes tipos de produtos. Buscamos congregar simplicidade de comunicação vendedor-cliente, gerência e disponibilidade de produtos gratuitamente.

## Ambiente de Desenvolvimento

Para desenvolver, basta criar um ambiente virtual que contenha as bibliotecas em <requirements.txt>.
Também é possível rodar com Docker Compose:

```sh
cp .env.example .env        # defina SECRET_KEY
docker compose up -d --build # app em http://localhost:8000
docker compose watch         # modo desenvolvimento: reinicia ao editar src/
docker compose down          # para (os dados ficam nos volumes)
```

O banco SQLite fica no volume `db-data` e as imagens enviadas no volume `images`,
então sobrevivem a rebuilds. `docker compose down -v` apaga ambos.

Há softwares de Lint e verificação de código a cada commit e push. Verifique se todos arquivos e modificações passam nos testes.
