"use client";

import { useEffect, useState } from "react";

import { TaskCard } from "@/components/TaskCard";
import { listarTasks, mensagemDoErro } from "@/lib/api";
import { type FiltrosTask, STATUS, type Status, type Task } from "@/types/task";

const ROTULO_COLUNA: Record<Status, string> = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  concluida: "Concluida",
};

const INTERVALO_POLLING = 15_000;

// O resultado guarda a chave dos filtros que o produziu. "Carregando" e
// derivado disso, em vez de um setState sincrono no efeito (que a regra
// react-hooks/set-state-in-effect proibe). Como o polling nao muda a chave,
// ele atualiza a lista sem piscar.
type Resultado =
  | { chave: string; tipo: "ok"; tasks: Task[] }
  | { chave: string; tipo: "erro"; mensagem: string };

interface BoardProps {
  filtros: FiltrosTask;
  /** Muda para forcar nova busca (task criada, botao recarregar, polling). */
  versao: number;
  onRecarregar: () => void;
}

/** Board de 3 colunas por status. Busca no backend e executa as acoes. */
export function Board({ filtros, versao, onRecarregar }: BoardProps) {
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const chave = JSON.stringify(filtros);

  useEffect(() => {
    let ativo = true; // descarta resposta de uma busca ja substituida
    listarTasks(filtros)
      .then((tasks) => {
        if (ativo) setResultado({ chave, tipo: "ok", tasks });
      })
      .catch((erro: unknown) => {
        if (ativo) setResultado({ chave, tipo: "erro", mensagem: mensagemDoErro(erro) });
      });
    return () => {
      ativo = false;
    };
  }, [chave, filtros, versao]);

  useEffect(() => {
    const id = setInterval(() => {
      // Aba escondida nao gasta requisicao.
      if (document.visibilityState === "visible") onRecarregar();
    }, INTERVALO_POLLING);
    return () => clearInterval(id);
  }, [onRecarregar]);

  const carregando = resultado === null || resultado.chave !== chave;
  const tasks = resultado?.tipo === "ok" ? resultado.tasks : [];

  // Quantas tasks cada uma esta travando, dentro do que foi carregado.
  const travando = new Map<number, number>();
  for (const task of tasks) {
    if (task.bloqueada_por !== null) {
      travando.set(task.bloqueada_por, (travando.get(task.bloqueada_por) ?? 0) + 1);
    }
  }

  function substituir(atualizada: Task) {
    setResultado((atual) =>
      atual?.tipo === "ok"
        ? {
            ...atual,
            tasks: atual.tasks.map((t) => (t.id === atualizada.id ? atualizada : t)),
          }
        : atual,
    );
  }

  function remover(taskId: number) {
    setResultado((atual) =>
      atual?.tipo === "ok"
        ? { ...atual, tasks: atual.tasks.filter((t) => t.id !== taskId) }
        : atual,
    );
  }

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
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50"
        >
          Recarregar
        </button>
      </div>

      {resultado?.tipo === "erro" && (
        <p className="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Nao foi possivel carregar as tasks: {resultado.mensagem}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {STATUS.map((status) => {
          // O backend ja devolve por prioridade; filtrar preserva a ordem.
          const daColuna = tasks.filter((t) => t.status === status);
          return (
            <div key={status} className="rounded bg-gray-100/70 p-2">
              <h3 className="mb-2 px-1 text-sm font-medium text-gray-700">
                {ROTULO_COLUNA[status]}
                <span className="ml-1 text-gray-400">({daColuna.length})</span>
              </h3>
              <div className="space-y-2">
                {daColuna.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    travando={travando.get(task.id) ?? 0}
                    onAtualizada={substituir}
                    onApagada={remover}
                  />
                ))}
                {daColuna.length === 0 && (
                  <p className="px-1 py-4 text-center text-xs text-gray-400">
                    {carregando ? "Carregando..." : "Nenhuma task"}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
