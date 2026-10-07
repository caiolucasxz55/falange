"""API HTTP do Falange.

Este arquivo so monta o app: CORS, middlewares e os routers. Toda regra de
banco esta em `repositorio/`, toda conta esta em `dominio/`, e cada grupo de
rota tem seu arquivo em `rotas/`.

Os servidores MCP falam com o mundo por AQUI, nunca direto com o banco --
uma fonte de verdade so.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import middlewares
from backend.config import MIN_JWT_SEGREDO, settings
from backend.rotas import (
    analise,
    aprendizado,
    autonomia,
    configuracao,
    notas,
    saude,
    sessao,
    usuarios,
)
from backend.rotas import tasks as rotas_tasks

app = FastAPI(title="Falange")

# Sem isso o navegador bloqueia as chamadas do frontend (outra origem/porta).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

middlewares.registrar(app)

app.include_router(saude.rotas)
app.include_router(sessao.rotas)
app.include_router(usuarios.rotas)
app.include_router(rotas_tasks.rotas)
app.include_router(notas.rotas)
app.include_router(analise.rotas)
app.include_router(configuracao.rotas)
app.include_router(aprendizado.rotas)
app.include_router(autonomia.rotas)


@app.on_event("startup")
async def conferir_configuracao():
    if not settings.api_token:
        # Barulhento de proposito: ninguem deve subir isto exposto sem token.
        print("ATENCAO: API_TOKEN vazio, a API esta aberta a quem alcancar a porta")

    if not settings.jwt_segredo:
        print("ATENCAO: JWT_SEGREDO vazio, o login esta desligado (/sessao da 503)")
    elif len(settings.jwt_segredo) < MIN_JWT_SEGREDO:
        # Erro, nao aviso: chave curta em HMAC-SHA256 e fraca (RFC 7518), e
        # subir assim seria pior que nao subir. O pyjwt so avisa; aqui para.
        raise RuntimeError(
            f"JWT_SEGREDO tem {len(settings.jwt_segredo)} caracteres; "
            f"use pelo menos {MIN_JWT_SEGREDO}. "
            'Gere com: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    if settings.exigir_login and not settings.jwt_segredo:
        raise RuntimeError(
            "EXIGIR_LOGIN=true sem JWT_SEGREDO: ninguem conseguiria entrar"
        )
