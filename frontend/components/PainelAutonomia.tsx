"use client";

import { useEffect, useState } from "react";

import { definirAutonomia, mensagemDoErro, verAutonomia } from "@/lib/api";
import type { Autonomia, NivelAutonomia } from "@/types/task";

const ROTULO_NIVEL: Record<NivelAutonomia, string> = {
  perguntar: "pergunta sempre",
  confirmar_em_lote: "confirma em lote",
  automatico: "automatico",
};

const ESTILO_NIVEL: Record<NivelAutonomia, string> = {
  perguntar: "bg-gray-100 text-gray-700",
  confirmar_em_lote: "bg-sky-100 text-sky-800",
  automatico: "bg-amber-100 text-amber-900",
};

const ROTULO_ACAO: Record<string, string> = {
  definir_prioridade: "definir prioridade",
  definir_estimativa: "definir estimativa",
  marcar_bloqueio: "marcar bloqueio",
  criar_pre_tasks_aprovadas: "criar pre-tasks aprovadas",
};

type Resultado =
  | { versao: number; tipo: "ok"; dados: Autonomia }
  | { versao: number; tipo: "erro"; mensagem: string };

/** Nivel de autonomia por acao.
 *
 * Daqui so da para REBAIXAR, com um clique. Subir e sempre pela conversa com
 * a IA, com um sim explicito. A assimetria e de proposito: tirar confianca
 * precisa ser facil; dar confianca precisa ser deliberado. */
export function PainelAutonomia() {
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [versao, setVersao] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    let ativo = true;
    verAutonomia()
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

  function rebaixar(acao: string, nivel: NivelAutonomia) {
    setOcupado(true);
    setErro(null);
    definirAutonomia(acao, nivel)
      .then(() => setVersao((v) => v + 1))
      .catch((e: unknown) => setErro(mensagemDoErro(e)))
      .finally(() => setOcupado(false));
  }

  const dados = resultado?.tipo === "ok" ? resultado.dados : null;

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">Autonomia da IA</h2>
      <p className="mt-1 text-xs text-gray-500">
        Rebaixar e um clique. Subir so na conversa com a IA, com um sim seu.
        Apagar task ou nota nunca entra aqui.
      </p>

      {erro && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {erro}
        </p>
      )}
      {resultado?.tipo === "erro" && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          Nao foi possivel carregar: {resultado.mensagem}
        </p>
      )}

      {dados && (
        <ul className="mt-3 space-y-2">
          {Object.entries(dados.acoes).map(([acao, estado]) => {
            const indice = dados.niveis.indexOf(estado.nivel);
            const abaixo = indice > 0 ? dados.niveis[indice - 1] : null;
            return (
              <li key={acao} className="rounded border border-gray-200 p-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-gray-800">
                    {ROTULO_ACAO[acao] ?? acao}
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs ${ESTILO_NIVEL[estado.nivel]}`}
                  >
                    {ROTULO_NIVEL[estado.nivel]}
                  </span>
                  {abaixo && (
                    <button
                      type="button"
                      disabled={ocupado}
                      onClick={() => rebaixar(acao, abaixo)}
                      className="ml-auto rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Rebaixar para {ROTULO_NIVEL[abaixo]}
                    </button>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {estado.pode ? `pode subir: ${estado.motivo}` : estado.motivo}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
