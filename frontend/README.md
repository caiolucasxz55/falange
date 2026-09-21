# Falange - frontend de teste

Tela minima para validar visualmente o fluxo MCP -> backend. Nao e o design
final da Falange.

    npm install
    npm run dev        # http://localhost:3010

Backend esperado em `http://localhost:8010` (a stack do `docker-compose` na
raiz). Para trocar, copie `.env.example` para `.env.local` e ajuste
`NEXT_PUBLIC_API_URL` - ela e embutida no build, entao reinicie o `dev`.

## Estrutura

| Arquivo | Responsabilidade |
|---|---|
| `types/task.ts` | Tipos espelhando o modelo do backend |
| `lib/api.ts` | Unica camada que faz `fetch`; funcoes tipadas + `ApiError` |
| `components/TaskList.tsx` | Busca (`GET /tasks`) e renderiza a lista |
| `components/TaskCard.tsx` | Exibe uma task; so apresentacao |
| `components/TaskForm.tsx` | Criacao (`POST /tasks`) |
| `app/page.tsx` | Junta tudo; recarrega a lista quando uma task e criada |

Tasks criadas via MCP aparecem ao clicar em **Recarregar** (nao ha polling).

## Portas

3010 e nao 3000: nesta maquina a 3000 e de outro projeto. Se o Next cair em
outra porta, o CORS do backend (`CORS_ORIGINS`) bloqueia as chamadas.

Se `next dev` responder 404 em `/` com o `page.tsx` no lugar, apague `.next/`
(cache do Turbopack de uma execucao anterior).
