"use client";

import { useState } from "react";

import { entrar, mensagemDoErro } from "@/lib/api";
import { useSessao } from "@/components/SessaoProvider";

interface LoginProps {
  /**
   * Chamado depois de entrar. Existe porque, no modo sem login, quem
   * pediu a tela de login foi a propria pagina: sem avisar de volta, ela
   * continuaria mostrando o formulario para sempre.
   */
  onEntrou?: () => void;
}

/**
 * Tela de entrada.
 *
 * A senha nunca sai daqui para o estado global nem para o localStorage: vai
 * no corpo do POST e e esquecida. O que volta sao cookies HttpOnly, gravados
 * pelo proxy -- este componente nao ve token nenhum.
 */
export function Login({ onEntrou }: LoginProps = {}) {
  const { recarregar } = useSessao();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function submeter(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar({ email: email.trim(), senha });
      setSenha("");
      onEntrou?.();
      recarregar();
    } catch (e) {
      setErro(mensagemDoErro(e));
      setEnviando(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center px-4">
      <h1 className="text-2xl font-semibold text-gray-900">Falange</h1>
      <p className="mt-1 text-sm text-gray-500">
        Entre para ver e mexer no quadro do time.
      </p>

      <form onSubmit={submeter} className="mt-6 flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-gray-700">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
            className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-900
                       focus:border-gray-900 focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-gray-700">Senha</span>
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
            autoComplete="current-password"
            className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-900
                       focus:border-gray-900 focus:outline-none"
          />
        </label>

        {erro !== null && (
          <p role="alert" className="text-sm text-red-700">
            {erro}
          </p>
        )}

        <button
          type="submit"
          disabled={enviando}
          className="mt-1 rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white
                     hover:bg-gray-700 disabled:opacity-50"
        >
          {enviando ? "Entrando..." : "Entrar"}
        </button>
      </form>

      <p className="mt-6 text-xs text-gray-500">
        Nao existe cadastro aberto nem recuperacao de senha: um admin cria a
        conta e entrega a senha. Troque depois em &quot;Minha conta&quot;.
      </p>
    </main>
  );
}
