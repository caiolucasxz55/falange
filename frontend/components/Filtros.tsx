"use client";

import {
  BLOCOS,
  type FiltrosTask,
  isBloco,
  isPrioridade,
  PRIORIDADES,
} from "@/types/task";

interface FiltrosProps {
  filtros: FiltrosTask;
  onMudar: (filtros: FiltrosTask) => void;
}

/** Barra de filtros. Quem filtra e o backend: isto so monta o pedido. */
export function Filtros({ filtros, onMudar }: FiltrosProps) {
  const estilo =
    "rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-gray-500 focus:outline-none";

  const algumAtivo = Boolean(filtros.bloco || filtros.prioridade || filtros.responsavel);

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <select
        value={filtros.bloco ?? ""}
        onChange={(e) => {
          const valor = e.target.value;
          onMudar({ ...filtros, bloco: isBloco(valor) ? valor : "" });
        }}
        className={estilo}
        aria-label="Filtrar por bloco"
      >
        <option value="">todos os blocos</option>
        {BLOCOS.map((bloco) => (
          <option key={bloco} value={bloco}>
            {bloco}
          </option>
        ))}
      </select>

      <select
        value={filtros.prioridade ?? ""}
        onChange={(e) => {
          const valor = e.target.value;
          onMudar({ ...filtros, prioridade: isPrioridade(valor) ? valor : "" });
        }}
        className={estilo}
        aria-label="Filtrar por prioridade"
      >
        <option value="">todas as prioridades</option>
        {PRIORIDADES.map((prioridade) => (
          <option key={prioridade} value={prioridade}>
            {prioridade}
          </option>
        ))}
      </select>

      <input
        placeholder="responsavel"
        value={filtros.responsavel ?? ""}
        onChange={(e) => onMudar({ ...filtros, responsavel: e.target.value })}
        className={`${estilo} w-40`}
        aria-label="Filtrar por responsavel"
      />

      {algumAtivo && (
        <button
          type="button"
          onClick={() => onMudar({})}
          className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-700 hover:bg-gray-50"
        >
          Limpar
        </button>
      )}
    </div>
  );
}
