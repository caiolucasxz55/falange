"""Porteiros que rodam antes de qualquer rota.

Ficam fora de `main.py` para o arquivo do app continuar legivel, e fora de
`rotas/` porque nao sao rota: valem para todas de uma vez.
"""

import time
from collections import defaultdict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.dominio.limite import permitido, segundos_para_liberar
from backend.seguranca import exige_token, token_valido

# Historico por cliente. Em memoria: morre no restart e nao e compartilhado
# entre replicas. Suficiente para barrar script, nao para abuso distribuido.
_HISTORICO: dict[str, list[float]] = defaultdict(list)

# Fora do teto de requisicoes: o healthcheck do docker bate aqui sem parar.
SEM_LIMITE = ("/health",)


async def limitar_taxa(request, proxima):
    """Teto de requisicoes por cliente, para ninguem encher o banco em rajada.

    Atencao: atras do proxy do frontend, TODA a tela chega com um IP so, e o
    time inteiro divide o mesmo teto.
    """
    if settings.limite_por_minuto > 0 and request.url.path not in SEM_LIMITE:
        cliente = request.client.host if request.client else "desconhecido"
        agora = time.monotonic()
        passa, historico = permitido(
            _HISTORICO[cliente], agora, maximo=settings.limite_por_minuto
        )
        _HISTORICO[cliente] = historico
        if not passa:
            espera = segundos_para_liberar(historico, agora)
            return JSONResponse(
                {"detail": f"limite de requisicoes atingido; tente em {espera}s"},
                status_code=429,
                headers={"Retry-After": str(espera or 60)},
            )
    return await proxima(request)


async def exigir_token(request, proxima):
    """Porteiro da API: sem o token certo, nao entra.

    CORS nao e seguranca: ele so restringe navegador. Qualquer curl alcanca
    a API sem passar por ele, entao a checagem acontece aqui.
    """
    if exige_token(request.url.path, request.method, settings.api_token):
        if not token_valido(request.headers.get("authorization"), settings.api_token):
            return JSONResponse({"detail": "token invalido ou ausente"}, status_code=401)
    return await proxima(request)


def registrar(app: FastAPI) -> None:
    """Pendura os middlewares na ordem certa.

    O Starlette executa na ordem INVERSA do registro, entao registrar o
    limite antes do token faz o token ser conferido primeiro. Mantenha
    assim: barrar quem nao tem token antes de gastar o historico dele.
    """
    app.middleware("http")(limitar_taxa)
    app.middleware("http")(exigir_token)
