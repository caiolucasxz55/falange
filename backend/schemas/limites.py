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


def recusar_nulos(*campos: str):
    """Validador que recusa `campo: null` explicito nos campos dados.

    Nos schemas de edicao parcial todo campo e `Optional[...] = None`, porque
    e assim que "nao enviado" se escreve. O problema: `exclude_unset` nao
    distingue "nao enviei" de "enviei null" -- nos dois casos o campo some ou
    sobra como None. Com `{"papel": null}`, o None atravessava a rota e ia
    para uma coluna NOT NULL, virando IntegrityError 500.

    Nulo NAO e proibido em tudo: `responsavel: null` remove o responsavel e
    `task_id: null` desliga a nota da task. Por isso a lista e explicita --
    passe aqui so os campos que a tabela declara NOT NULL.
    """

    def validar(dados):
        # `mode="before"` tambem recebe instancia do proprio modelo; nesse
        # caso nao ha dict de entrada para inspecionar.
        if not isinstance(dados, dict):
            return dados
        nulos = sorted(c for c in campos if c in dados and dados[c] is None)
        if nulos:
            raise ValueError(f"nao aceita nulo em: {', '.join(nulos)}")
        return dados

    return validar
