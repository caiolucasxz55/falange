"use client";

import { useEffect, useState } from "react";

import {
  criarProjeto,
  listarProjetos,
  mensagemDoErro,
  verProjeto,
} from "@/lib/api";
import { lembrarProjeto } from "@/lib/projeto";
import { useSessao } from "@/components/SessaoProvider";
import type { Projeto, ProjetoAtual } from "@/types/task";

/**
 * Em que projeto a tela esta trabalhando.
 *
 * Trocar de projeto recarrega a pagina de proposito. O projeto atravessa
 * TUDO -- board, notas, priorizacao, aprendizado, autonomia --, e cada um
 * desses paineis busca por conta propria; avisar um por um deixaria a tela
 * misturando dados de dois projetos durante alguns instantes, que e
 * exatamente o que a Fase D existe para impedir.
 *
 * Quem nao gere projetos ve so o nome do atual, sem seletor: o backend
 * recusaria a listagem com 403.
 */
export function SeletorProjeto() {
  const { pode } = useSessao();
  const [atual, setAtual] = useState<ProjetoAtual | null>(null);
  const [projetos, setProjetos] = useState<Projeto[] | null>(null);
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const podeGerir = pode("gerir_projetos");

  useEffect(() => {
    let ativo = true;
    verProjeto()
      .then((p) => ativo && setAtual(p))
      .catch(() => ativo && setAtual(null));
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!podeGerir) return;
    let ativo = true;
    listarProjetos()
      .then((lista) => ativo && setProjetos(lista))
      .catch(() => ativo && setProjetos(null));
    return () => {
      ativo = false;
    };
  }, [podeGerir]);

  if (atual === null) return null;

  function trocar(slug: string) {
    lembrarProjeto(slug);
    window.location.reload();
  }

  return (
    <div className="flex flex-col items-start gap-1">
      {podeGerir && projetos !== null ? (
        <div className="flex items-center gap-2">
          <select
            value={atual.projeto.slug}
            onChange={(e) => trocar(e.target.value)}
            aria-label="Projeto"
            className="rounded border border-gray-300 px-2 py-1 text-sm text-gray-900"
          >
            {projetos.map((p) => (
              <option key={p.id} value={p.slug}>
                {p.nome}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setCriando((v) => !v)}
            className="text-xs text-gray-600 underline hover:text-gray-900"
          >
            {criando ? "cancelar" : "novo projeto"}
          </button>
        </div>
      ) : (
        <span className="text-sm text-gray-700">
          Projeto: <strong>{atual.projeto.nome}</strong>
        </span>
      )}

      {erro !== null && (
        <p role="alert" className="text-xs text-red-700">
          {erro}
        </p>
      )}

      {criando && (
        <Novo
          onCriado={(slug) => trocar(slug)}
          onErro={setErro}
        />
      )}
    </div>
  );
}

function Novo({
  onCriado,
  onErro,
}: {
  onCriado: (slug: string) => void;
  onErro: (erro: string | null) => void;
}) {
  const [slug, setSlug] = useState("");
  const [nome, setNome] = useState("");

  async function submeter(evento: React.FormEvent) {
    evento.preventDefault();
    onErro(null);
    try {
      const criado = await criarProjeto({ slug: slug.trim(), nome: nome.trim() });
      onCriado(criado.slug);
    } catch (e) {
      onErro(mensagemDoErro(e));
    }
  }

  return (
    <form onSubmit={submeter} className="flex flex-wrap items-center gap-2">
      <input
        value={nome}
        onChange={(e) => setNome(e.target.value)}
        placeholder="nome"
        required
        minLength={2}
        className="rounded border border-gray-300 px-2 py-1 text-sm"
      />
      <input
        value={slug}
        onChange={(e) => setSlug(e.target.value)}
        placeholder="slug (ex.: falange)"
        required
        minLength={2}
        pattern="[a-z0-9]([a-z0-9-]*[a-z0-9])?"
        title="minusculas, digitos e hifen; sem hifen nas pontas"
        className="rounded border border-gray-300 px-2 py-1 text-sm"
      />
      <button
        type="submit"
        className="rounded bg-gray-900 px-3 py-1 text-sm font-medium text-white hover:bg-gray-700"
      >
        Criar
      </button>
    </form>
  );
}
