"use client";

import { type FormEvent, useState } from "react";

import {
  BLOCOS,
  type Bloco,
  type EdicaoTask,
  ESTIMATIVAS,
  type Estimativa,
  isBloco,
  isEstimativa,
  isPrioridade,
  PRIORIDADES,
  type Prioridade,
  type Task,
} from "@/types/task";

interface Campos {
  titulo: string;
  descricao: string;
  estimativa: Estimativa;
  bloco: Bloco;
  prioridade: Prioridade;
  responsavel: string;
}

interface TaskCardEdicaoProps {
  task: Task;
  salvando: boolean;
  onSalvar: (campos: EdicaoTask) => void;
  onCancelar: () => void;
}

/** Formulario inline do card. Nao chama a API: devolve os campos ao card. */
export function TaskCardEdicao({
  task,
  salvando,
  onSalvar,
  onCancelar,
}: TaskCardEdicaoProps) {
  const [campos, setCampos] = useState<Campos>({
    titulo: task.titulo,
    descricao: task.descricao,
    estimativa: task.estimativa,
    bloco: task.bloco,
    prioridade: task.prioridade,
    responsavel: task.responsavel ?? "",
  });

  function atualizar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    onSalvar({
      titulo: campos.titulo.trim(),
      descricao: campos.descricao.trim(),
      estimativa: campos.estimativa,
      bloco: campos.bloco,
      prioridade: campos.prioridade,
      // "" chega na api como null e desatribui.
      responsavel: campos.responsavel.trim(),
    });
  }

  const estilo =
    "w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-gray-500 focus:outline-none";

  return (
    <form onSubmit={enviar} className="space-y-2">
      <input
        required
        maxLength={120}
        value={campos.titulo}
        onChange={(e) => atualizar("titulo", e.target.value)}
        className={estilo}
        aria-label="Titulo"
      />
      <textarea
        rows={3}
        value={campos.descricao}
        onChange={(e) => atualizar("descricao", e.target.value)}
        className={estilo}
        aria-label="Descricao"
      />
      <div className="grid grid-cols-3 gap-2">
        <select
          value={campos.estimativa}
          onChange={(e) => {
            const valor = e.target.value;
            if (isEstimativa(valor)) atualizar("estimativa", valor);
          }}
          className={estilo}
          aria-label="Estimativa"
        >
          {ESTIMATIVAS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select
          value={campos.bloco}
          onChange={(e) => {
            const valor = e.target.value;
            if (isBloco(valor)) atualizar("bloco", valor);
          }}
          className={estilo}
          aria-label="Bloco"
        >
          {BLOCOS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select
          value={campos.prioridade}
          onChange={(e) => {
            const valor = e.target.value;
            if (isPrioridade(valor)) atualizar("prioridade", valor);
          }}
          className={estilo}
          aria-label="Prioridade"
        >
          {PRIORIDADES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>
      <input
        maxLength={80}
        placeholder="responsavel (vazio remove)"
        value={campos.responsavel}
        onChange={(e) => atualizar("responsavel", e.target.value)}
        className={estilo}
        aria-label="Responsavel"
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={salvando}
          className="rounded bg-gray-900 px-3 py-1 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {salvando ? "Salvando..." : "Salvar"}
        </button>
        <button
          type="button"
          onClick={onCancelar}
          disabled={salvando}
          className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
