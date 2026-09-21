import type { Status, Task } from "@/types/task";

const ROTULO_STATUS: Record<Status, string> = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  concluida: "Concluida",
};

interface TaskCardProps {
  task: Task;
}

/** Exibe uma task. So apresentacao: nao busca nem altera nada. */
export function TaskCard({ task }: TaskCardProps) {
  const bloqueada = task.bloqueada_por !== null;

  return (
    <article
      className={`rounded border bg-white p-4 ${bloqueada ? "border-red-300" : "border-gray-200"}`}
    >
      <header className="flex items-start justify-between gap-3">
        <h3 className="font-medium text-gray-900">
          <span className="mr-1 text-gray-400">#{task.id}</span>
          {task.titulo}
        </h3>
        {bloqueada && (
          <span className="shrink-0 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            Bloqueada por #{task.bloqueada_por}
          </span>
        )}
      </header>

      {task.descricao && (
        <p className="mt-2 whitespace-pre-line text-sm text-gray-600">{task.descricao}</p>
      )}

      <footer className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">
          Estimativa: {task.estimativa}
        </span>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">Bloco: {task.bloco}</span>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">
          {ROTULO_STATUS[task.status]}
        </span>
        {task.responsavel && (
          <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">
            {task.responsavel}
          </span>
        )}
      </footer>
    </article>
  );
}
