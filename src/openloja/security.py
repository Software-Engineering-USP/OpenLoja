"""Hash de senhas e cookie de sessão assinado."""

import base64
import hashlib
import hmac
import secrets

from fastapi import Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .config import settings

SESSION_COOKIE = "session"

# ---------------------------------------------------------------------
# Senhas: scrypt (biblioteca padrão), formato "scrypt$<salt>$<hash>"
# ---------------------------------------------------------------------

_PREFIXO = "scrypt"
_N, _R, _P = 2**14, 8, 1


def _scrypt(senha: str, salt: bytes) -> bytes:
    return hashlib.scrypt(senha.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).decode()


def hash_senha(senha: str) -> str:
    salt = secrets.token_bytes(16)
    return f"{_PREFIXO}${_b64(salt)}${_b64(_scrypt(senha, salt))}"


def senha_tem_hash(armazenada: str) -> bool:
    return armazenada.startswith(f"{_PREFIXO}$")


def verificar_senha(senha: str, armazenada: str) -> bool:
    if not senha_tem_hash(armazenada):
        # contas criadas antes do hash: comparação direta (o login
        # converte a senha para hash em seguida)
        return hmac.compare_digest(senha.encode(), armazenada.encode())

    try:
        _, salt_b64, hash_b64 = armazenada.split("$")
        salt = base64.urlsafe_b64decode(salt_b64)
        esperado = base64.urlsafe_b64decode(hash_b64)
    except ValueError:
        return False

    return hmac.compare_digest(_scrypt(senha, salt), esperado)


# ---------------------------------------------------------------------
# Sessão
# ---------------------------------------------------------------------

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session-cookie")


def criar_sessao(response: Response, nome: str, tipo: str) -> None:
    token = _serializer.dumps({"nome": nome, "tipo": tipo})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_max_age,
    )


def encerrar_sessao(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def ler_sessao(token: str | None) -> dict | None:
    """Decodifica o cookie; None se ausente, expirado ou inválido."""
    if not token:
        return None

    try:
        dados = _serializer.loads(token, max_age=settings.session_max_age)
    except BadSignature:
        return None

    if not isinstance(dados, dict) or "nome" not in dados or "tipo" not in dados:
        return None

    return dados
