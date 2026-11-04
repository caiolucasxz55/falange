"use client";

import { useEffect, useState } from "react";

import { mensagemDoErro, verEvolucao } from "@/lib/api";
import type { Evolucao, PrevisaoMarco, VereditoMarco } from "@/types/task";

const ESTILO_VEREDITO: Record<VereditoMarco, string> = {
  no_prazo: "bg-green-100 text-green-800",
  em_risco: "bg-amber-100 text-amber-900",
  atrasado: "bg-red-100 text-red-700",
  sem_data: "bg-gray-100 text-gray-600",
  concluido: "bg-gray-100 text-gray-500",
};

const ROTULO_VEREDITO: Record<VereditoMarco, string> = {
  no_prazo: "no prazo",
  em_risco: "em risco",
  atrasado: "atrasado",
  sem_data: "sem data",
  concluido: "concluido",
};

/** "02/11" a partir de "2026-11-02", sem passar por fuso.
 *
 * `new Date("2026-11-02")` e interpretado como UTC e, a oeste de
 * Greenwich, volta como dia 1. A data aqui e um rotulo de calendario, nao
 * um instante: cortar a string e o certo.
 */
function diaMes(iso: string): string {
  const [, mes, dia] = iso.split("-");
  return `${dia}/${mes}`;
}

/**
 * Barras sem biblioteca: uma coluna por semana, com altura em porcentagem.
 *
 * Um grafico de 8 barras nao justifica 100kb de dependencia, e manter uma
 * a menos no `package.json` e manter uma a menos para atualizar.
 *
 * Feito com divs, e nao com SVG: a primeira versao desenhava tudo num
 * `<svg preserveAspectRatio="none">`, e o texto dentro dele era esticado
 * junto com as barras -- os rotulos das semanas sairam gigantes e
 * deformados. Texto nao sobrevive a escala nao-uniforme. Com divs, a
 * barra estica e a fonte nao.
 */
function Barras({ semanas, valores }: { semanas: string[]; valores: number[] }) {
  const maximo = Math.max(1, ...valores);

  return (
    <div
      className="flex items-end gap-1"
      role="img"
      aria-label={`Tasks concluidas por semana: ${valores.join(", ")}`}
    >
      {valores.map((valor, i) => (
        <div key={semanas[i]} className="flex flex-1 flex-col items-center gap-1">
          <span className="text-[10px] leading-none text-gray-600">
            {valor > 0 ? valor : ""}
          </span>
          <div className="flex h-20 w-full items-end">
            <div
              className="w-full rounded-sm bg-gray-800"
              // Minimo de 2px no valor zero: a coluna vazia precisa de uma
              // marca, ou a semana some do grafico e parece nao ter
              // existido.
              style={{
                height: valor > 0 ? `${(valor / maximo) * 100}%` : "2px",
                opacity: valor > 0 ? 1 : 0.15,
              }}
            />
          </div>
          <span className="text-[10px] leading-none text-gray-400">
            {diaMes(semanas[i])}
          </span>
        </div>
      ))}
    </div>
  );
}

function Marco({ marco }: { marco: PrevisaoMarco }) {
  const feito = marco.tasks_total
    ? Math.round((marco.tasks_concluidas / marco.tasks_total) * 100)
    : 0;

  return (
    <li className="rounded border border-gray-200 p-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-gray-800">{marco.nome}</span>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${ESTILO_VEREDITO[marco.veredito]}`}
        >
          {ROTULO_VEREDITO[marco.veredito]}
        </span>
        {marco.data_alvo && (
          <span className="text-xs text-gray-500">{diaMes(marco.data_alvo)}</span>
        )}
        <span className="ml-auto text-xs text-gray-500">
          {marco.tasks_concluidas}/{marco.tasks_total}
        </span>
      </div>

      <div className="mt-1.5 h-1 w-full rounded bg-gray-100">
        <div
          className="h-1 rounded bg-gray-700"
          style={{ width: `${feito}%` }}
        />
      </div>

      {/*
        A CONTA, nao so a cor. "Em risco" sem numero e palpite, e palpite
        de software sobre prazo nao convence ninguem -- com razao. Com a
        conta a vista, quem discorda tem onde apontar.
      */}
      <p className="mt-1.5 text-xs text-gray-500">{marco.motivo}</p>
    </li>
  );
}

/** Aba Evolucao: como o time esta andando, a partir dos eventos. */
export function PainelEvolucao() {
  const [dados, setDados] = useState<Evolucao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    verEvolucao(8)
      .then((e) => ativo && setDados(e))
      .catch((e: unknown) => ativo && setErro(mensagemDoErro(e)));
    return () => {
      ativo = false;
    };
  }, []);

  if (erro) {
    return (
      <section className="mt-4 rounded border border-gray-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-gray-900">Evolucao</h2>
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          Nao foi possivel carregar: {erro}
        </p>
      </section>
    );
  }

  if (!dados) return null;

  const { throughput, tempo_de_ciclo: ciclo, marcos } = dados;
  const total = throughput.concluidas.reduce((a, b) => a + b, 0);

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">Evolucao</h2>

      {/*
        O aviso vem ANTES dos numeros, de proposito: um grafico quase
        vazio diz "o time parou" sozinho, e o que houve foi o registro ter
        comecado agora. Deixar o leitor concluir a primeira coisa seria o
        painel mentindo por omissao.
      */}
      {dados.aviso && (
        <p className="mt-2 rounded border border-sky-200 bg-sky-50 p-2 text-xs text-sky-900">
          {dados.aviso}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs text-gray-600">
        <span>
          <strong className="text-gray-900">{total}</strong> concluidas em 8
          semanas
        </span>
        <span>
          ciclo mediano:{" "}
          {ciclo.mediana_dias === null ? (
            // Nulo e nao zero: zero diria "o time entrega
            // instantaneamente"; nulo diz "ainda nao da para saber".
            <span className="text-gray-400">ainda nao da para saber</span>
          ) : (
            <>
              <strong className="text-gray-900">{ciclo.mediana_dias}d</strong>{" "}
              <span className="text-gray-400">
                (n={ciclo.n}
                {ciclo.n < 5 && ", amostra pequena"})
              </span>
            </>
          )}
        </span>
      </div>

      {/*
        Os ciclos que nao couberam na janela. Fica fora do parenteses do
        `n` de proposito: nao e "amostra pequena", e amostra ENVIESADA --
        so o ciclo longo cai de fora, entao a mediana esta puxada para
        baixo, e quem le precisa saber a direcao do erro.
      */}
      {ciclo.sem_inicio_na_janela > 0 && (
        <p className="mt-1 text-xs text-amber-800">
          {ciclo.sem_inicio_na_janela} conclusao(oes) comecaram antes da
          janela e ficaram de fora do ciclo; a mediana esta puxada para
          baixo.
        </p>
      )}

      <div className="mt-2">
        <Barras semanas={throughput.semanas} valores={throughput.concluidas} />
      </div>

      {Object.keys(throughput.por_bloco).length > 0 && (
        <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
          {Object.entries(throughput.por_bloco).map(([bloco, valores]) => (
            <li key={bloco}>
              {bloco}: <span className="text-gray-700">{valores.reduce((a, b) => a + b, 0)}</span>
            </li>
          ))}
        </ul>
      )}

      {marcos.length > 0 && (
        <>
          <h3 className="mt-4 text-sm font-medium text-gray-800">Marcos</h3>
          <ul className="mt-2 space-y-2">
            {marcos.map((marco) => (
              <Marco key={marco.id} marco={marco} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
