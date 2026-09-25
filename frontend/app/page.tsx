"use client";

import { useCallback, useState } from "react";

import { Board } from "@/components/Board";
import { Filtros } from "@/components/Filtros";
import { PainelNotas } from "@/components/PainelNotas";
import { TaskForm } from "@/components/TaskForm";
import { API_URL } from "@/lib/api";
import type { FiltrosTask } from "@/types/task";

export default function Home() {
  const [filtros, setFiltros] = useState<FiltrosTask>({});
  // Incrementar a versao faz o Board buscar de novo.
  const [versao, setVersao] = useState(0);
  // useCallback: o Board usa isto na dependencia do polling, e uma funcao
  // nova a cada render reiniciaria o intervalo sem parar.
  const recarregar = useCallback(() => setVersao((v) => v + 1), []);

  return (
    <main className="mx-auto w-full max-w-[90rem] px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Falange</h1>
        <p className="mt-1 text-sm text-gray-500">
          Backend: <code className="rounded bg-gray-100 px-1">{API_URL}</code>. A lista
          atualiza sozinha a cada 15s enquanto a aba estiver visivel.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-[20rem_1fr]">
        <aside>
          <TaskForm onCriada={recarregar} />
          <PainelNotas />
        </aside>
        <div>
          <Filtros filtros={filtros} onMudar={setFiltros} />
          <Board filtros={filtros} versao={versao} onRecarregar={recarregar} />
        </div>
      </div>
    </main>
  );
}
