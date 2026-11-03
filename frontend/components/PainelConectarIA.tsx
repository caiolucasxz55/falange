"use client";

import { useEffect, useState } from "react";

import { useSessao } from "@/components/SessaoProvider";
import {
  criarTokenMCP,
  listarTokensMCP,
  mensagemDoErro,
  revogarTokenMCP,
} from "@/lib/api";
import type { TokenMCP, TokenMCPCriado } from "@/types/task";

/**
 * Porta do servidor MCP remoto nesta maquina.
 *
 * Fixa aqui, e nao vinda do backend, porque e o endereco de UM processo que
 * o compose sobe ao lado -- o backend nao sabe nem se ele esta no ar. Em
 * outra instalacao, trocar aqui.
 */
const PORTA_SSE = 8765;

function enderecoSSE(): string {
  if (typeof window === "undefined") return `http://127.0.0.1:${PORTA_SSE}/sse`;
  // O host de quem esta olhando, nao "localhost": quem abre a tela de outra
  // maquina da rede precisa do endereco que funciona para ELE.
  return `${window.location.protocol}//${window.location.hostname}:${PORTA_SSE}/sse`;
}

/** O `.mcp.json` pronto para colar, com o token dentro. */
function configuracaoMCP(token: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        falange: {
          type: "sse",
          url: enderecoSSE(),
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );
}

function dataCurta(iso: string | null): string {
  if (!iso) return "nunca";
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
}

/**
 * "Conectar sua IA": a pessoa gera o proprio token e conecta como ela mesma.
 *
 * Existe porque, antes dele, ligar a IA no Falange exigia ter o repositorio
 * clonado -- e quem entrava pelo servidor remoto usava as credenciais DO
 * SERVIDOR, entao duas pessoas eram a mesma conta para o backend.
 *
 * O painel NAO guarda o segredo em lugar nenhum: ele aparece uma vez, no
 * estado desta tela, e se vai quando a pessoa fecha o aviso. Guardar em
 * `localStorage` para "poder ver depois" desfaria o ponto de so mostrar
 * uma vez.
 */
export function PainelConectarIA() {
  const { eu } = useSessao();
  const [tokens, setTokens] = useState<TokenMCP[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [erroCarga, setErroCarga] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [ocupado, setOcupado] = useState(false);

  const [nome, setNome] = useState("");
  const [dias, setDias] = useState("");
  const [recemCriado, setRecemCriado] = useState<TokenMCPCriado | null>(null);
  const [copiou, setCopiou] = useState<"token" | "config" | null>(null);
  const [confirmando, setConfirmando] = useState<number | null>(null);

  // Sem conta, nao ha "meus tokens": a conta de servico entra pelo token
  // compartilhado e a API recusa criar token para ela.
  const logado = eu?.usuario != null;

  useEffect(() => {
    if (!logado) return;
    let ativo = true;
    listarTokensMCP()
      .then((lista) => {
        if (ativo) {
          setTokens(lista);
          setErroCarga(null);
        }
      })
      .catch((e: unknown) => {
        if (ativo) setErroCarga(mensagemDoErro(e));
      });
    return () => {
      ativo = false;
    };
  }, [logado, versao]);

  async function copiar(texto: string, qual: "token" | "config") {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiou(qual);
      window.setTimeout(() => setCopiou(null), 2000);
    } catch {
      // Clipboard bloqueado (http sem localhost, permissao negada): o
      // texto esta na tela em campo selecionavel, entao da para copiar a
      // mao. Falhar em silencio aqui e melhor que um alerta inutil.
    }
  }

  function criar() {
    setOcupado(true);
    setErro(null);
    const prazo = dias.trim() === "" ? null : Number(dias);
    if (prazo !== null && (!Number.isInteger(prazo) || prazo < 1)) {
      setErro("dias tem de ser um numero inteiro de 1 em diante, ou vazio");
      setOcupado(false);
      return;
    }

    criarTokenMCP({ nome: nome.trim(), dias: prazo })
      .then((criado) => {
        setRecemCriado(criado);
        setNome("");
        setDias("");
        setVersao((v) => v + 1);
      })
      .catch((e: unknown) => setErro(mensagemDoErro(e)))
      .finally(() => setOcupado(false));
  }

  function revogar(tokenId: number) {
    setOcupado(true);
    setErro(null);
    revogarTokenMCP(tokenId)
      .then(() => {
        setConfirmando(null);
        // Se o segredo na tela e justamente o que acabou de ser revogado,
        // sumir com ele: deixar visivel um token morto convida a colar.
        setRecemCriado((atual) => (atual?.id === tokenId ? null : atual));
        setVersao((v) => v + 1);
      })
      .catch((e: unknown) => setErro(mensagemDoErro(e)))
      .finally(() => setOcupado(false));
  }

  const campo =
    "rounded border border-gray-300 px-2 py-1 text-xs text-gray-900 placeholder:text-gray-400";
  const botao =
    "rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50";

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">Conectar sua IA</h2>
      <p className="mt-1 text-xs text-gray-500">
        Gere um token, cole o <code>.mcp.json</code> no seu cliente e a IA
        passa a trabalhar no Falange <strong>como voce</strong>: as tasks saem
        com o seu nome, e ela so alcanca o que o seu papel alcanca. Nao
        precisa ter o repositorio.
      </p>

      {!logado && (
        <p className="mt-2 rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-600">
          Entre com a sua conta para gerar um token: ele existe para
          identificar uma pessoa, e sem login nao ha quem identificar.
        </p>
      )}

      {logado && (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="meu notebook"
              aria-label="Nome do token"
              className={`${campo} w-44`}
            />
            <input
              value={dias}
              onChange={(e) => setDias(e.target.value)}
              inputMode="numeric"
              placeholder="dias (opcional)"
              aria-label="Dias de validade"
              className={`${campo} w-32`}
            />
            <button
              type="button"
              disabled={ocupado || nome.trim().length < 2}
              onClick={criar}
              className="rounded bg-gray-900 px-3 py-1 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50"
            >
              Gerar token
            </button>
            <span className="text-xs text-gray-400">
              sem prazo, vale ate voce revogar
            </span>
          </div>

          {erro && (
            <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
              {erro}
            </p>
          )}

          {recemCriado && (
            <div className="mt-3 rounded border border-amber-300 bg-amber-50 p-3">
              <p className="text-xs font-medium text-amber-900">
                Copie agora: este token nao volta a aparecer.
              </p>
              <p className="mt-1 text-xs text-amber-800">
                Perdido, o caminho e revogar e gerar outro. Nem o Falange
                consegue mostrar de novo -- o banco guarda so o hash.
              </p>

              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  readOnly
                  value={recemCriado.token}
                  onFocus={(e) => e.currentTarget.select()}
                  aria-label="Token de conexao"
                  className="min-w-0 flex-1 rounded border border-amber-300 bg-white px-2 py-1 font-mono text-xs text-gray-900"
                />
                <button
                  type="button"
                  className={botao}
                  onClick={() => copiar(recemCriado.token, "token")}
                >
                  {copiou === "token" ? "copiado" : "copiar token"}
                </button>
              </div>

              <p className="mt-3 text-xs font-medium text-amber-900">
                Ou cole isto direto no seu <code>.mcp.json</code>:
              </p>
              {/*
                `whitespace-pre-wrap break-words`, e nao scroll horizontal:
                o painel mora numa coluna de 20rem, e um token de 56 chars
                nao cabe. Com scroll, a linha do `Authorization` ficava
                cortada na borda e a pessoa nao via o que ia copiar.
              */}
              <pre className="mt-1 max-h-56 overflow-y-auto whitespace-pre-wrap break-words rounded border border-amber-300 bg-white p-2 font-mono text-[11px] leading-relaxed text-gray-800">
                {configuracaoMCP(recemCriado.token)}
              </pre>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className={botao}
                  onClick={() =>
                    copiar(configuracaoMCP(recemCriado.token), "config")
                  }
                >
                  {copiou === "config" ? "copiado" : "copiar .mcp.json"}
                </button>
                <button
                  type="button"
                  className={botao}
                  onClick={() => setRecemCriado(null)}
                >
                  Ja copiei, fechar
                </button>
              </div>
            </div>
          )}

          {erroCarga && (
            <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
              Nao foi possivel carregar os seus tokens: {erroCarga}
            </p>
          )}

          {tokens?.length === 0 && (
            <p className="mt-3 text-xs text-gray-500">
              Voce ainda nao tem token nenhum.
            </p>
          )}

          {tokens && tokens.length > 0 && (
            <ul className="mt-3 space-y-2">
              {tokens.map((token) => (
                <li
                  key={token.id}
                  className="rounded border border-gray-200 p-2"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-medium text-gray-800">
                      {token.nome}
                    </span>
                    <code className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      flg_{token.prefixo}…
                    </code>
                    {token.ultimo_uso_em === null ? (
                      // Token gerado e nunca usado costuma ser o que a
                      // pessoa perdeu. Dizer isso ajuda a achar o que
                      // revogar.
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                        nunca usado
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500">
                        usado em {dataCurta(token.ultimo_uso_em)}
                      </span>
                    )}
                    {token.expira_em && (
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        vence {dataCurta(token.expira_em)}
                      </span>
                    )}
                    <button
                      type="button"
                      className={`${botao} ml-auto`}
                      disabled={ocupado}
                      onClick={() => setConfirmando(token.id)}
                    >
                      Revogar
                    </button>
                  </div>

                  {confirmando === token.id && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 rounded bg-red-50 p-2 text-xs text-red-800">
                      <span>
                        Revogar &quot;{token.nome}&quot;? A IA conectada por
                        ele para de responder na proxima chamada.
                      </span>
                      <button
                        type="button"
                        className="rounded bg-red-600 px-2 py-0.5 font-medium text-white hover:bg-red-700 disabled:opacity-50"
                        disabled={ocupado}
                        onClick={() => revogar(token.id)}
                      >
                        {ocupado ? "Revogando..." : "Sim, revogar"}
                      </button>
                      <button
                        type="button"
                        className={botao}
                        disabled={ocupado}
                        onClick={() => setConfirmando(null)}
                      >
                        Cancelar
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}

          <p className="mt-3 text-xs text-gray-400">
            O token nasce amarrado ao projeto selecionado no cabecalho, e nao
            da para mover depois. Ele tambem nao amplia nada: vale o que o seu
            papel vale. Desativar ou rebaixar a sua conta revoga todos.
          </p>
        </>
      )}
    </section>
  );
}
