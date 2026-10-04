// Espelho do modelo do backend (backend/models.py e backend/schemas.py).
// Os nomes dos campos seguem o backend (snake_case) de proposito: assim o
// JSON da API entra direto nestes tipos, sem camada de conversao.

// Os arrays sao a fonte unica: os tipos derivam deles e os <select> do
// formulario iteram sobre eles, entao opcao e tipo nunca divergem.
export const ESTIMATIVAS = ["PP", "P", "M", "G"] as const;
export const BLOCOS = ["frontend", "backend", "infra", "seguranca"] as const;
export const STATUS = ["aberta", "em_andamento", "concluida"] as const;
export const PRIORIDADES = ["alta", "media", "baixa"] as const;

export type Estimativa = (typeof ESTIMATIVAS)[number]; // "PP" | "P" | "M" | "G"
export type Bloco = (typeof BLOCOS)[number]; // "frontend" | "backend" | "infra" | "seguranca"
export type Status = (typeof STATUS)[number]; // "aberta" | "em_andamento" | "concluida"
export type Prioridade = (typeof PRIORIDADES)[number]; // "alta" | "media" | "baixa"

/** Task como o backend devolve (TaskOut). */
export interface Task {
  id: number;
  titulo: string;
  descricao: string;
  estimativa: Estimativa;
  bloco: Bloco;
  responsavel: string | null;
  /** Id da task que trava esta. null = nao esta bloqueada. */
  bloqueada_por: number | null;
  status: Status;
  prioridade: Prioridade;
  /** Datas ISO 8601 com timezone, como o backend devolve. */
  criada_em: string;
  atualizada_em: string;
  /** Primeira ida para em_andamento; null se nunca comecou. */
  iniciada_em: string | null;
  concluida_em: string | null;
}

/** Payload de criacao (TaskNova). id e status sao definidos pelo backend. */
export interface NovaTask {
  titulo: string;
  descricao?: string;
  estimativa: Estimativa;
  bloco: Bloco;
  prioridade?: Prioridade;
  responsavel?: string | null;
}

/** Campos que o board consegue editar de uma task existente. */
export interface EdicaoTask {
  titulo?: string;
  descricao?: string;
  estimativa?: Estimativa;
  bloco?: Bloco;
  prioridade?: Prioridade;
  /** "" remove o responsavel, mesma convencao da tool do MCP. */
  responsavel?: string;
}

/** Filtros do topo do board. Vazio = sem filtro. */
export interface FiltrosTask {
  bloco?: Bloco | "";
  prioridade?: Prioridade | "";
  responsavel?: string;
}

export function isEstimativa(valor: string): valor is Estimativa {
  return (ESTIMATIVAS as readonly string[]).includes(valor);
}

export function isBloco(valor: string): valor is Bloco {
  return (BLOCOS as readonly string[]).includes(valor);
}

export function isPrioridade(valor: string): valor is Prioridade {
  return (PRIORIDADES as readonly string[]).includes(valor);
}

/** Dias inteiros desde uma data ISO do backend. */
export function diasDesde(iso: string): number {
  const ms = Date.now() - new Date(iso).getTime();
  return Math.max(0, Math.floor(ms / 86_400_000));
}

/** Registro solto do time: problema, decisao ou duvida. Nao e task. */
export interface Nota {
  id: number;
  texto: string;
  autor: string | null;
  /** Task ligada; volta a null se a task for apagada. */
  task_id: number | null;
  resolvida: boolean;
  criada_em: string;
}

export interface NovaNota {
  texto: string;
  autor?: string | null;
  task_id?: number | null;
}

/** Edicao parcial da nota. `resolvida: false` reabre uma nota fechada. */
export interface EdicaoNota {
  texto?: string;
  autor?: string | null;
  task_id?: number | null;
  resolvida?: boolean;
}

/** Uma sugestao do motor de priorizacao do backend. */
export interface Sugestao {
  id: number;
  titulo: string;
  prioridade: Prioridade;
  estimativa: Estimativa;
  bloco: Bloco;
  responsavel: string | null;
  status: Status;
  score: number;
  /** Frases prontas explicando o score; vem do backend. */
  motivos: string[];
  /** Ids que esperam por esta task, direta ou transitivamente. */
  destrava: number[];
}

export interface Alerta {
  tipo: "inversao" | "inflacao" | "parada";
  task_id: number | null;
  mensagem: string;
  tasks_afetadas: number[];
}

export interface Priorizacao {
  sugestoes: Sugestao[];
  alertas: Alerta[];
  avisos: string[];
}

export interface Configuracao {
  perguntas_ativas: boolean;
}

export type OrigemPreferencia = "explicita" | "inferida";

export interface Preferencia {
  id: number;
  descricao: string;
  origem: OrigemPreferencia;
  ativa: boolean;
  criada_em: string;
}

/** Habito detectado nos dados que ainda nao virou preferencia. */
export interface PadraoCandidato {
  descricao: string;
  tipo: string;
  rotulo: string;
  ocorrencias: number;
  total: number;
  consistencia: number;
}

export interface ClasseCalibrada {
  n: number;
  mediana_dias: number | null;
  faixa: { minimo_dias: number | null; maximo_dias: number | null };
  veredito: "coerente" | "superestimada" | "subestimada" | "sem_dados";
}

export interface Perfil {
  calibracao: {
    por_estimativa: Record<string, ClasseCalibrada>;
    por_bloco: Record<string, Record<string, ClasseCalibrada>>;
    n_total: number;
  } | null;
  aceitacao_por_tipo: Record<string, { n: number; aceitas: number; taxa: number }>;
  ajustes_comuns: string[];
  preferencias_ativas: Preferencia[];
  padroes_candidatos: PadraoCandidato[];
}
