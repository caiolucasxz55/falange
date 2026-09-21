// Espelho do modelo do backend (backend/models.py e backend/schemas.py).
// Os nomes dos campos seguem o backend (snake_case) de proposito: assim o
// JSON da API entra direto nestes tipos, sem camada de conversao.

// Os arrays sao a fonte unica: os tipos derivam deles e os <select> do
// formulario iteram sobre eles, entao opcao e tipo nunca divergem.
export const ESTIMATIVAS = ["PP", "P", "M", "G"] as const;
export const BLOCOS = ["frontend", "backend", "infra", "seguranca"] as const;
export const STATUS = ["aberta", "em_andamento", "concluida"] as const;

export type Estimativa = (typeof ESTIMATIVAS)[number]; // "PP" | "P" | "M" | "G"
export type Bloco = (typeof BLOCOS)[number]; // "frontend" | "backend" | "infra" | "seguranca"
export type Status = (typeof STATUS)[number]; // "aberta" | "em_andamento" | "concluida"

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
}

/** Payload de criacao (TaskNova). id e status sao definidos pelo backend. */
export interface NovaTask {
  titulo: string;
  descricao?: string;
  estimativa: Estimativa;
  bloco: Bloco;
  responsavel?: string | null;
}

export function isEstimativa(valor: string): valor is Estimativa {
  return (ESTIMATIVAS as readonly string[]).includes(valor);
}

export function isBloco(valor: string): valor is Bloco {
  return (BLOCOS as readonly string[]).includes(valor);
}
