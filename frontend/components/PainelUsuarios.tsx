"use client";

import { useEffect, useState } from "react";

import {
  criarUsuario,
  cortarSessoes,
  editarUsuario,
  listarUsuarios,
  mensagemDoErro,
} from "@/lib/api";
import { useSessao } from "@/components/SessaoProvider";
import type { Papel, Usuario } from "@/types/task";

/** Papeis que um admin pode atribuir. `ia` fica fora: e conta de servico. */
const PAPEIS: Papel[] = ["admin", "lead", "dev", "leitor"];

type Resultado =
  | { tipo: "ok"; usuarios: Usuario[] }
  | { tipo: "erro"; mensagem: string };

/**
 * Gestao de usuarios. So aparece para quem tem `gerir_usuarios`.
 *
 * Nao oferece apagar: a API nao tem DELETE de usuario de proposito, porque
 * apagar deixaria as tasks e decisoes da pessoa sem autor. Desativar corta o
 * acesso na hora e preserva o historico.
 */
export function PainelUsuarios() {
  const { pode, eu } = useSessao();
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [versao, setVersao] = useState(0);
  const [aberto, setAberto] = useState(false);

  const podeGerir = pode("gerir_usuarios");

  useEffect(() => {
    if (!podeGerir || !aberto) return;
    let ativo = true;
    listarUsuarios()
      .then((usuarios) => ativo && setResultado({ tipo: "ok", usuarios }))
      .catch(
        (e) =>
          ativo && setResultado({ tipo: "erro", mensagem: mensagemDoErro(e) }),
      );
    return () => {
      ativo = false;
    };
  }, [podeGerir, aberto, versao]);

  if (!podeGerir) return null;

  const recarregar = () => setVersao((v) => v + 1);

  return (
    <section className="mb-4 rounded border border-gray-200 p-3">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <h2 className="text-sm font-semibold text-gray-900">Time</h2>
        <span className="text-xs text-gray-500">{aberto ? "fechar" : "abrir"}</span>
      </button>

      {aberto && (
        <>
          {resultado?.tipo === "erro" && (
            <p role="alert" className="mt-2 text-sm text-red-700">
              {resultado.mensagem}
            </p>
          )}

          {resultado?.tipo === "ok" && (
            <ul className="mt-3 flex flex-col gap-2">
              {resultado.usuarios.map((usuario) => (
                <Linha
                  key={usuario.id}
                  usuario={usuario}
                  souEu={usuario.id === eu?.usuario?.id}
                  onMudou={recarregar}
                />
              ))}
            </ul>
          )}

          <Novo onCriado={recarregar} />
        </>
      )}
    </section>
  );
}

function Linha({
  usuario,
  souEu,
  onMudou,
}: {
  usuario: Usuario;
  souEu: boolean;
  onMudou: () => void;
}) {
  const [erro, setErro] = useState<string | null>(null);
  // A conta de servico nao se edita pela API; mostrar os controles seria
  // prometer o que vai dar 403.
  const eServico = usuario.papel === "ia";

  async function aplicar(acao: () => Promise<unknown>) {
    setErro(null);
    try {
      await acao();
      onMudou();
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  return (
    <li className="rounded border border-gray-100 bg-gray-50 p-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="font-medium text-gray-900">{usuario.nome}</span>
          {souEu && <span className="ml-1 text-xs text-gray-500">(voce)</span>}
          <span className="ml-2 text-xs text-gray-500">{usuario.email}</span>
          {!usuario.ativo && (
            <span className="ml-2 rounded bg-gray-200 px-1 text-xs text-gray-700">
              inativo
            </span>
          )}
        </div>

        {eServico ? (
          <span className="text-xs text-gray-500">conta de servico do MCP</span>
        ) : (
          <div className="flex items-center gap-2">
            <select
              value={usuario.papel}
              onChange={(e) =>
                aplicar(() =>
                  editarUsuario(usuario.id, { papel: e.target.value as Papel }),
                )
              }
              className="rounded border border-gray-300 px-1 py-0.5 text-xs"
            >
              {PAPEIS.map((papel) => (
                <option key={papel} value={papel}>
                  {papel}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={() =>
                aplicar(() => editarUsuario(usuario.id, { ativo: !usuario.ativo }))
              }
              className="text-xs text-gray-600 underline hover:text-gray-900"
            >
              {usuario.ativo ? "desativar" : "reativar"}
            </button>

            <button
              type="button"
              onClick={() => aplicar(() => cortarSessoes(usuario.id))}
              title="Derruba as sessoes abertas sem mexer na conta"
              className="text-xs text-gray-600 underline hover:text-gray-900"
            >
              cortar sessoes
            </button>
          </div>
        )}
      </div>

      {erro !== null && (
        <p role="alert" className="mt-1 text-xs text-red-700">
          {erro}
        </p>
      )}
    </li>
  );
}

function Novo({ onCriado }: { onCriado: () => void }) {
  const [email, setEmail] = useState("");
  const [nome, setNome] = useState("");
  const [senha, setSenha] = useState("");
  const [papel, setPapel] = useState<Papel>("dev");
  const [erro, setErro] = useState<string | null>(null);

  async function submeter(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await criarUsuario({ email: email.trim(), nome: nome.trim(), senha, papel });
      setEmail("");
      setNome("");
      setSenha("");
      onCriado();
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  return (
    <form onSubmit={submeter} className="mt-3 border-t border-gray-200 pt-3">
      <p className="mb-2 text-xs text-gray-600">
        Nova conta. Nao ha convite por email: entregue a senha a pessoa e peca
        que ela troque.
      </p>
      <div className="flex flex-col gap-2">
        <input
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder="nome"
          required
          minLength={2}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          required
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <input
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          placeholder="senha inicial (10+ caracteres)"
          required
          minLength={10}
          autoComplete="new-password"
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <div className="flex items-center gap-2">
          <select
            value={papel}
            onChange={(e) => setPapel(e.target.value as Papel)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            {PAPEIS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="rounded bg-gray-900 px-3 py-1 text-sm font-medium text-white hover:bg-gray-700"
          >
            Criar
          </button>
        </div>
      </div>
      {erro !== null && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {erro}
        </p>
      )}
    </form>
  );
}
