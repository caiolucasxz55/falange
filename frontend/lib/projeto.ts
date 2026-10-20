/**
 * Em que projeto a tela esta trabalhando.
 *
 * Fica no localStorage porque e preferencia de VISUALIZACAO por navegador,
 * nao estado do time: duas pessoas podem estar olhando projetos diferentes
 * ao mesmo tempo, e isso nao e conflito.
 *
 * Todo acesso e protegido: em aba anonima, com dados do site bloqueados ou
 * durante a captura de miniatura, ler ou escrever pode estourar. Sem o
 * valor guardado, a tela cai no projeto padrao do backend -- que e
 * exatamente o comportamento de quem nunca escolheu nada.
 */

const CHAVE = "falange_projeto";

/** Header que o backend le para saber o projeto da chamada. */
export const HEADER_PROJETO = "X-Falange-Projeto";

export function projetoLembrado(): string | null {
  try {
    return window.localStorage.getItem(CHAVE);
  } catch {
    return null;
  }
}

export function lembrarProjeto(slug: string | null): void {
  try {
    if (slug === null) {
      window.localStorage.removeItem(CHAVE);
    } else {
      window.localStorage.setItem(CHAVE, slug);
    }
  } catch {
    // Sem onde guardar: a tela segue funcionando no projeto padrao.
  }
}
