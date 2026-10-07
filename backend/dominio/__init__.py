"""Regra de negocio pura: entra dado, sai dado.

Nenhum modulo daqui abre sessao, fala HTTP ou conhece FastAPI. E o que
permite testar a decisao sem subir banco, e o que deixa a mesma conta
servir a API e a tela.
"""
