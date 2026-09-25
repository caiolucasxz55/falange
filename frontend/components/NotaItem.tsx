"use client";

import { type FormEvent, useState } from "react";

import { apagarNota, editarNota, mensagemDoErro, resolverNota } from "@/lib/api";
import { diasDesde, type Nota } from "@/types/task";

interface NotaItemProps {
  nota: Nota;
  onAtualizada: (nota: Nota) => void;
  onApagada: (notaId: number) => void;
}

/** Uma nota da lista, com as acoes sobre ela. Erro fica dentro do item. */
export function NotaItem({ nota, onAtualizada, onApagada }: NotaItemProps) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [texto, setTexto] = useState(nota.texto);
  const [autor, setAutor] = useState(nota.autor ?? "");
  const [taskId, setTaskId] = useState(nota.task_id === null ? "" : String(nota.task_id));

  async function executar(acao: () => Promise<void>) {
    setOcupado(true);
    setErro(null);
    try {
      await acao();
    } catch (e: unknown) {
      setErro(mensagemDoErro(e));
    } finally {
      setOcupado(false);
    }
  }

  function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const alvo = taskId.trim();
    if (alvo && !/^\d+$/.test(alvo)) {
      setErro("task deve ser um numero, ex.: 7");
      return;
    }
    void executar(async () => {
      onAtualizada(
        await editarNota(nota.id, {
          texto: texto.trim(),
          autor: autor.trim() || null,
          task_id: alvo ? Number(alvo) : null,
        }),
      );
      setEditando(false);
    });
  }

  const alternarResolvida = () =>
    executar(async () => {
      // Resolver tem rota propria; reabrir passa pela edicao.
      onAtualizada(
        nota.resolvida
          ? await editarNota(nota.id, { resolvida: false })
          : await resolverNota(nota.id),
      );
    });

  const apagar = () =>
    executar(async () => {
      await apagarNota(nota.id);
      onApagada(nota.id);
    });

  const botao =
    "rounded border border-gray-300 px-2 py-0.5 text-gray-700 hover:bg-gray-50 disabled:opacity-50";
  const campo =
    "w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-900 focus:border-gray-500 focus:outline-none";

  return (
    <li className={`rounded border p-2 ${nota.resolvida ? "border-gray-200 bg-gray-50" : "border-gray-200"}`}>
      {editando ? (
        <form onSubmit={salvar} className="space-y-2">
          <textarea
            required
            rows={3}
            minLength={5}
            maxLength={2000}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className={campo}
            aria-label="Texto da nota em edicao"
          />
          <input
            maxLength={80}
            placeholder="autor (vazio remove)"
            value={autor}
            onChange={(e) => setAutor(e.target.value)}
            className={campo}
            aria-label="Autor da nota em edicao"
          />
          <input
            inputMode="numeric"
            placeholder="task # (vazio desliga)"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            className={campo}
            aria-label="Task ligada em edicao"
          />
          <div className="flex gap-2 text-xs">
            <button
              type="submit"
              disabled={ocupado}
              className="rounded bg-gray-900 px-2 py-0.5 font-medium text-white hover:bg-gray-700 disabled:opacity-50"
            >
              {ocupado ? "Salvando..." : "Salvar"}
            </button>
            <button
              type="button"
              className={botao}
              disabled={ocupado}
              onClick={() => setEditando(false)}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <>
          <p
            className={`whitespace-pre-line text-xs ${nota.resolvida ? "text-gray-400" : "text-gray-700"}`}
          >
            {nota.texto}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-400">
            {nota.autor && <span>{nota.autor}</span>}
            {nota.task_id !== null && <span>task #{nota.task_id}</span>}
            <span>ha {diasDesde(nota.criada_em)}d</span>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5 text-xs">
            <button
              type="button"
              className={botao}
              disabled={ocupado}
              onClick={alternarResolvida}
            >
              {nota.resolvida ? "Reabrir" : "Resolver"}
            </button>
            <button
              type="button"
              className={botao}
              disabled={ocupado}
              onClick={() => setEditando(true)}
            >
              Editar
            </button>
            <button
              type="button"
              className={botao}
              disabled={ocupado}
              onClick={() => setConfirmando(true)}
            >
              Apagar
            </button>
          </div>
        </>
      )}

      {confirmando && (
        <div className="mt-2 flex items-center gap-2 rounded bg-red-50 p-2 text-xs text-red-800">
          <span>Apagar de vez?</span>
          <button
            type="button"
            className="rounded bg-red-600 px-2 py-0.5 font-medium text-white hover:bg-red-700 disabled:opacity-50"
            disabled={ocupado}
            onClick={apagar}
          >
            {ocupado ? "Apagando..." : "Sim"}
          </button>
          <button
            type="button"
            className={botao}
            disabled={ocupado}
            onClick={() => setConfirmando(false)}
          >
            Cancelar
          </button>
        </div>
      )}

      {erro && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {erro}
        </p>
      )}
    </li>
  );
}
