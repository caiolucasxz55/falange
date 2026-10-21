"use client";

import { useState } from "react";

import { useSessao } from "@/components/SessaoProvider";
import { TaskCardEdicao } from "@/components/TaskCardEdicao";
import {
  adicionarDependencia,
  apagarTask,
  editarTask,
  mensagemDoErro,
  mudarStatus,
  removerDependencia,
} from "@/lib/api";
import {
  diasDesde,
  type EdicaoTask,
  type Nota,
  type Prioridade,
  STATUS,
  type Status,
  type Task,
} from "@/types/task";

const ROTULO_STATUS: Record<Status, string> = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  concluida: "Concluida",
};

// Cor por prioridade: alta chama atencao, baixa recua.
const ESTILO_PRIORIDADE: Record<Prioridade, string> = {
  alta: "bg-red-100 text-red-700",
  media: "bg-gray-100 text-gray-700",
  baixa: "bg-gray-100 text-gray-500",
};

interface TaskCardProps {
  task: Task;
  /** Quantas tasks carregadas esta aqui esta travando. */
  travando: number;
  /** Notas abertas ligadas a esta task. */
  notas: Nota[];
  onAtualizada: (task: Task) => void;
  onApagada: (taskId: number) => void;
}

/** Card do board: exibe a task e executa as acoes sobre ela. */
export function TaskCard({
  task,
  travando,
  notas,
  onAtualizada,
  onApagada,
}: TaskCardProps) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);

  // Esconder nao e autorizar: a API recusa de todo jeito. Isto so evita
  // oferecer botao que ja se sabe que vai dar 403.
  const { pode, eu } = useSessao();
  const podeStatus = pode("mudar_status_task");
  const podeEditar = pode("editar_task");
  const podeBloqueio = pode("marcar_bloqueio");
  // Quem apaga so o proprio precisa ser o autor da task.
  const podeApagar =
    pode("apagar_task") ||
    (pode("apagar_task_propria") &&
      task.autor_id !== null &&
      task.autor_id === eu?.usuario?.id);
  const [bloqueando, setBloqueando] = useState(false);
  const [idBloqueadora, setIdBloqueadora] = useState("");
  const [verNotas, setVerNotas] = useState(false);

  const bloqueada = task.bloqueada;
  const posicao = STATUS.indexOf(task.status);

  /** Roda uma acao da API mantendo o erro dentro deste card. */
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

  const moverPara = (destino: Status) =>
    executar(async () => onAtualizada(await mudarStatus(task.id, destino)));

  const salvarEdicao = (campos: EdicaoTask) =>
    executar(async () => {
      onAtualizada(await editarTask(task.id, campos));
      setEditando(false);
    });

  const aplicarBloqueio = () =>
    executar(async () => {
      const alvo = Number(idBloqueadora);
      if (!Number.isInteger(alvo) || alvo <= 0) {
        setErro("informe o numero de uma task, ex.: 7");
        return;
      }
      onAtualizada(await adicionarDependencia(task.id, alvo));
      setBloqueando(false);
      setIdBloqueadora("");
    });

  // Uma por vez: com N:N, "desbloquear" sem dizer qual seria ambiguo.
  const soltarDe = (outra: number) =>
    executar(async () =>
      onAtualizada(await removerDependencia(task.id, outra)),
    );

  const apagar = () =>
    executar(async () => {
      await apagarTask(task.id);
      onApagada(task.id);
    });

  const botao =
    "rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50";

  return (
    <article
      className={`rounded border bg-white p-3 ${bloqueada ? "border-red-300" : "border-gray-200"}`}
    >
      {editando ? (
        <TaskCardEdicao
          task={task}
          salvando={ocupado}
          onSalvar={salvarEdicao}
          onCancelar={() => setEditando(false)}
        />
      ) : (
        <>
          <h3 className="text-sm font-medium text-gray-900">
            <span className="mr-1 text-gray-400">#{task.id}</span>
            {task.titulo}
          </h3>

          {task.descricao && (
            <p className="mt-2 line-clamp-3 whitespace-pre-line text-xs text-gray-600">
              {task.descricao}
            </p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
            {bloqueada && (
              <span className="rounded bg-red-100 px-2 py-0.5 font-medium text-red-700">
                Bloqueada
              </span>
            )}
            <span
              className={`rounded px-2 py-0.5 font-medium ${ESTILO_PRIORIDADE[task.prioridade]}`}
            >
              {task.prioridade}
            </span>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">
              {task.estimativa}
            </span>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">
              {task.bloco}
            </span>
            {task.responsavel && (
              <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">
                {task.responsavel}
              </span>
            )}
            {travando > 0 && (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">
                travando {travando}
              </span>
            )}
            {notas.length > 0 && (
              <button
                type="button"
                onClick={() => setVerNotas((v) => !v)}
                className="rounded bg-sky-100 px-2 py-0.5 text-sky-800 hover:bg-sky-200"
              >
                {notas.length} nota{notas.length > 1 ? "s" : ""}
              </button>
            )}
            <span className="text-gray-400">ha {diasDesde(task.criada_em)}d</span>
          </div>

          {task.criterios.length > 0 && (
            <ul className="mt-2 space-y-1">
              {task.criterios.map((criterio) => {
                const cumprido = criterio.cumprido_em !== null;
                return (
                  <li
                    key={criterio.id}
                    className="flex items-start gap-1.5 text-xs text-gray-600"
                  >
                    {/*
                      Quadradinho, nao <input type="checkbox">: nao e campo.
                      Quem marca criterio e a evidencia, no backend -- um
                      checkbox convidaria a clicar e nada aconteceria.
                    */}
                    <span
                      aria-hidden
                      className={`mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border text-[9px] leading-none ${
                        cumprido
                          ? "border-green-600 bg-green-600 text-white"
                          : "border-gray-300"
                      }`}
                    >
                      {cumprido ? "✓" : ""}
                    </span>
                    <span className={cumprido ? "text-gray-400 line-through" : ""}>
                      {criterio.texto}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}

          {task.depende_de.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-gray-500">depende de</span>
              {task.depende_de.map((outra) => (
                <span
                  key={outra}
                  className="flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-gray-700"
                >
                  #{outra}
                  {podeBloqueio && (
                    <button
                      type="button"
                      disabled={ocupado}
                      onClick={() => soltarDe(outra)}
                      className="text-gray-400 hover:text-red-600 disabled:opacity-50"
                      aria-label={`Soltar #${task.id} de #${outra}`}
                      title="soltar"
                    >
                      &times;
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}

          {verNotas && notas.length > 0 && (
            <ul className="mt-2 space-y-1 rounded bg-sky-50 p-2">
              {notas.map((nota) => (
                <li key={nota.id} className="text-xs text-sky-900">
                  {nota.texto}
                  {nota.autor && <span className="text-sky-700"> - {nota.autor}</span>}
                </li>
              ))}
            </ul>
          )}

          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-gray-100 pt-2">
            {podeStatus && posicao > 0 && (
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={() => moverPara(STATUS[posicao - 1])}
              >
                &larr; {ROTULO_STATUS[STATUS[posicao - 1]]}
              </button>
            )}
            {podeStatus && posicao < STATUS.length - 1 && (
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={() => moverPara(STATUS[posicao + 1])}
              >
                {ROTULO_STATUS[STATUS[posicao + 1]]} &rarr;
              </button>
            )}
            {podeEditar && (
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={() => setEditando(true)}
              >
                Editar
              </button>
            )}
            {podeBloqueio && (
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={() => setBloqueando((v) => !v)}
              >
                Depende de...
              </button>
            )}
            {podeApagar && (
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={() => setConfirmandoExclusao(true)}
              >
                Apagar
              </button>
            )}
          </div>

          {bloqueando && (
            <div className="mt-2 flex items-center gap-2">
              <input
                inputMode="numeric"
                placeholder="esperar por #"
                value={idBloqueadora}
                onChange={(e) => setIdBloqueadora(e.target.value)}
                className="w-32 rounded border border-gray-300 px-2 py-1 text-xs"
                aria-label="Id da task de quem esta depende"
              />
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={aplicarBloqueio}
              >
                Confirmar
              </button>
            </div>
          )}

          {confirmandoExclusao && (
            <div className="mt-2 flex items-center gap-2 rounded bg-red-50 p-2 text-xs text-red-800">
              <span>Apagar #{task.id}?</span>
              <button
                type="button"
                className="rounded bg-red-600 px-2 py-0.5 font-medium text-white hover:bg-red-700 disabled:opacity-50"
                disabled={ocupado}
                onClick={apagar}
              >
                {ocupado ? "Apagando..." : "Sim, apagar"}
              </button>
              <button
                type="button"
                className={botao}
                disabled={ocupado}
                onClick={() => setConfirmandoExclusao(false)}
              >
                Cancelar
              </button>
            </div>
          )}
        </>
      )}

      {erro && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {erro}
        </p>
      )}
    </article>
  );
}
