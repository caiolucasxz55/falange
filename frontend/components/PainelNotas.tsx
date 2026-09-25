"use client";

import { type FormEvent, useEffect, useState } from "react";

import { NotaItem } from "@/components/NotaItem";
import { listarNotas, mensagemDoErro, registrarNota } from "@/lib/api";
import type { Nota } from "@/types/task";

// Mesmo padrao do Board: o resultado guarda a chave que o produziu, para
// "carregando" ser derivado em vez de setState sincrono no efeito.
type Resultado =
  | { chave: string; tipo: "ok"; notas: Nota[] }
  | { chave: string; tipo: "erro"; mensagem: string };

interface PainelNotasProps {
  /** Avisa o board: nota nova pode mudar o contador do card da task. */
  onMudou: () => void;
}

/** Notas do time: registro, lista (abertas ou resolvidas) e acoes. */
export function PainelNotas({ onMudou }: PainelNotasProps) {
  const [mostrarResolvidas, setMostrarResolvidas] = useState(false);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [versao, setVersao] = useState(0);
  const [texto, setTexto] = useState("");
  const [autor, setAutor] = useState("");
  const [taskId, setTaskId] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const chave = `${mostrarResolvidas}#${versao}`;

  useEffect(() => {
    let ativo = true;
    listarNotas(mostrarResolvidas)
      .then((notas) => {
        if (ativo) setResultado({ chave, tipo: "ok", notas });
      })
      .catch((e: unknown) => {
        if (ativo) setResultado({ chave, tipo: "erro", mensagem: mensagemDoErro(e) });
      });
    return () => {
      ativo = false;
    };
  }, [chave, mostrarResolvidas]);

  function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const alvo = taskId.trim();
    if (alvo && !/^\d+$/.test(alvo)) {
      setErro("task deve ser um numero, ex.: 7");
      return;
    }

    setOcupado(true);
    setErro(null);
    void (async () => {
      try {
        await registrarNota({
          texto: texto.trim(),
          autor: autor.trim() || null,
          task_id: alvo ? Number(alvo) : null,
        });
        setTexto("");
        setTaskId("");
        setVersao((v) => v + 1);
        onMudou();
      } catch (e: unknown) {
        setErro(mensagemDoErro(e));
      } finally {
        setOcupado(false);
      }
    })();
  }

  function substituir(atualizada: Nota) {
    // Nota que saiu do filtro atual (resolvida/reaberta) some da lista.
    setResultado((atual) =>
      atual?.tipo === "ok"
        ? {
            ...atual,
            notas:
              atualizada.resolvida === mostrarResolvidas
                ? atual.notas.map((n) => (n.id === atualizada.id ? atualizada : n))
                : atual.notas.filter((n) => n.id !== atualizada.id),
          }
        : atual,
    );
    onMudou();
  }

  function remover(notaId: number) {
    setResultado((atual) =>
      atual?.tipo === "ok"
        ? { ...atual, notas: atual.notas.filter((n) => n.id !== notaId) }
        : atual,
    );
    onMudou();
  }

  const notas = resultado?.tipo === "ok" ? resultado.notas : [];
  const estilo =
    "w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-gray-500 focus:outline-none";
  const aba = (ativa: boolean) =>
    `rounded px-2 py-0.5 text-xs ${ativa ? "bg-gray-900 text-white" : "border border-gray-300 text-gray-700 hover:bg-gray-50"}`;

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Notas
          {resultado?.tipo === "ok" && (
            <span className="ml-2 text-sm font-normal text-gray-500">({notas.length})</span>
          )}
        </h2>
        <div className="flex gap-1">
          <button
            type="button"
            className={aba(!mostrarResolvidas)}
            onClick={() => setMostrarResolvidas(false)}
          >
            abertas
          </button>
          <button
            type="button"
            className={aba(mostrarResolvidas)}
            onClick={() => setMostrarResolvidas(true)}
          >
            resolvidas
          </button>
        </div>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Problema, decisao ou duvida que precisa de mais gente, sem virar task.
      </p>

      <form onSubmit={registrar} className="mt-3 space-y-2">
        <textarea
          required
          rows={3}
          minLength={5}
          maxLength={2000}
          placeholder="o que precisa ser discutido"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          className={estilo}
          aria-label="Texto da nota"
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            maxLength={80}
            placeholder="autor (opcional)"
            value={autor}
            onChange={(e) => setAutor(e.target.value)}
            className={estilo}
            aria-label="Autor da nota"
          />
          <input
            inputMode="numeric"
            placeholder="task # (opcional)"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            className={estilo}
            aria-label="Task ligada a nota"
          />
        </div>
        <button
          type="submit"
          disabled={ocupado}
          className="w-full rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {ocupado ? "Registrando..." : "Registrar nota"}
        </button>
      </form>

      {erro && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {erro}
        </p>
      )}
      {resultado?.tipo === "erro" && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          Nao foi possivel carregar as notas: {resultado.mensagem}
        </p>
      )}

      <ul className="mt-3 space-y-2">
        {notas.map((nota) => (
          <NotaItem
            key={nota.id}
            nota={nota}
            onAtualizada={substituir}
            onApagada={remover}
          />
        ))}
      </ul>

      {resultado?.tipo === "ok" && notas.length === 0 && (
        <p className="mt-3 text-center text-xs text-gray-400">
          {mostrarResolvidas ? "Nenhuma nota resolvida." : "Nenhuma nota aberta."}
        </p>
      )}
    </section>
  );
}
