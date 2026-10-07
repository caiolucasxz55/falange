"use client";

import { useState } from "react";

import { mensagemDoErro, sair, trocarSenha } from "@/lib/api";
import { useSessao } from "@/components/SessaoProvider";
import type { Papel } from "@/types/task";

const ROTULO_PAPEL: Record<Papel, string> = {
  admin: "admin",
  lead: "lead",
  dev: "dev",
  leitor: "leitor",
  ia: "IA",
};

/** O que cada papel pode, em uma linha, para a pessoa saber onde esta. */
const RESUMO_PAPEL: Record<Papel, string> = {
  admin: "gerencia o time e a plataforma",
  lead: "prioriza, atribui e sobe a autonomia da IA",
  dev: "cria e executa; apaga o que e seu",
  leitor: "somente leitura",
  ia: "conta de servico do MCP",
};

interface CabecalhoProps {
  /** Chamado no modo sem login, quando a pessoa quer entrar de verdade. */
  onEntrar: () => void;
}

export function Cabecalho({ onEntrar }: CabecalhoProps) {
  const { eu, recarregar } = useSessao();
  const [trocando, setTrocando] = useState(false);

  if (eu === null) return null;

  async function encerrar() {
    try {
      await sair();
    } finally {
      // Mesmo se o backend reclamar, os cookies ja foram apagados pelo proxy.
      recarregar();
    }
  }

  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Falange</h1>
        <p className="mt-1 text-sm text-gray-500">
          A lista atualiza sozinha a cada 15s enquanto a aba estiver visivel.
        </p>
      </div>

      <div className="flex flex-col items-end gap-1 text-sm">
        {eu.sem_login ? (
          <>
            <span className="rounded bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900">
              sem login
            </span>
            <span className="text-xs text-gray-500">
              tratado como admin (EXIGIR_LOGIN=false)
            </span>
            <button
              type="button"
              onClick={onEntrar}
              className="mt-1 text-xs text-gray-600 underline hover:text-gray-900"
            >
              entrar com uma conta
            </button>
          </>
        ) : (
          <>
            <span className="font-medium text-gray-900">{eu.usuario?.nome}</span>
            <span className="text-xs text-gray-500">
              {eu.papel ? `${ROTULO_PAPEL[eu.papel]} - ${RESUMO_PAPEL[eu.papel]}` : ""}
            </span>
            <div className="mt-1 flex gap-3">
              <button
                type="button"
                onClick={() => setTrocando((v) => !v)}
                className="text-xs text-gray-600 underline hover:text-gray-900"
              >
                {trocando ? "cancelar" : "trocar senha"}
              </button>
              <button
                type="button"
                onClick={encerrar}
                className="text-xs text-gray-600 underline hover:text-gray-900"
              >
                sair
              </button>
            </div>
          </>
        )}
      </div>

      {trocando && <TrocaDeSenha onPronto={() => setTrocando(false)} />}
    </header>
  );
}

function TrocaDeSenha({ onPronto }: { onPronto: () => void }) {
  const { recarregar } = useSessao();
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  async function submeter(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await trocarSenha(atual, nova);
      // Trocar a senha encerra todas as sessoes, inclusive esta: recarregar
      // leva de volta ao login, que e o comportamento esperado.
      onPronto();
      recarregar();
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  return (
    <form
      onSubmit={submeter}
      className="w-full rounded border border-gray-200 bg-gray-50 p-3"
    >
      <p className="mb-2 text-xs text-gray-600">
        Trocar a senha encerra todas as sessoes, inclusive esta.
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <input
          type="password"
          value={atual}
          onChange={(e) => setAtual(e.target.value)}
          placeholder="senha atual"
          required
          autoComplete="current-password"
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <input
          type="password"
          value={nova}
          onChange={(e) => setNova(e.target.value)}
          placeholder="senha nova"
          required
          minLength={10}
          autoComplete="new-password"
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <button
          type="submit"
          className="rounded bg-gray-900 px-3 py-1 text-sm font-medium text-white hover:bg-gray-700"
        >
          Trocar
        </button>
      </div>
      {erro !== null && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {erro}
        </p>
      )}
    </form>
  );
}
