"use client";

import { useState } from "react";

import { TaskForm } from "@/components/TaskForm";
import { TaskList } from "@/components/TaskList";
import { API_URL } from "@/lib/api";

export default function Home() {
  // Incrementar a versao faz o TaskList buscar de novo.
  const [versao, setVersao] = useState(0);
  const recarregar = () => setVersao((v) => v + 1);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Falange - tela de teste</h1>
        <p className="mt-1 text-sm text-gray-500">
          Backend: <code className="rounded bg-gray-100 px-1">{API_URL}</code>. Tasks criadas via
          MCP aparecem ao recarregar a lista.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-[20rem_1fr]">
        <aside>
          <TaskForm onCriada={recarregar} />
        </aside>
        <TaskList versao={versao} onRecarregar={recarregar} />
      </div>
    </main>
  );
}
