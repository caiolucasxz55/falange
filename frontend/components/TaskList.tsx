"use client";

import { useEffect, useState } from "react";

import { TaskCard } from "@/components/TaskCard";
import { listarTasks, mensagemDoErro } from "@/lib/api";
import type { Task } from "@/types/task";

// Cada resultado guarda a versao que o produziu. "Carregando" e derivado
// (resultado.versao !== versao) em vez de um setState sincrono no efeito,
// que a regra react-hooks/set-state-in-effect proibe.
type Resultado =
  | { versao: number; tipo: "ok"; tasks: Task[] }
  | { versao: number; tipo: "erro"; mensagem: string };

interface TaskListProps {
  /** Muda para forcar nova busca (ex.: depois de criar uma task). */
  versao: number;
  onRecarregar: () => void;
}

/** Busca (GET /tasks) e renderiza a lista. */
export function TaskList({ versao, onRecarregar }: TaskListProps) {
  const [resultado, setResultado] = useState<Resultado | null>(null);

  useEffect(() => {
    let ativo = true; // descarta resposta de uma busca que ja foi substituida
    listarTasks()
      .then((tasks) => {
        if (ativo) setResultado({ versao, tipo: "ok", tasks });
      })
      .catch((erro: unknown) => {
        if (ativo) setResultado({ versao, tipo: "erro", mensagem: mensagemDoErro(erro) });
      });
    return () => {
      ativo = false;
    };
  }, [versao]);

  const carregando = resultado === null || resultado.versao !== versao;

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Tasks
          {resultado?.tipo === "ok" && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({resultado.tasks.length})
            </span>
          )}
        </h2>
        <button
          type="button"
          onClick={onRecarregar}
          disabled={carregando}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          {carregando ? "Carregando..." : "Recarregar"}
        </button>
      </div>

      {resultado?.tipo === "erro" && (
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Nao foi possivel carregar as tasks: {resultado.mensagem}
        </p>
      )}

      {resultado?.tipo === "ok" && resultado.tasks.length === 0 && (
        <p className="rounded border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
          Nenhuma task ainda. Crie pelo formulario ou via MCP.
        </p>
      )}

      {resultado?.tipo === "ok" && resultado.tasks.length > 0 && (
        <ul className="space-y-3">
          {resultado.tasks.map((task) => (
            <li key={task.id}>
              <TaskCard task={task} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
