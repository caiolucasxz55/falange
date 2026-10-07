"""Token de acesso (JWT) e token de renovacao (opaco).

Modulo puro: entra dado, sai dado. Nao abre sessao de banco e nao faz HTTP.

Por que os dois juntos: JWT nao revoga. Assinatura valida e assinatura
valida ate expirar, entao logout, usuario removido ou papel rebaixado
continuariam valendo pelo resto da validade. Por isso:

- o **access** e JWT curto, e serve para carregar a identidade sem poder
  ser forjado;
- o **refresh** e um texto aleatorio guardado NO BANCO (so o hash), que o
  humano pode invalidar na hora.

E por isso tambem que o `papel` dentro do JWT e informativo, nao autoridade:
quem decide e a linha do usuario no banco, lida a cada request. Rebaixar
alguem tem efeito imediato, sem esperar o token vencer. Sem isso, um admin
rebaixado seguiria admin por toda a validade do token.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

ALGORITMO = "HS256"

# Tamanho em bytes do segredo do refresh, antes do base64.
BYTES_REFRESH = 32


def criar_access(
    usuario_id: int,
    sessao_id: int,
    papel: str,
    segredo: str,
    minutos: int,
    agora: Optional[datetime] = None,
) -> str:
    """JWT curto que identifica usuario e sessao."""
    inicio = agora or datetime.now(timezone.utc)
    corpo = {
        "sub": str(usuario_id),
        "sid": sessao_id,
        # Informativo: a tela usa para desenhar sem esperar o /eu. A API
        # NAO confia nisto -- le o papel do banco.
        "papel": papel,
        "iat": inicio,
        "exp": inicio + timedelta(minutes=minutos),
    }
    return jwt.encode(corpo, segredo, algorithm=ALGORITMO)


def ler_access(token: str, segredo: str) -> Optional[dict]:
    """Corpo do JWT, ou None se invalido, expirado ou mexido.

    Qualquer falha devolve None de proposito: a rota nao precisa saber se o
    token venceu ou se a assinatura nao bate, e distinguir isso para quem
    chama entrega informacao de graca.
    """
    try:
        corpo = jwt.decode(token, segredo, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None
    try:
        return {
            "usuario_id": int(corpo["sub"]),
            "sessao_id": int(corpo["sid"]),
            "papel": corpo.get("papel"),
        }
    except (KeyError, TypeError, ValueError):
        # Assinado com o nosso segredo, mas sem os campos que esperamos.
        return None


def gerar_refresh() -> tuple[str, str]:
    """Devolve (token para o cliente, hash para o banco).

    O banco guarda so o hash: um vazamento da tabela nao da sessao a
    ninguem. sha256 puro basta aqui, diferente de senha -- o segredo tem
    256 bits de entropia, entao nao existe dicionario para percorrer.
    """
    bruto = secrets.token_urlsafe(BYTES_REFRESH)
    return bruto, hash_refresh(bruto)


def hash_refresh(bruto: str) -> str:
    return hashlib.sha256(bruto.encode()).hexdigest()


def refresh_confere(bruto: str, guardado: str) -> bool:
    """Comparacao em tempo constante, para nao vazar o prefixo comum."""
    return secrets.compare_digest(hash_refresh(bruto), guardado)


def expira_em(dias: int, agora: Optional[datetime] = None) -> datetime:
    return (agora or datetime.now(timezone.utc)) + timedelta(days=dias)
