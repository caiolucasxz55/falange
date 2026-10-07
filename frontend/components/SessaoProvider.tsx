"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { verEu } from "@/lib/api";
import type { Acao, Eu } from "@/types/task";

/**
 * Quem esta usando a tela, e o que essa pessoa alcanca.
 *
 * A fonte da verdade e o backend: `GET /eu` devolve o papel lido do banco e
 * a lista de acoes. A tela NAO decide permissao -- ela so evita desenhar
 * botao que ja se sabe que vai dar 403. Quem recusa de fato e a API, e e por
 * isso que esconder aqui e cortesia, nao seguranca.
 */
interface Estado {
  eu: Eu | null;
  carregando: boolean;
  /** Mensagem quando nem /eu respondeu (backend fora, ou sessao morta). */
  erro: string | null;
  pode: (acao: Acao) => boolean;
  recarregar: () => void;
}

const Contexto = createContext<Estado | null>(null);

export function SessaoProvider({ children }: { children: ReactNode }) {
  const [eu, setEu] = useState<Eu | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  // Comeca em 0 e sobe a cada recarga; o efeito depende disso.
  const [versao, setVersao] = useState(0);
  const [resolvido, setResolvido] = useState(false);

  useEffect(() => {
    let ativo = true;
    verEu()
      .then((novo) => {
        if (!ativo) return;
        setEu(novo);
        setErro(null);
        setResolvido(true);
      })
      .catch(() => {
        if (!ativo) return;
        // 401 aqui e o caso normal de "nao logado": nao e erro de tela.
        setEu(null);
        setErro(null);
        setResolvido(true);
      });
    return () => {
      ativo = false;
    };
  }, [versao]);

  const recarregar = useCallback(() => {
    setResolvido(false);
    setVersao((v) => v + 1);
  }, []);

  const pode = useCallback(
    (acao: Acao) => eu?.acoes.includes(acao) ?? false,
    [eu],
  );

  return (
    <Contexto.Provider
      value={{ eu, carregando: !resolvido, erro, pode, recarregar }}
    >
      {children}
    </Contexto.Provider>
  );
}

export function useSessao(): Estado {
  const estado = useContext(Contexto);
  if (estado === null) {
    throw new Error("useSessao precisa estar dentro de <SessaoProvider>");
  }
  return estado;
}
