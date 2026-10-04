"use client";

import { useEffect, useState } from "react";

import {
  definirConfiguracao,
  mensagemDoErro,
  verConfiguracao,
  verPriorizacao,
} from "@/lib/api";
import type { Alerta, Configuracao, Priorizacao } from "@/types/task";

// Cor por tipo de alerta: inversao e o que mais pede acao.
const ESTILO_ALERTA: Record<Alerta["tipo"], string> = {
  inversao: "border-amber-300 bg-amber-50 text-amber-900",
  inflacao: "border-gray-300 bg-gray-50 text-gray-700",
  parada: "border-amber-300 bg-amber-50 text-amber-900",
};

type Resultado =
  | { versao: number; tipo: "ok"; dados: Priorizacao }
  | { versao: number; tipo: "erro"; mensagem: string };

interface PainelRecomendadasProps {
  /** Muda quando o board muda: a recomendacao precisa acompanhar. */
  versao: number;
}

/** Top 3 do motor de priorizacao, com os motivos e os alertas da fila.
 *
 * So leitura e sem IA: a mesma regra que a IA consulta, na tela. */
export function PainelRecomendadas({ versao }: PainelRecomendadasProps) {
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [config, setConfig] = useState<Configuracao | null>(null);
  const [erroConfig, setErroConfig] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    verPriorizacao(3)
      .then((dados) => {
        if (ativo) setResultado({ versao, tipo: "ok", dados });
      })
      .catch((e: unknown) => {
        if (ativo) setResultado({ versao, tipo: "erro", mensagem: mensagemDoErro(e) });
      });
    return () => {
      ativo = false;
    };
  }, [versao]);

  useEffect(() => {
    let ativo = true;
    verConfiguracao()
      .then((c) => {
        if (ativo) setConfig(c);
      })
      .catch(() => {
        // Sem configuracao o painel ainda serve; o interruptor e que some.
      });
    return () => {
      ativo = false;
    };
  }, []);

  function alternarPerguntas(ativas: boolean) {
    setErroConfig(null);
    // Otimista: o checkbox e controlado, entao sem isto ele so se mexeria
    // depois da ida e volta ao servidor. Falhou, volta ao que era.
    const anterior = config;
    setConfig({ perguntas_ativas: ativas });
    definirConfiguracao({ perguntas_ativas: ativas })
      .then(setConfig)
      .catch((e: unknown) => {
        setConfig(anterior);
        setErroConfig(mensagemDoErro(e));
      });
  }

  const dados = resultado?.tipo === "ok" ? resultado.dados : null;

  return (
    <section className="mb-4 rounded border border-gray-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-900">Proximas recomendadas</h2>
        {config && (
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={config.perguntas_ativas}
              onChange={(e) => alternarPerguntas(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            a IA pergunta antes de decidir
          </label>
        )}
      </div>

      {erroConfig && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {erroConfig}
        </p>
      )}

      {resultado?.tipo === "erro" && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          Nao foi possivel carregar as recomendacoes: {resultado.mensagem}
        </p>
      )}

      {dados?.avisos.map((aviso) => (
        <p
          key={aviso}
          className="mt-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900"
        >
          {aviso}
        </p>
      ))}

      {dados && dados.sugestoes.length > 0 && (
        <ol className="mt-3 space-y-2">
          {dados.sugestoes.map((sugestao, posicao) => (
            <li
              key={sugestao.id}
              className="rounded border border-gray-200 p-2 text-sm"
            >
              <div className="flex items-start gap-2">
                <span className="mt-0.5 text-xs font-medium text-gray-400">
                  {posicao + 1}
                </span>
                <div className="min-w-0">
                  <p className="font-medium text-gray-900">
                    <span className="mr-1 text-gray-400">#{sugestao.id}</span>
                    {sugestao.titulo}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-600">
                    {sugestao.motivos.join(" · ")}
                  </p>
                </div>
                <span className="ml-auto shrink-0 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {sugestao.score}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}

      {dados && dados.sugestoes.length === 0 && (
        <p className="mt-3 text-xs text-gray-400">
          Nenhuma task livre: o que resta esta bloqueado ou concluido.
        </p>
      )}

      {dados && dados.alertas.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {dados.alertas.map((alerta, indice) => (
            <li
              key={`${alerta.tipo}-${alerta.task_id ?? indice}`}
              className={`rounded border p-2 text-xs ${ESTILO_ALERTA[alerta.tipo]}`}
            >
              <span className="font-medium">{alerta.tipo}</span> · {alerta.mensagem}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
