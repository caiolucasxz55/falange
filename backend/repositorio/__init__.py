"""Acesso ao banco, um modulo por agregado.

Toda regra de banco mora aqui; as rotas so traduzem HTTP. Nenhum modulo
daqui conhece FastAPI, e nenhum levanta HTTPException: devolve None, False
ou uma tupla (valor, erro) e quem decide o status e a rota.
"""
