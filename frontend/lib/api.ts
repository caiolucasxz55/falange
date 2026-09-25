import type {
  EdicaoTask,
  FiltrosTask,
  Nota,
  NovaNota,
  NovaTask,
  Status,
  Task,
} from "@/types/task";

/**
 * URL do backend Falange. Troque por NEXT_PUBLIC_API_URL no .env.local.
 *
 * O padrao e 8010, nao 8000: nesta maquina a 8000 e de outro projeto
 * (ResinArts) e o docker-compose publica o Falange na 8010.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

/** Erro de chamada ao backend, com mensagem pronta para mostrar na tela. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Texto para exibir a partir de qualquer erro lancado por estas funcoes. */
export function mensagemDoErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : "Erro inesperado";
}

// ---------------------------------------------------------------------------
// endpoints
// ---------------------------------------------------------------------------

/** GET /tasks. Os filtros vao como query string: quem filtra e o backend. */
export function listarTasks(filtros: FiltrosTask = {}): Promise<Task[]> {
  const query = new URLSearchParams();
  for (const [campo, valor] of Object.entries(filtros)) {
    const limpo = valor?.trim();
    if (limpo) query.set(campo, limpo);
  }
  const busca = query.toString();
  return pedir<Task[]>(busca ? `/tasks?${busca}` : "/tasks");
}

/** POST /tasks */
export function criarTask(nova: NovaTask): Promise<Task> {
  return pedir<Task>("/tasks", { method: "POST", body: JSON.stringify(nova) });
}

/** PATCH /tasks/{taskId}. So os campos enviados mudam. */
export function editarTask(taskId: number, campos: EdicaoTask): Promise<Task> {
  // "" significa remover o responsavel; o backend so desatribui com null.
  // Mesma convencao da tool do MCP, que faz essa conversao do lado dela.
  const corpo: Record<string, unknown> = { ...campos };
  if (campos.responsavel === "") corpo.responsavel = null;

  return pedir<Task>(`/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(corpo),
  });
}

/** PATCH /tasks/{taskId}/status */
export function mudarStatus(taskId: number, status: Status): Promise<Task> {
  return pedir<Task>(`/tasks/${taskId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

/** DELETE /tasks/{taskId}. Responde 204, sem corpo. */
export async function apagarTask(taskId: number): Promise<void> {
  await pedir<null>(`/tasks/${taskId}`, { method: "DELETE" });
}

/** PATCH /tasks/{taskId}/bloqueio. bloqueadaPor = null desbloqueia. */
export function marcarBloqueio(taskId: number, bloqueadaPor: number | null): Promise<Task> {
  return pedir<Task>(`/tasks/${taskId}/bloqueio`, {
    method: "PATCH",
    body: JSON.stringify({ bloqueada_por: bloqueadaPor }),
  });
}

/** GET /notas */
export function listarNotas(resolvida?: boolean): Promise<Nota[]> {
  const busca = resolvida === undefined ? "" : `?resolvida=${resolvida}`;
  return pedir<Nota[]>(`/notas${busca}`);
}

/** POST /notas */
export function registrarNota(nova: NovaNota): Promise<Nota> {
  return pedir<Nota>("/notas", { method: "POST", body: JSON.stringify(nova) });
}

/** PATCH /notas/{notaId}/resolver */
export function resolverNota(notaId: number): Promise<Nota> {
  return pedir<Nota>(`/notas/${notaId}/resolver`, { method: "PATCH" });
}

// ---------------------------------------------------------------------------
// infraestrutura
// ---------------------------------------------------------------------------

async function pedir<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  // Content-Type so quando ha corpo: num GET ele forcaria um preflight a toa.
  const headers = init.body ? { "Content-Type": "application/json" } : undefined;

  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, { ...init, headers });
  } catch {
    // fetch so rejeita em falha de rede (ou CORS): backend fora do ar.
    throw new ApiError(0, `Backend inacessivel em ${API_URL}. Ele esta rodando?`);
  }

  if (!resposta.ok) {
    throw new ApiError(resposta.status, await mensagemDeErro(resposta));
  }

  // 204 (DELETE) nao tem corpo: json() estouraria.
  if (resposta.status === 204) return null as T;

  // Fronteira de confianca: o JSON e assumido no formato T, sem validacao em
  // tempo de execucao. Suficiente para uma tela de teste contra o proprio backend.
  const dados: unknown = await resposta.json();
  return dados as T;
}

/** FastAPI devolve {detail: string} ou, no 422, {detail: [{loc, msg}, ...]}. */
async function mensagemDeErro(resposta: Response): Promise<string> {
  const corpo: unknown = await resposta.json().catch(() => null);

  if (typeof corpo === "object" && corpo !== null && "detail" in corpo) {
    const { detail } = corpo;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(formatarErroDeValidacao).join("; ");
  }
  return `Erro HTTP ${resposta.status}`;
}

function formatarErroDeValidacao(item: unknown): string {
  if (typeof item !== "object" || item === null) return "valor invalido";

  const msg = "msg" in item && typeof item.msg === "string" ? item.msg : "valor invalido";
  const campo =
    "loc" in item && Array.isArray(item.loc)
      ? item.loc.filter((parte) => parte !== "body").join(".")
      : "";
  return campo ? `${campo}: ${msg}` : msg;
}
