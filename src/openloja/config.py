"""Configurações da aplicação, lidas de variáveis de ambiente."""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _bool_env(nome: str, padrao: bool = False) -> bool:
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _secret_key() -> str:
    chave = os.environ.get("SECRET_KEY")
    if chave:
        return chave

    print(
        "AVISO: variável de ambiente SECRET_KEY não definida.",
        "Usando uma chave temporária gerada agora (as sessões expiram ao reiniciar).",
    )
    return secrets.token_hex(32)


@dataclass
class Settings:
    # chave usada para assinar os cookies de sessão
    secret_key: str = field(default_factory=_secret_key)

    # URL do banco (SQLAlchemy). Ex.: sqlite:////data/database.db
    database_url: str = field(
        default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///database.db")
    )

    # pasta onde as imagens enviadas (logo, banner, produtos) são salvas;
    # é servida em /static/images
    upload_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("UPLOAD_DIR", PACKAGE_DIR / "static" / "images")
        )
    )

    # marque como true quando o site estiver atrás de HTTPS
    cookie_secure: bool = field(default_factory=lambda: _bool_env("COOKIE_SECURE"))

    # duração máxima de uma sessão, em segundos (7 dias)
    session_max_age: int = 60 * 60 * 24 * 7


settings = Settings()

STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATES_DIR = PACKAGE_DIR / "templates"
