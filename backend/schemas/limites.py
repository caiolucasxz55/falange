"""Tetos de tamanho dos campos livres.

Em modulo proprio porque mais de um schema depende deles e porque o teto e
uma decisao de seguranca, nao um detalhe de um contrato: Text e JSONB nao
tem limite no Postgres, entao sem isto um loop enche o disco.
"""

import json

# Folgado para texto humano, apertado para abuso.
MAX_DESCRICAO = 5000

# Teto do JSON de uma decisao, serializado.
MAX_JSON_DECISAO = 4000


def json_cabe(valor: dict, limite: int = MAX_JSON_DECISAO) -> dict:
    tamanho = len(json.dumps(valor, default=str))
    if tamanho > limite:
        raise ValueError(f"json com {tamanho} chars (maximo {limite})")
    return valor
