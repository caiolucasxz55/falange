"use client";

import { type FormEvent, useEffect, useState } from "react";

import { listarNotas, mensagemDoErro, registrarNota, resolverNota } from "@/lib/api";
import { diasDesde, type Nota } from "@/types/task";

// Mesmo padrao do Board: o resultado guarda a versao que o produziu, para
// "carregando" ser derivado em vez de setState sincrono no efeito.
type Resultado =
  | { versao: number; tipo: "ok"; notas: Nota[] }
  | { versao: number; tipo: "erro"; mensagem: string };

/** Notas abertas do time: lista, registro e resolucao. */
export function PainelNotas() {
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [versao, setVersao] = useState(0);
  const [texto, setTexto] = useState("");
  const [autor, setAutor] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    listarNotas(false)
      .then((notas) => {
        if (ativo) setResultado({ versao, tipo: "ok", notas });
      })
      .catch((e: unknown) => {
        if (ativo) setResultado({ versao, tipo: "erro", mensagem: mensagemDoErro(e) });
      });
    return () => {
      ativo = false;
    };
  }, [versao]);

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

  function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    void executar(async () => {
      await registrarNota({ texto: texto.trim(), autor: autor.trim() || null });
      setTexto("");
      setVersao((v) => v + 1);
    });
  }

  const resolver = (notaId: number) =>
    executar(async () => {
      await resolverNota(notaId);
      setVersao((v) => v + 1);
    });

  const notas = resultado?.tipo === "ok" ? resultado.notas : [];
  const estilo =
    "w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-gray-500 focus:outline-none";

  return (
    <section className="mt-4 rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-900">
        Notas abertas
        {resultado?.tipo === "ok" && (
          <span className="ml-2 text-sm font-normal text-gray-500">({notas.length})</span>
        )}
      </h2>
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
        <input
          maxLength={80}
          placeholder="autor (opcional)"
          value={autor}
          onChange={(e) => setAutor(e.target.value)}
          className={estilo}
          aria-label="Autor da nota"
        />
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
          <li key={nota.id} className="rounded border border-gray-200 p-2">
            <p className="whitespace-pre-line text-xs text-gray-700">{nota.texto}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-400">
              {nota.autor && <span>{nota.autor}</span>}
              {nota.task_id !== null && <span>task #{nota.task_id}</span>}
              <span>ha {diasDesde(nota.criada_em)}d</span>
              <button
                type="button"
                disabled={ocupado}
                onClick={() => resolver(nota.id)}
                className="ml-auto rounded border border-gray-300 px-2 py-0.5 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Resolver
              </button>
            </div>
          </li>
        ))}
      </ul>

      {resultado?.tipo === "ok" && notas.length === 0 && (
        <p className="mt-3 text-center text-xs text-gray-400">Nenhuma nota aberta.</p>
      )}
    </section>
  );
}
