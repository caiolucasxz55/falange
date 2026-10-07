"""Configuracao do backend, lida do .env (ou de variaveis de ambiente)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://falange:falange@127.0.0.1:5432/falange"

    # Acima de quantas tasks abertas uma pessoa/bloco e considerado sobrecarregado.
    limite_sobrecarga: int = 5

    # Origens que o navegador pode usar para chamar a API (o frontend Next).
    # 3010 e nao 3000: nesta maquina a 3000 e do resinarts_frontend.
    # No .env, em JSON: CORS_ORIGINS=["http://localhost:3010"]
    cors_origins: list[str] = ["http://localhost:3010"]

    # Segredo compartilhado exigido em toda chamada. Vazio = porta aberta,
    # aceitavel so em dev local. Em qualquer maquina que o time alcance,
    # preencha: sem isso, quem chega na porta cria e apaga task.
    api_token: str = ""

    # Teto de requisicoes por cliente por minuto; 0 desliga. Atras do proxy
    # do frontend o time inteiro conta como um cliente so.
    limite_por_minuto: int = 300

    # Segredo que assina o access token. Vazio = login desligado (nao da
    # para emitir token sem ele). Trocar este valor desloga todo mundo.
    jwt_segredo: str = ""

    # Validade do access token. Curta de proposito: e o unico intervalo em
    # que um token ja emitido sobrevive a uma troca de segredo. Revogacao de
    # sessao e de papel e imediata, porque a API le o banco a cada request.
    jwt_minutos: int = 15

    # Validade do refresh. Passado isso, login de novo.
    sessao_dias: int = 14

    # true: toda chamada precisa de login (ou do token do MCP). false: quem
    # chega com o token compartilhado e sem o header do MCP e tratado como
    # admin sem login, que e o comportamento de antes da V2. Serve para a
    # transicao: vira true quando a tela tiver login.
    exigir_login: bool = False


# HMAC-SHA256 com chave curta e fraca (RFC 7518, secao 3.2), e o pyjwt
# avisa. Barrar na subida evita descobrir isso em producao.
MIN_JWT_SEGREDO = 32

settings = Settings()
