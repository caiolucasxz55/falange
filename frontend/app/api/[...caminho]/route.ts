/**
 * Proxy do backend, executado no servidor do Next.
 *
 * Por que existe: nenhum segredo pode ir para o navegador. Qualquer coisa em
 * NEXT_PUBLIC_ e embutida no bundle e fica visivel para quem abrir a pagina,
 * entao seria ofuscacao, nao autenticacao. Aqui os segredos ficam no processo
 * do servidor e o navegador fala com a mesma origem (/api/...), o que de
 * quebra dispensa CORS.
 *
 * Com login, este arquivo guarda DOIS segredos por pessoa em cookies
 * HttpOnly -- o access e o refresh. O JavaScript da pagina nao os alcanca,
 * entao um XSS na tela nao rouba a sessao. O token compartilhado continua
 * sendo a porta do cliente, e e o que vale para quem ainda nao fez login.
 *
 * O access vence rapido (15 min por padrao). Em vez de empurrar isso para a
 * tela, o 401 e tratado aqui uma vez: renova com o refresh, repete o pedido
 * e grava os cookies novos. A pessoa nao ve.
 */

import { cookies } from "next/headers";

const BACKEND = process.env.FALANGE_BACKEND_URL ?? "http://127.0.0.1:8010";
const TOKEN = process.env.FALANGE_API_TOKEN ?? "";

const COOKIE_ACCESS = "falange_access";
const COOKIE_REFRESH = "falange_refresh";

// Metodos sem corpo; ler req.text() neles devolve "" e quebra o GET.
const SEM_CORPO = new Set(["GET", "HEAD", "DELETE"]);

// O refresh dura mais que o access de proposito: e ele que evita pedir senha
// de novo. O backend tem a palavra final (SESSAO_DIAS) -- isto e so o cookie.
const DIAS_REFRESH = 30;

/** Resposta do backend ao abrir ou renovar sessao. */
interface SessaoAberta {
  access: string;
  refresh: string;
  expira_em_minutos: number;
}

type Cofre = Awaited<ReturnType<typeof cookies>>;

/**
 * `secure` fica de fora em dev (http://localhost): com ele, o navegador
 * descarta o cookie e o login "funciona" sem nunca logar. Em producao o
 * HTTPS e obrigatorio, e ai a flag volta.
 */
function guardar(cofre: Cofre, nome: string, valor: string, maxAge: number): void {
  cofre.set({
    name: nome,
    value: valor,
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge,
    secure: process.env.NODE_ENV === "production",
  });
}

function guardarSessao(cofre: Cofre, sessao: SessaoAberta): void {
  // O cookie do access vive um pouco mais que a validade do token: assim ele
  // chega ao backend, toma 401 e dispara a renovacao, em vez de desaparecer
  // antes e fazer a tela cair para o token compartilhado sem avisar.
  guardar(cofre, COOKIE_ACCESS, sessao.access, sessao.expira_em_minutos * 60 + 60);
  guardar(cofre, COOKIE_REFRESH, sessao.refresh, 60 * 60 * 24 * DIAS_REFRESH);
}

function limparSessao(cofre: Cofre): void {
  cofre.delete(COOKIE_ACCESS);
  cofre.delete(COOKIE_REFRESH);
}

function cabecalhos(requisicao: Request, access: string | null): Headers {
  const saida = new Headers();
  // O access da pessoa tem prioridade; o token compartilhado e o fallback
  // para quem ainda nao entrou (vale enquanto EXIGIR_LOGIN=false).
  const credencial = access || TOKEN;
  if (credencial) saida.set("Authorization", `Bearer ${credencial}`);
  const tipo = requisicao.headers.get("content-type");
  if (tipo) saida.set("Content-Type", tipo);
  return saida;
}

function chamar(
  destino: string,
  metodo: string,
  enviados: Headers,
  corpo: string | undefined,
): Promise<Response> {
  return fetch(destino, {
    method: metodo,
    headers: enviados,
    body: corpo,
    cache: "no-store",
  });
}

/** Troca o refresh por um par novo. null quando o refresh ja nao vale. */
async function renovar(refresh: string): Promise<SessaoAberta | null> {
  const porta = new Headers({ "Content-Type": "application/json" });
  if (TOKEN) porta.set("Authorization", `Bearer ${TOKEN}`);
  try {
    const resposta = await fetch(`${BACKEND}/sessao/renovar`, {
      method: "POST",
      headers: porta,
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
    if (!resposta.ok) return null;
    return (await resposta.json()) as SessaoAberta;
  } catch {
    return null;
  }
}

function repassar(resposta: Response, corpo: string): Response {
  const tipo = resposta.headers.get("content-type") ?? "application/json";
  // 204 nao pode ter corpo; repassar um aqui vira erro no navegador.
  if (resposta.status === 204) return new Response(null, { status: 204 });
  return new Response(corpo, {
    status: resposta.status,
    headers: { "content-type": tipo },
  });
}

async function encaminhar(
  requisicao: Request,
  contexto: { params: Promise<{ caminho: string[] }> },
): Promise<Response> {
  const { caminho } = await contexto.params;
  const rota = caminho.join("/");
  const busca = new URL(requisicao.url).search;
  const destino = `${BACKEND}/${rota}${busca}`;
  const corpo = SEM_CORPO.has(requisicao.method) ? undefined : await requisicao.text();

  const eLogin = rota === "sessao" && requisicao.method === "POST";
  const eLogout = rota === "sessao" && requisicao.method === "DELETE";

  const cofre = await cookies();
  const access = cofre.get(COOKIE_ACCESS)?.value ?? null;
  const refresh = cofre.get(COOKIE_REFRESH)?.value ?? null;

  let resposta: Response;
  try {
    // No login, nunca mande o access velho: o backend precisa so da porta.
    resposta = await chamar(
      destino,
      requisicao.method,
      cabecalhos(requisicao, eLogin ? null : access),
      corpo,
    );
  } catch {
    return Response.json({ detail: `backend inacessivel em ${BACKEND}` }, { status: 502 });
  }

  let texto = resposta.status === 204 ? "" : await resposta.text();

  // Sessao expirada: renova uma vez e repete. Sem isto, a tela deslogaria
  // sozinha a cada 15 minutos.
  if (resposta.status === 401 && access && refresh && !eLogin) {
    const nova = await renovar(refresh);
    if (nova) {
      guardarSessao(cofre, nova);
      const repetida = await chamar(
        destino,
        requisicao.method,
        cabecalhos(requisicao, nova.access),
        corpo,
      );
      return repassar(repetida, repetida.status === 204 ? "" : await repetida.text());
    }
    // O refresh tambem morreu: limpa para a tela pedir login de novo.
    limparSessao(cofre);
    return repassar(resposta, texto);
  }

  if (eLogin && resposta.ok) {
    const sessao = JSON.parse(texto) as SessaoAberta;
    guardarSessao(cofre, sessao);
    // Os tokens ficam nos cookies e NAO voltam para o navegador; a tela so
    // precisa saber quem entrou.
    const { access: _descartado, refresh: _tambem, ...publico } = sessao;
    texto = JSON.stringify(publico);
  }

  if (eLogout) limparSessao(cofre);

  return repassar(resposta, texto);
}

export const GET = encaminhar;
export const POST = encaminhar;
export const PATCH = encaminhar;
export const PUT = encaminhar;
export const DELETE = encaminhar;
