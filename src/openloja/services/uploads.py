"""Gravação das imagens enviadas pelo vendedor."""

import os
import shutil

from fastapi import HTTPException, UploadFile

from ..config import settings

EXTENSOES_PERMITIDAS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}


def salvar_imagem(arquivo: UploadFile, prefixo: str) -> str:
    """Salva o arquivo em UPLOAD_DIR e devolve o caminho relativo a /static."""
    nome = os.path.basename(arquivo.filename or "")
    extensao = os.path.splitext(nome)[1].lower()

    if not nome or extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            400,
            "Formato de imagem não suportado. Use: "
            + ", ".join(sorted(EXTENSOES_PERMITIDAS)),
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    nome_final = f"{prefixo}_{nome}"

    with open(settings.upload_dir / nome_final, "wb") as destino:
        shutil.copyfileobj(arquivo.file, destino)

    return f"images/{nome_final}"
