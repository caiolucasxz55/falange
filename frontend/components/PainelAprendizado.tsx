"use client";

import { useEffect, useState } from "react";

import {
  definirPreferencia,
  listarPreferencias,
  mensagemDoErro,
  verPerfil,
} from "@/lib/api";
import { useSessao } from "@/components/SessaoProvider";
import type { ClasseCalibrada, Perfil, Preferencia } from "@/types/task";

const ESTILO_VEREDITO: Record<ClasseCalibrada["veredito"], string> = {
  coerente: "bg-gray-100 text-gray-700",
  superestimada: "bg-amber-100 text-amber-900",
  subestimada: "bg-amber-100 text-amber-900",
  sem_dados: "bg-gray-100 text-gray-400",
};

type Resultado =
  | { versao: number; tipo: "ok"; perfil: Perfil; preferencias: Preferencia[] }
  | { versao: number; tipo: "erro"; mensagem: string };

/** O que o Falange aprendeu: calibracao, correcoes e preferencias.
 *
 * As inferidas aparecem para confirmar ou descartar. Desativar qualquer uma
 * e sempre um clique: a regra e do time, nao da IA. */
export function PainelAprendizado() {
  const { pode } = useSessao();
  const podeAtivar = pode("ativar_preferencia");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [versao, setVersao] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    let ativo = true;
    Promise.all([verPerfil(), listarPreferencias()])
      .then(([perfil, preferencias]) => {
        if (ativo) setResultado({ versao, tipo: "ok", perfil, preferencias });
      })
      .catch((e: unknown) => {
        if (ativo) setResultado({ versao, tipo: "erro", mensagem: mensagemDoErro(e) });
      });
    return () => {
      ativo = false;
    };
  }, [versao]);

  function alternar(id: number, ativa: boolean) {
    setOcupado(true);
    setErro(null);
    definirPreferencia(id, ativa)
      .then(() => setVersao((v) => v + 1))
      .catch((e: unknown) => setErro(mensagemDoErro(e)))
      .finally(() => setOcupado(false));
  }

  const perfil = resultado?.tipo === "ok" ? resultado.perfil : null;
  const preferencias = resultado?.tipo === "ok" ? resultado.preferencias : [];
  const inferidas = preferencias.filter((p) => p.origem === "inferida" && !p.ativa);
  const ativas = preferencias.filter((p) => p.ativa);
  const classes = Object.entries(perfil?.calibracao?.por_estimativa ?? {}).filter(
    ([, dados]) => dados.n > 0,
  );

  const botao =
    "rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50";

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">O que o Falange aprendeu</h2>
      <p className="mt-1 text-xs text-gray-500">
        Sai das escolhas do time, nao de palpite da IA.
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

      <h3 className="mt-3 text-xs font-medium text-gray-700">Estimativas</h3>
      {classes.length === 0 ? (
        <p className="mt-1 text-xs text-gray-400">
          Ainda sem task concluida com os dois marcos de tempo.
        </p>
      ) : (
        <ul className="mt-1 flex flex-wrap gap-1.5">
          {classes.map(([classe, dados]) => (
            <li
              key={classe}
              className={`rounded px-2 py-0.5 text-xs ${ESTILO_VEREDITO[dados.veredito]}`}
              title={`mediana ${dados.mediana_dias} dias`}
            >
              {classe}: {dados.veredito} (n={dados.n})
            </li>
          ))}
        </ul>
      )}

      <h3 className="mt-3 text-xs font-medium text-gray-700">Correcoes mais comuns</h3>
      {perfil && perfil.ajustes_comuns.length > 0 ? (
        <ul className="mt-1 space-y-1">
          {perfil.ajustes_comuns.map((frase) => (
            <li key={frase} className="text-xs text-gray-600">
              {frase}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-xs text-gray-400">Ninguem corrigiu a IA ainda.</p>
      )}

      {inferidas.length > 0 && (
        <>
          <h3 className="mt-3 text-xs font-medium text-gray-700">
            Padroes aguardando confirmacao
          </h3>
          <ul className="mt-1 space-y-2">
            {inferidas.map((preferencia) => (
              <li
                key={preferencia.id}
                className="rounded border border-amber-300 bg-amber-50 p-2"
              >
                <p className="text-xs text-amber-900">{preferencia.descricao}</p>
                <div className="mt-1.5 flex gap-1.5">
                  {podeAtivar && (
                    <button
                      type="button"
                      disabled={ocupado}
                      onClick={() => alternar(preferencia.id, true)}
                      className="rounded bg-gray-900 px-2 py-0.5 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50"
                    >
                      Confirmar
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={ocupado}
                    onClick={() => alternar(preferencia.id, false)}
                    className={botao}
                  >
                    Descartar
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3 className="mt-3 text-xs font-medium text-gray-700">Preferencias ativas</h3>
      {ativas.length === 0 ? (
        <p className="mt-1 text-xs text-gray-400">Nenhuma ainda.</p>
      ) : (
        <ul className="mt-1 space-y-1">
          {ativas.map((preferencia) => (
            <li
              key={preferencia.id}
              className="flex items-center gap-2 rounded border border-gray-200 p-2"
            >
              <span className="min-w-0 text-xs text-gray-700">
                {preferencia.descricao}
              </span>
              <span className="text-xs text-gray-400">{preferencia.origem}</span>
              <button
                type="button"
                disabled={ocupado}
                onClick={() => alternar(preferencia.id, false)}
                className={`ml-auto shrink-0 ${botao}`}
              >
                Desativar
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
