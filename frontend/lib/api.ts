import type {
  Autonomia,
  Configuracao,
  EdicaoNota,
  EdicaoTask,
  FiltrosTask,
  Nota,
  NovaNota,
  NivelAutonomia,
  NovaTask,
  Perfil,
  Preferencia,
  Priorizacao,
  Status,
  Task,
} from "@/types/task";

/**
 * O navegador fala com a MESMA origem: /api e um proxy do Next que injeta o
 * token no servidor (app/api/[...caminho]/route.ts). O token nunca chega ao
 * bundle, e nao ha CORS no caminho.
 *
 * Para apontar para outro backend, use FALANGE_BACKEND_URL no servidor, nao
 * aqui: esta constante e o caminho do proxy, nao o endereco do backend.
 */
export const API_URL = "/api";

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

/** PATCH /notas/{notaId} */
export function editarNota(notaId: number, campos: EdicaoNota): Promise<Nota> {
  return pedir<Nota>(`/notas/${notaId}`, {
    method: "PATCH",
    body: JSON.stringify(campos),
  });
}

/** DELETE /notas/{notaId} */
export async function apagarNota(notaId: number): Promise<void> {
  await pedir<null>(`/notas/${notaId}`, { method: "DELETE" });
}

/** GET /priorizacao */
export function verPriorizacao(limite = 3): Promise<Priorizacao> {
  return pedir<Priorizacao>(`/priorizacao?limite=${limite}`);
}

/** GET /configuracao */
export function verConfiguracao(): Promise<Configuracao> {
  return pedir<Configuracao>("/configuracao");
}

/** PATCH /configuracao */
export function definirConfiguracao(campos: Partial<Configuracao>): Promise<Configuracao> {
  return pedir<Configuracao>("/configuracao", {
    method: "PATCH",
    body: JSON.stringify(campos),
  });
}

/** GET /perfil */
export function verPerfil(): Promise<Perfil> {
  return pedir<Perfil>("/perfil");
}

/** GET /preferencias */
export function listarPreferencias(): Promise<Preferencia[]> {
  return pedir<Preferencia[]>("/preferencias");
}

/** PATCH /preferencias/{id}. ativa=false desliga, sempre permitido. */
export function definirPreferencia(id: number, ativa: boolean): Promise<Preferencia> {
  return pedir<Preferencia>(`/preferencias/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ ativa }),
  });
}

/** GET /autonomia */
export function verAutonomia(): Promise<Autonomia> {
  return pedir<Autonomia>("/autonomia");
}

/** PATCH /autonomia/{tipo}. A tela so rebaixa; subir e pela conversa. */
export function definirAutonomia(
  tipoAcao: string,
  nivel: NivelAutonomia,
): Promise<{ acoes: Record<string, NivelAutonomia> }> {
  return pedir(`/autonomia/${tipoAcao}`, {
    method: "PATCH",
    body: JSON.stringify({ nivel }),
  });
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
