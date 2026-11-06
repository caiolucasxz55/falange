"use client";

import { useEffect, useState } from "react";

import { useSessao } from "@/components/SessaoProvider";
import {
  apagarMarco,
  criarMarco,
  fecharMarco,
  listarMarcos,
  mensagemDoErro,
} from "@/lib/api";
import type { Marco } from "@/types/task";

/** "02/11/26" a partir de "2026-11-02", sem passar por fuso.
 *
 * `new Date("2026-11-02")` e lido como UTC e volta dia 1 a oeste de
 * Greenwich. A data aqui e rotulo de calendario, nao instante.
 */
function dataCurta(iso: string | null): string {
  if (!iso) return "sem prazo";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano.slice(2)}`;
}

/**
 * Marcos: criar, fechar e apagar a entrega com data.
 *
 * Esta tela existe porque a API a PROMETE. A IA leva 403 ao tentar criar
 * um marco, com a mensagem "peca ao dev para fazer isso na tela" -- e por
 * um tempo nao havia tela nenhuma, entao a unica forma de criar marco era
 * `curl`. Mensagem de erro que aponta para o que nao existe e pior que
 * erro sem explicacao: ela manda a pessoa procurar.
 *
 * A previsao de prazo NAO mora aqui: ela esta no painel Evolucao, junto do
 * throughput, porque "a entrega vai dar" e "o time esta andando" sao a
 * mesma pergunta vista de dois lados. Aqui e so a gestao.
 */
export function PainelMarcos() {
  const { pode } = useSessao();
  const podeGerir = pode("gerir_marcos");

  const [marcos, setMarcos] = useState<Marco[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [erroCarga, setErroCarga] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [ocupado, setOcupado] = useState(false);

  const [nome, setNome] = useState("");
  const [data, setData] = useState("");
  const [confirmando, setConfirmando] = useState<number | null>(null);

  useEffect(() => {
    let ativo = true;
    listarMarcos(true)
      .then((lista) => {
        if (ativo) {
          setMarcos(lista);
          setErroCarga(null);
        }
      })
      .catch((e: unknown) => ativo && setErroCarga(mensagemDoErro(e)));
    return () => {
      ativo = false;
    };
  }, [versao]);

  function executar(acao: () => Promise<unknown>) {
    setOcupado(true);
    setErro(null);
    acao()
      .then(() => setVersao((v) => v + 1))
      .catch((e: unknown) => setErro(mensagemDoErro(e)))
      .finally(() => setOcupado(false));
  }

  function criar() {
    executar(async () => {
      await criarMarco({
        nome: nome.trim(),
        // Vazio vira null: marco sem prazo e um caso legitimo, e a
        // previsao devolve `sem_data` em vez de fingir um veredito.
        data_alvo: data.trim() === "" ? null : data,
      });
      setNome("");
      setData("");
    });
  }

  const campo =
    "rounded border border-gray-300 px-2 py-1 text-xs text-gray-900 placeholder:text-gray-400";
  const botao =
    "rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50";

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">Marcos</h2>
      <p className="mt-1 text-xs text-gray-500">
        A entrega com data. Da dado real a &quot;pre-requisito de uma entrega
        proxima&quot; na regra de prioridade: task de marco que vence em ate 7
        dias sobe no ranking. A previsao de prazo aparece em Evolucao.
      </p>

      {!podeGerir && (
        <p className="mt-2 text-xs text-gray-500">
          Criar e fechar marco e de admin ou lead. Voce ve a lista.
        </p>
      )}

      {podeGerir && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Entrega de novembro"
            aria-label="Nome do marco"
            className={`${campo} w-48`}
          />
          <input
            type="date"
            value={data}
            onChange={(e) => setData(e.target.value)}
            aria-label="Data alvo"
            className={campo}
          />
          <button
            type="button"
            disabled={ocupado || nome.trim().length < 2}
            onClick={criar}
            className="rounded bg-gray-900 px-3 py-1 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            Criar marco
          </button>
          <span className="text-xs text-gray-400">data e opcional</span>
        </div>
      )}

      {erro && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {erro}
        </p>
      )}
      {erroCarga && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          Nao foi possivel carregar: {erroCarga}
        </p>
      )}

      {marcos?.length === 0 && (
        <p className="mt-3 text-xs text-gray-500">Nenhum marco ainda.</p>
      )}

      {marcos && marcos.length > 0 && (
        <ul className="mt-3 space-y-2">
          {marcos.map((marco) => {
            const fechado = marco.fechado_em !== null;
            return (
              <li key={marco.id} className="rounded border border-gray-200 p-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`text-xs font-medium ${fechado ? "text-gray-400 line-through" : "text-gray-800"}`}
                  >
                    {marco.nome}
                  </span>
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                    {dataCurta(marco.data_alvo)}
                  </span>
                  {fechado && (
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                      fechado
                    </span>
                  )}
                  {podeGerir && (
                    <>
                      <button
                        type="button"
                        className={`${botao} ml-auto`}
                        disabled={ocupado}
                        onClick={() =>
                          executar(() => fecharMarco(marco.id, !fechado))
                        }
                      >
                        {fechado ? "Reabrir" : "Fechar"}
                      </button>
                      <button
                        type="button"
                        className={botao}
                        disabled={ocupado}
                        onClick={() => setConfirmando(marco.id)}
                      >
                        Apagar
                      </button>
                    </>
                  )}
                </div>

                {confirmando === marco.id && (
                  <div className="mt-2 flex flex-wrap items-center gap-2 rounded bg-red-50 p-2 text-xs text-red-800">
                    {/*
                      Dizer o que NAO acontece e tao importante quanto o
                      que acontece: "apagar" soa como se levasse o
                      trabalho junto, e aqui a FK e SET NULL.
                    */}
                    <span>
                      Apagar &quot;{marco.nome}&quot;? As tasks dele continuam;
                      elas so deixam de ter marco.
                    </span>
                    <button
                      type="button"
                      className="rounded bg-red-600 px-2 py-0.5 font-medium text-white hover:bg-red-700 disabled:opacity-50"
                      disabled={ocupado}
                      onClick={() =>
                        executar(async () => {
                          await apagarMarco(marco.id);
                          setConfirmando(null);
                        })
                      }
                    >
                      {ocupado ? "Apagando..." : "Sim, apagar"}
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
            );
          })}
        </ul>
      )}
    </section>
  );
}
