"use client";

import { useCallback, useState } from "react";

import { Board } from "@/components/Board";
import { Cabecalho } from "@/components/Cabecalho";
import { Filtros } from "@/components/Filtros";
import { Login } from "@/components/Login";
import { PainelAprendizado } from "@/components/PainelAprendizado";
import { PainelAutonomia } from "@/components/PainelAutonomia";
import { PainelNotas } from "@/components/PainelNotas";
import { PainelRecomendadas } from "@/components/PainelRecomendadas";
import { PainelUsuarios } from "@/components/PainelUsuarios";
import { SessaoProvider, useSessao } from "@/components/SessaoProvider";
import { TaskForm } from "@/components/TaskForm";
import type { FiltrosTask } from "@/types/task";

export default function Home() {
  return (
    <SessaoProvider>
      <Conteudo />
    </SessaoProvider>
  );
}

function Conteudo() {
  const { eu, carregando } = useSessao();
  const [filtros, setFiltros] = useState<FiltrosTask>({});
  // No modo sem login a tela funciona sem conta, mas ainda tem de DAR
  // para entrar; sem isto, o login ficaria inalcancavel.
  const [querEntrar, setQuerEntrar] = useState(false);
  // Incrementar a versao faz o Board buscar de novo.
  const [versao, setVersao] = useState(0);
  // useCallback: o Board usa isto na dependencia do polling, e uma funcao
  // nova a cada render reiniciaria o intervalo sem parar.
  const recarregar = useCallback(() => setVersao((v) => v + 1), []);

  // Enquanto /eu nao responde, nao da para saber se e login ou board. Mostrar
  // um dos dois aqui faria a tela piscar o errado.
  if (carregando) {
    return (
      <main className="mx-auto w-full max-w-[90rem] px-4 py-8">
        <p className="text-sm text-gray-500">Carregando...</p>
      </main>
    );
  }

  if (eu === null || querEntrar) {
    return <Login onEntrou={() => setQuerEntrar(false)} />;
  }

  // Um leitor nao escreve nada: os paineis de escrita saem da tela em vez de
  // oferecerem botao que vai dar 403.
  const escreve = eu.acoes.includes("criar_task");

  return (
    <main className="mx-auto w-full max-w-[90rem] px-4 py-8">
      <Cabecalho onEntrar={() => setQuerEntrar(true)} />

      <div className="grid gap-6 md:grid-cols-[20rem_1fr]">
        <aside>
          <PainelUsuarios />
          {escreve && <TaskForm onCriada={recarregar} />}
          <PainelNotas onMudou={recarregar} />
          <PainelAprendizado />
          <PainelAutonomia />
        </aside>
        <div>
          <PainelRecomendadas versao={versao} />
          <Filtros filtros={filtros} onMudar={setFiltros} />
          <Board filtros={filtros} versao={versao} onRecarregar={recarregar} />
        </div>
      </div>
    </main>
  );
}
