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
from backend.config import settings
from backend.rotas import analise, aprendizado, autonomia, configuracao, notas, saude
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
app.include_router(rotas_tasks.rotas)
app.include_router(notas.rotas)
app.include_router(analise.rotas)
app.include_router(configuracao.rotas)
app.include_router(aprendizado.rotas)
app.include_router(autonomia.rotas)


@app.on_event("startup")
async def avisar_porta_aberta():
    if not settings.api_token:
        # Barulhento de proposito: ninguem deve subir isto exposto sem token.
        print("ATENCAO: API_TOKEN vazio, a API esta aberta a quem alcancar a porta")
