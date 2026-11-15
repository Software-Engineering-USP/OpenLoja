"""
Fixtures compartilhadas pelos testes de backend.

Cada teste roda contra um banco SQLite temporário e isolado, então
rodar os testes nunca mexe no database.db real.

Como rodar (na raiz do repositório):
    pip install -r requirements-dev.txt
    pytest
"""

import os
import tempfile

import pytest

# precisa ser definido antes de importar a aplicação
os.environ.setdefault("SECRET_KEY", "chave-de-teste-fixa-para-pytest")
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="openloja-uploads-")

from fastapi.testclient import TestClient

from openloja import database
from openloja.config import settings
from openloja.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Cliente de testes com banco e pasta de uploads exclusivos do teste."""
    engine_original = database.engine
    database.configure_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "images")

    with TestClient(app) as c:
        yield c

    database.engine.dispose()
    database.engine = engine_original
