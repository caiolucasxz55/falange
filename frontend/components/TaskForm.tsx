"use client";

import { type FormEvent, useState } from "react";

import { criarTask, mensagemDoErro } from "@/lib/api";
import {
  BLOCOS,
  type Bloco,
  ESTIMATIVAS,
  type Estimativa,
  isBloco,
  isEstimativa,
  type Task,
} from "@/types/task";

interface Campos {
  titulo: string;
  descricao: string;
  estimativa: Estimativa;
  bloco: Bloco;
  responsavel: string;
}

const CAMPOS_INICIAIS: Campos = {
  titulo: "",
  descricao: "",
  estimativa: "P",
  bloco: "backend",
  responsavel: "",
};

interface TaskFormProps {
  onCriada: (task: Task) => void;
}

/** Formulario de criacao (POST /tasks). */
export function TaskForm({ onCriada }: TaskFormProps) {
  const [campos, setCampos] = useState<Campos>(CAMPOS_INICIAIS);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [criadaId, setCriadaId] = useState<number | null>(null);

  function atualizar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    setCriadaId(null);

    try {
      const task = await criarTask({
        titulo: campos.titulo.trim(),
        descricao: campos.descricao.trim(),
        estimativa: campos.estimativa,
        bloco: campos.bloco,
        responsavel: campos.responsavel.trim() || null,
      });
      setCampos(CAMPOS_INICIAIS);
      setCriadaId(task.id);
      onCriada(task);
    } catch (e: unknown) {
      setErro(mensagemDoErro(e));
    } finally {
      setEnviando(false);
    }
  }

  const estiloCampo =
    "w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-gray-500 focus:outline-none";

  return (
    <form onSubmit={enviar} className="space-y-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">Nova task</h2>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Titulo</span>
        <input
          required
          maxLength={120}
          value={campos.titulo}
          onChange={(e) => atualizar("titulo", e.target.value)}
          className={estiloCampo}
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Descricao</span>
        <textarea
          rows={4}
          value={campos.descricao}
          onChange={(e) => atualizar("descricao", e.target.value)}
          className={estiloCampo}
        />
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-gray-700">Estimativa</span>
          <select
            value={campos.estimativa}
            onChange={(e) => {
              const valor = e.target.value;
              if (isEstimativa(valor)) atualizar("estimativa", valor);
            }}
            className={estiloCampo}
          >
            {ESTIMATIVAS.map((estimativa) => (
              <option key={estimativa} value={estimativa}>
                {estimativa}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-gray-700">Bloco</span>
          <select
            value={campos.bloco}
            onChange={(e) => {
              const valor = e.target.value;
              if (isBloco(valor)) atualizar("bloco", valor);
            }}
            className={estiloCampo}
          >
            {BLOCOS.map((bloco) => (
              <option key={bloco} value={bloco}>
                {bloco}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">
          Responsavel <span className="font-normal text-gray-400">(opcional)</span>
        </span>
        <input
          maxLength={80}
          value={campos.responsavel}
          onChange={(e) => atualizar("responsavel", e.target.value)}
          className={estiloCampo}
        />
      </label>

      {erro && (
        <p className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{erro}</p>
      )}
      {criadaId !== null && (
        <p className="rounded border border-green-200 bg-green-50 p-2 text-sm text-green-700">
          Task #{criadaId} criada.
        </p>
      )}

      <button
        type="submit"
        disabled={enviando}
        className="w-full rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
      >
        {enviando ? "Criando..." : "Criar task"}
      </button>
    </form>
  );
}
