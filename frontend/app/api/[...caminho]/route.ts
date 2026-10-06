/**
 * Proxy do backend, executado no servidor do Next.
 *
 * Por que existe: o token nao pode ir para o navegador. Qualquer coisa em
 * NEXT_PUBLIC_ e embutida no bundle e fica visivel para quem abrir a pagina,
 * entao seria ofuscacao, nao autenticacao. Aqui o segredo fica no processo
 * do servidor e o navegador fala com a mesma origem (/api/...), o que de
 * quebra dispensa CORS.
 *
 * Nao e autorizacao por pessoa: quem abre a tela usa o token do servidor.
 * Enquanto nao houver login (V2), proteja QUEM alcanca o frontend.
 */

const BACKEND = process.env.FALANGE_BACKEND_URL ?? "http://127.0.0.1:8010";
const TOKEN = process.env.FALANGE_API_TOKEN ?? "";

// Metodos sem corpo; ler req.text() neles devolve "" e quebra o GET.
const SEM_CORPO = new Set(["GET", "HEAD", "DELETE"]);

async function encaminhar(
  requisicao: Request,
  contexto: { params: Promise<{ caminho: string[] }> },
): Promise<Response> {
  const { caminho } = await contexto.params;
  const busca = new URL(requisicao.url).search;
  const destino = `${BACKEND}/${caminho.join("/")}${busca}`;

  const cabecalhos = new Headers();
  if (TOKEN) cabecalhos.set("Authorization", `Bearer ${TOKEN}`);
  const tipo = requisicao.headers.get("content-type");
  if (tipo) cabecalhos.set("Content-Type", tipo);

  let resposta: Response;
  try {
    resposta = await fetch(destino, {
      method: requisicao.method,
      headers: cabecalhos,
      body: SEM_CORPO.has(requisicao.method) ? undefined : await requisicao.text(),
    });
  } catch {
    return Response.json(
      { detail: `backend inacessivel em ${BACKEND}` },
      { status: 502 },
    );
  }

  // 204 nao pode ter corpo; repassar um aqui vira erro no navegador.
  if (resposta.status === 204) return new Response(null, { status: 204 });

  return new Response(resposta.body, {
    status: resposta.status,
    headers: { "content-type": resposta.headers.get("content-type") ?? "application/json" },
  });
}

export const GET = encaminhar;
export const POST = encaminhar;
export const PATCH = encaminhar;
export const PUT = encaminhar;
export const DELETE = encaminhar;
