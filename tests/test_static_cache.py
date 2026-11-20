"""Arquivos estáticos são versionados para não ficarem presos no cache."""

import re

from helpers import vendedor_logado


def test_scripts_e_estilos_tem_versao_na_url(client):
    vendedor_logado(client)

    html = client.get("/orders").text

    assert re.search(r'src="/static/ordersScript\.js\?v=\d+"', html)
    assert re.search(r'href="/static/ordersStyle\.css\?v=\d+"', html)
    assert (
        client.get(re.search(r"/static/ordersScript\.js\?v=\d+", html)[0]).status_code
        == 200
    )
