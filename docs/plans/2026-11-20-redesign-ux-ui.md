# Redesenho de UX/UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar a interface do frontend por uma casca de app profissional (identidade Dev/terminal, 4 seções com rotas, responsiva 360 px→desktop), tela a tela, sem mudar a API.

**Architecture:** Migração em etapas: Tailwind v4 + shadcn/ui convivem com o `styles.css` até a última tarefa. Primeiro tema, casca e rotas (telas antigas dentro); depois cada seção vira uma página em `src/pages/`, com peças em `src/features/<seção>/`. Lógica de decisão (próximo passo, estado do dia, onboarding) fica em funções puras testadas; componentes só exibem.

**Tech Stack:** React 19, Vite 8, TypeScript, TanStack Query 5, Tailwind CSS 4.3.5 (`@tailwindcss/vite`), shadcn 4.23 (CLI) + radix-ui 1.8.1, react-router 8.5.2, lucide-react 1.77.0, sonner 2.0.8, `@fontsource-variable/inter` 5.3.0 e `@fontsource-variable/jetbrains-mono` 5.3.0, class-variance-authority, clsx, tailwind-merge, tw-animate-css. Testes: Vitest + Testing Library, playwright-bdd.

**Spec:** `docs/specs/2026-11-20-redesign-ux-ui-design.md`

## Global Constraints

- **Não commitar** neste repositório (preferência do autor): onde o fluxo diria "commit", rodar as verificações e seguir.
- Toda tarefa termina com `cd frontend && npm run lint && npm run typecheck && npm test` verdes; tarefas que mexem em texto/rota usado pelo e2e também rodam `make e2e` (na raiz) verde.
- Textos usados por testes mudam **junto** com os testes, na mesma tarefa.
- Só pt-BR. Sem mudanças no backend.
- Tema escuro por padrão; opções `"dark" | "light" | "system"`, salvas em `localStorage["dm-theme"]` com try/catch (falha → escuro).
- Verde (esmeralda) é a única cor de ação; âmbar = aviso; vermelho = erro. Contraste AA nos dois temas.
- Mono (`font-mono`, JetBrains Mono) **só** em rótulos curtos, números, metadados e timer; texto e editor em Inter (`font-sans`).
- Paleta de dados existente (`--series-1..6`, `--seq-fill`, `--seq-track`, `--rust`) preservada com os mesmos valores para gráficos.
- Rotas: `/hoje` (índice `/` redireciona), `/trilha`, `/caderno`, `/caderno/:contentId`, `/progresso` (abas `?aba=competencias|historico`), `/conta`, `/entrar`, `/cadastro`.
- Breakpoints: celular `< 640px` (barra inferior), tablet `640–1023px` (menu só ícones), desktop `≥ 1024px` (menu completo).
- Nome acessível da navegação principal: `aria-label="Seções"` (menu lateral e barra inferior são o mesmo `<nav>` com layout responsivo — não duplicar).
- `prefers-reduced-motion`: sem animações de entrada quando ativo (usar variantes `motion-safe:` do Tailwind).
- Remover `window.confirm` e emojis da interface (exceto 🔥 da sequência, que é conteúdo).

## Review Focus

1. **Recarregar (F5) numa rota profunda** (`/caderno/<id>`, `/progresso?aba=historico`) logado → abre a mesma tela; deslogado → `/entrar` e, após login, volta para a rota pedida. Teste no Task 2.
2. **Sessão ativa iniciada em outra aba/aparelho** enquanto o usuário está em `/trilha` → indicador da sessão aparece no menu e leva ao Hoje com o painel. Teste no Task 2.
3. **Dia com revisão obrigatória pendente** → o próximo passo é a revisão, nunca um estudo, mesmo que o estudo venha antes na lista. Teste no Task 3.
4. **Celular 360 px**: botão Iniciar visível sem rolagem horizontal, barra inferior não cobre o botão Finalizar da sessão (padding inferior do conteúdo = altura da barra + safe-area). Cenário e2e no Task 9.
5. **Tema salvo inválido ou storage bloqueado** → app abre no escuro sem erro. Teste no Task 1.

---

## File Structure

```
frontend/
  components.json                    # config do shadcn (Task 1)
  src/
    index.css                        # Tailwind + tokens de tema + fontes (Task 1)
    lib/utils.ts                     # cn() (Task 1)
    lib/theme.ts                     # tema: ler/salvar/aplicar (Task 1)
    components/ui/*                  # gerados pelo shadcn (Task 1, +conforme precisar)
    app/router.tsx                   # rotas (Task 2)
    app/AppShell.tsx                 # casca: nav + conteúdo (Task 2)
    app/MainNav.tsx                  # nav responsiva "Seções" (Task 2)
    app/SessionIndicator.tsx         # sessão em andamento no nav (Task 2)
    app/RequireAuth.tsx              # guarda de rota (Task 2)
    app/Brand.tsx                    # wordmark dev/myself (Task 2)
    features/today/day.ts            # dayItems/nextStep (puro) (Task 3)
    features/today/*.tsx             # GamificationStrip, NextStepCard, DayList, WeekStrip (Task 3)
    features/session/*.tsx           # painel da sessão, passos do teste, resultado (Task 4)
    features/trail/*.tsx             # ContentCard, AddContentDialog, ContentActions (Task 5)
    features/notebook/*.tsx          # editor/lista (Task 6)
    features/progress/*.tsx          # competências/histórico (Task 7)
    features/onboarding/*.tsx        # guia de primeira vez (Task 8)
    pages/{Today,Trail,Notebook,Progress,Account,Auth}Page.tsx
    components/*                     # antigos: movidos/removidos à medida que cada página assume
    styles.css                       # removido no Task 9
```

Componentes antigos que já têm testes (ex.: `ActiveSessionPanel`, `RecallTest`, `NotebookEditor`, `ContentCard`) são **movidos** para `features/<seção>/` com os testes e reestilizados — não reescritos do zero — para preservar comportamento já testado.

---

### Task 1: Fundação — Tailwind, tema, fontes, shadcn

**Files:**
- Modify: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/main.tsx`, `frontend/index.html`
- Create: `frontend/components.json`, `frontend/src/index.css`, `frontend/src/lib/utils.ts`, `frontend/src/lib/theme.ts`, `frontend/src/components/ui/*`
- Test: `frontend/src/lib/theme.test.ts`

**Interfaces:**
- Produces: `cn(...inputs: ClassValue[]): string`; `type ThemeChoice = "dark" | "light" | "system"`; `readTheme(): ThemeChoice`; `saveTheme(t: ThemeChoice): void`; `applyTheme(t: ThemeChoice): void` (põe/tira a classe `dark` em `<html>`; `system` segue `matchMedia("(prefers-color-scheme: dark)")`); componentes shadcn em `@/components/ui/<nome>`; alias `@/` → `src/`.

- [ ] **Step 1: Instalar dependências** (versões exatas do Tech Stack): `npm i tailwindcss@4.3.5 @tailwindcss/vite@4.3.5 react-router@8.5.2 lucide-react@1.77.0 sonner@2.0.8 radix-ui@1.8.1 @fontsource-variable/inter@5.3.0 @fontsource-variable/jetbrains-mono@5.3.0 class-variance-authority@0.7.1 clsx@2.1.1 tailwind-merge@3.7.1 tw-animate-css@1.4.0`.
- [ ] **Step 2: Configurar** plugin `tailwindcss()` no `vite.config.ts`, alias `@` → `./src` (Vite `resolve.alias` e `paths` no tsconfig com `baseUrl: "."`), `components.json` do shadcn (style `new-york`, `tsx: true`, `cssVariables: true`, `iconLibrary: "lucide"`, aliases `@/components`, `@/lib/utils`, `@/components/ui`).
- [ ] **Step 3: Escrever `src/index.css`**: `@import "tailwindcss"; @import "tw-animate-css";`, fontes `@fontsource-variable/*`, `@custom-variant dark (&:is(.dark *));`, tokens shadcn (`--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--primary-foreground`, `--secondary`, `--muted`, `--muted-foreground`, `--accent`, `--destructive`, `--border`, `--input`, `--ring`, `--radius: 0.625rem`, `--warning`, `--success`) em `:root` (claro: fundo off-white, primário esmeralda escurecido) e `.dark` (fundo `#0b0d12`, superfície `#11141b`, borda `#232733`, primário `#34d399`, texto do primário `#06281b`), mapeados em `@theme inline`; `--font-sans: "Inter Variable", system-ui, sans-serif; --font-mono: "JetBrains Mono Variable", ui-monospace, monospace;`; copiar os tokens de dados (`--series-*`, `--seq-*`, `--rust`) do `styles.css` com os mesmos valores. Importar `index.css` **antes** de `styles.css` no `main.tsx`.
- [ ] **Step 4: Gerar componentes base** com `npx shadcn@4.23.0 add button card badge progress dialog alert-dialog dropdown-menu sheet tabs skeleton sonner tooltip input textarea label select separator` e rodar `npm run fmt`. Biome pode reclamar de código gerado: ajustar só o que o lint exigir.
- [ ] **Step 5: Teste que falha** em `src/lib/theme.test.ts`:

```ts
it("sem nada salvo, o tema é escuro", () => { localStorage.clear(); expect(readTheme()).toBe("dark"); });
it("valor salvo inválido cai no escuro", () => { localStorage.setItem("dm-theme", "roxo"); expect(readTheme()).toBe("dark"); });
it("storage bloqueado cai no escuro", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("bloqueado"); });
  expect(readTheme()).toBe("dark");
});
it("salva e relê a escolha", () => { saveTheme("light"); expect(readTheme()).toBe("light"); });
it("applyTheme('dark') põe a classe dark no html; 'light' tira", () => {
  applyTheme("dark"); expect(document.documentElement.classList.contains("dark")).toBe(true);
  applyTheme("light"); expect(document.documentElement.classList.contains("dark")).toBe(false);
});
```

- [ ] **Step 6: Rodar** `npx vitest run src/lib/theme.test.ts` → FAIL (módulo não existe).
- [ ] **Step 7: Implementar `src/lib/theme.ts` e `src/lib/utils.ts`** (`cn = twMerge(clsx(...))`). No `main.tsx`, `applyTheme(readTheme())` antes do `render` e `<Toaster />` (sonner) dentro do provider. No `index.html`: `<meta name="color-scheme" content="dark light">`, `<html lang="pt-BR" class="dark">` (evita flash), favicon SVG com `>_` verde em vez do emoji.
- [ ] **Step 8: Verificar** `npm run lint && npm run typecheck && npm test && npm run build` verdes; app antigo abre igual (o Tailwind preflight pode mudar margens: aceitável, nenhum teste quebra).

---

### Task 2: Casca, navegação e rotas

**Files:**
- Create: `src/app/router.tsx`, `src/app/AppShell.tsx`, `src/app/MainNav.tsx`, `src/app/SessionIndicator.tsx`, `src/app/RequireAuth.tsx`, `src/app/Brand.tsx`, `src/pages/AccountPage.tsx` (temporário: renderiza `SettingsView` + botão Sair)
- Modify: `src/App.tsx` (vira `<RouterProvider router={router} />`), `src/components/AuthScreen.tsx` (após login navega para `state.from ?? "/hoje"`), `e2e/steps/jornada.steps.ts`
- Test: `src/app/router.test.tsx`

**Interfaces:**
- Consumes: `cn`, `Button`, `Tooltip`, `useMe`, `usePlan`.
- Produces: `createAppRouter(opts?: { initialEntries?: string[] })` (memory router nos testes, browser router no app); `<AppShell>` com `<Outlet/>`; `SECTIONS: { to: string; label: "Hoje" | "Trilha" | "Caderno" | "Progresso"; icon: LucideIcon }[]`; rota de cada seção monta, por enquanto, a view antiga: `/hoje` → `PlanView`, `/trilha` → `PlanView`, `/caderno` → `NotebookView`, `/progresso` → `CompetenciesView` + `HistoryView` (abas por `?aba=`), `/conta` → `AccountPage`; `/entrar` e `/cadastro` → `AuthScreen` (modo pelo path). A Semana (`WeekView`) fica temporariamente sob `/hoje` abaixo do `PlanView`.

- [ ] **Step 1: Testes que falham** em `src/app/router.test.tsx` (com `routeFetch`):
  - `"/" logado redireciona para /hoje e marca Hoje como atual"` → link `Hoje` em `navigation "Seções"` tem `aria-current="page"`.
  - `"deslogado em /caderno/c1 vai para /entrar e volta para /caderno/c1 após login"` (`/me` 401 → tela de login; após POST login ok, rota atual `/caderno/c1`).
  - `"F5 em /progresso?aba=historico abre o histórico"`.
  - `"com sessão ativa, fora do Hoje, o indicador mostra o título e leva ao Hoje"`: `/plan` com `active_session` → em `/trilha`, link `Sessão em andamento: Clean Code` presente; clicar → rota `/hoje`.
  - `"a navegação tem as 4 seções e a conta"`: links `Hoje`, `Trilha`, `Caderno`, `Progresso`, `Conta`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `MainNav`: um único `<nav aria-label="Seções">` com `NavLink`s; classes: `fixed inset-x-0 bottom-0 h-16` no celular (pb `env(safe-area-inset-bottom)`), `sm:static sm:w-16 sm:h-dvh` (só ícones, rótulo em `Tooltip` e `sr-only`), `lg:w-60` (ícone + rótulo). Ícones: Hoje `Sun`, Trilha `Route`, Caderno `NotebookPen`, Progresso `TrendingUp`, Conta `CircleUser`. `AppShell`: nav + `<main className="pb-20 sm:pb-0">` com largura máxima `max-w-5xl` e gutter `px-4`. `SessionIndicator`: lê `usePlan().data?.active_session`; se houver e a rota não for `/hoje`, mostra `Link` com `aria-label={"Sessão em andamento: " + title}` e o tempo decorrido (mono). `Brand`: `dev/myself` em `font-mono` com cursor verde (`▍` animado com `motion-safe:animate-pulse`). `RequireAuth`: `useMe` pendente → skeleton; erro → `<Navigate to="/entrar" state={{ from: location }} replace />`.
- [ ] **Step 4: Atualizar e2e** (`jornada.steps.ts`): cadastro passa a ir por `/cadastro` ou pelo link de alternar; "abro … na aba Caderno" usa `getByRole("navigation", { name: "Seções" }).getByRole("link", { name: "Caderno" })`; "aparece no histórico" navega por link `Progresso` e depois aba `Histórico`.
- [ ] **Step 5: Verificar** testes Vitest verdes, `npm run build`, `make e2e` verde.

---

### Task 3: Página Hoje

**Files:**
- Create: `src/features/today/day.ts`, `src/features/today/day.test.ts`, `src/features/today/GamificationStrip.tsx`, `src/features/today/NextStepCard.tsx`, `src/features/today/DayList.tsx`, `src/features/today/WeekStrip.tsx`, `src/pages/TodayPage.tsx`, `src/pages/TodayPage.test.tsx`
- Move: `src/components/WeekView.tsx` (+teste) → `src/features/today/WeekDetails.tsx` (grade + preferências, aberto por "Ver semana"); `ReviewSuggestion` → `src/features/today/`
- Modify: `src/app/router.tsx` (`/hoje` → `TodayPage`)

**Interfaces:**
- Consumes: `useToday`, `usePlan`, `useStats`, `useCompetencies`, `useWeek`, `useStartSession`.
- Produces:
  - `type DayItemState = "done" | "next" | "later"`
  - `interface DayItem { contentId: string; title: string; kind: "REVIEW" | "STUDY"; day: number; totalDays: number; focus: string; pomodoros: number; minutes: number; state: DayItemState }`
  - `dayItems(today: Today, plan: Plan, localDate: string): DayItem[]` — revisões antes de estudos; `done` quando o conteúdo tem `last_session_at` na `localDate` (no fuso `plan.timezone`) ou, para revisão, `plan.reviewed_today`; o primeiro não-feito é `next`, os demais `later`; pomodoros/minutos vêm do `blocks` do mesmo `content_id` (0 se não houver).
  - `nextStep(items: DayItem[]): DayItem | null` — o item `next`.

- [ ] **Step 1: Testes puros que falham** (`day.test.ts`):
  - `"revisões vêm antes dos estudos"`.
  - `"com revisão pendente, o próximo passo é a revisão mesmo com estudo listado"` (Review Focus 3).
  - `"conteúdo com sessão hoje fica feito e o próximo passa ao seguinte"`.
  - `"revisão conta como feita quando reviewed_today"`.
  - `"tudo feito → nextStep null"`.
  - `"last_session_at de ontem no fuso do plano não conta como hoje"` (ex.: `2026-11-20T02:30:00Z` em `America/Sao_Paulo` é dia 19).
- [ ] **Step 2: Rodar** → FAIL. **Step 3: Implementar** `day.ts` (data local via `Intl.DateTimeFormat("en-CA", { timeZone })`). **Step 4:** PASS.
- [ ] **Step 5: Testes de página que falham** (`TodayPage.test.tsx`):
  - `"mostra a sequência, o nível e o XP em destaque"`: `/stats` `current_streak_days: 6`, `/competencies` `level: 4, xp: 620, next_level_xp: 1000` → textos `6 dias seguidos`, `Nível 4`, `progressbar` com `aria-valuenow={62}`.
  - `"alerta de skill enferrujando leva ao Progresso"`: competência `status: "enferrujando"` → link `Go está enferrujando` para `/progresso?aba=competencias`.
  - `"cartão Próximo passo tem o título e o botão Iniciar revisão"`; clicar chama `POST /contents/<id>/sessions` (o mesmo endpoint de `useStartSession`).
  - `"com sessão ativa o cartão dá lugar ao painel da sessão"` (heading `Revisão: Clean Code` presente, botão `Iniciar revisão` ausente).
  - `"dia concluído mostra o resumo e mantém a sequência"`: texto `Dia concluído`.
  - `"Ver semana abre a grade e as preferências"` (reaproveita asserções do antigo `WeekView.test`).
- [ ] **Step 6: Implementar** componentes e `TodayPage` na ordem do spec (saudação/data mono → `GamificationStrip` → `NextStepCard` ou painel de sessão → `DayList` → `WeekStrip` + `WeekDetails` em `Collapsible`/`Sheet` → `ReviewSuggestion`). Botão Iniciar: `w-full sm:w-auto`, rótulo `Iniciar revisão` / `Iniciar estudo`. Se `plan.needs_review_today`, linha explicativa: "Revise antes de estudar: sem a revisão do dia, o estudo não pontua." Skeletons enquanto carrega; erro com `ErrorState` (mensagem + "Tentar de novo" → `refetch`). Crie `src/components/ErrorState.tsx` aqui (substitui `ErrorText` nas páginas novas).
- [ ] **Step 7: Atualizar e2e** se algum passo dependia de `TodayCard`/banners antigos; remover `TodayCard`, `DayPlanView` e seus testes quando nada mais os importar.
- [ ] **Step 8: Verificar** lint/tipos/Vitest/e2e verdes.

---

### Task 4: Sessão ativa e resultado

**Files:**
- Move + restyle: `src/components/ActiveSessionPanel.tsx` (+teste) → `src/features/session/SessionPanel.tsx`; `RecallTest.tsx` (+teste) → `src/features/session/RecallTest.tsx`; `OutcomeBanner.tsx` (+teste) → `src/features/session/OutcomeDialog.tsx`
- Create: `src/features/session/SessionTimer.tsx`, `src/features/session/RecallSteps.tsx`
- Modify: `src/pages/TodayPage.tsx`

**Interfaces:**
- Consumes: `recallTestOn` (`src/api/recall.ts`), `NotebookEditor`, `useFinishSession`, `useCancelSession`.
- Produces: `<SessionPanel session serverTime onFinished />` (mesmas props e a mesma `key` por `started_at` já existente); `<OutcomeDialog outcome open onOpenChange />`; `<RecallSteps current: 1 | 2 | 3 />` (indicador "1 Responder · 2 Conferir · 3 Corrigir", `aria-current="step"`).

- [ ] **Step 1: Ajustar testes existentes** aos novos textos e adicionar:
  - `"mostra os passos e marca Responder como atual"` → depois de `Conferir respostas`, passo 2 atual.
  - `"timer usa role timer e mostra a expiração"` (mantém `role="timer"` usado pelo e2e).
  - `"no celular o caderno abre em painel deslizante só depois de conferir"`: com `matchMedia` < 640 mockado, botão `Abrir caderno` só aparece após conferir; abre `dialog` com o caderno.
  - `OutcomeDialog`: `"sessão sem ponto mostra o motivo"` (mantém `Sessão sem ponto.` e `/pelo menos 25 minutos/` do e2e) e `"subir de nível destaca o novo nível"`.
  - `"cancelar pede confirmação em diálogo"` (AlertDialog, sem `window.confirm`).
- [ ] **Step 2: Rodar** → FAIL. **Step 3: Implementar** layout: desktop `lg:grid-cols-[1fr_minmax(0,28rem)]` (sessão | caderno ao lado quando liberado), celular coluna única com caderno em `Sheet side="bottom"`; timer `font-mono text-5xl tabular-nums`; contador de 50 caracteres por campo de anotação (`aria-live="polite"`); rótulos `O que estudei`, `O que entendi`, `O que preciso revisar` e botão `Finalizar sessão` inalterados (e2e). Resultado em `OutcomeDialog` + `toast.success` quando pontuar.
- [ ] **Step 4: Verificar** lint/tipos/Vitest/e2e verdes.

---

### Task 5: Página Trilha

**Files:**
- Move + restyle: `ContentCard` (+teste), `ChallengeList`, `ScheduleView` → `src/features/trail/`
- Create: `src/features/trail/AddContentDialog.tsx`, `src/features/trail/ContentActions.tsx`, `src/components/ConfirmDialog.tsx`, `src/pages/TrailPage.tsx`, `src/pages/TrailPage.test.tsx`
- Delete: `src/components/AddContentForm.tsx`, `src/components/PlanView.tsx` (quando `/trilha` e `/hoje` não os usarem mais)

**Interfaces:**
- Produces: `<ConfirmDialog title description confirmLabel destructive? onConfirm>{trigger}</ConfirmDialog>` (usado também no Task 4 e 7); `<ContentActions content notebookLocked />` (menu "⋯" com Renomear, Cronograma, Desafios, Caderno → link `/caderno/<id>`, Concluir, Remover); `<AddContentDialog />` (botão `Adicionar conteúdo` abre diálogo com `Título` e `Tipo`, submit `Adicionar`).

- [ ] **Step 1: Testes que falham** (`TrailPage.test.tsx` + ajustes no `ContentCard.test`):
  - `"seções Em andamento (com vagas), Para revisar e Fila"` → heading `Em andamento` e texto mono `1/3 vagas`.
  - `"Adicionar conteúdo abre diálogo e cria"` → POST `/contents` com `{ title, kind }`.
  - `"conteúdo bloqueado mostra o motivo e não tem Iniciar"` (texto `conclua Clean Code ou chegue a Intermediário` preservado).
  - `"Remover pede confirmação"`; `"Concluir desabilitado abaixo de Avançado com dica"`.
  - `"durante teste de memória o menu não oferece Caderno"` (mantém o comportamento do `notebookLocked`).
  - Card é `article` com nome acessível = título (e2e usa `getByRole("article", { name })`).
- [ ] **Step 2: Rodar** → FAIL. **Step 3: Implementar**: card com `Badge` de status, `Progress` até o próximo nível (pontos e desafios, números mono), ação principal visível (`Estudar`/`Revisar`), resto em `ContentActions`. Grid `grid-cols-1 md:grid-cols-2`.
- [ ] **Step 4: Atualizar e2e**: "adiciono o conteúdo" vai a `/trilha`, clica `Adicionar conteúdo`, preenche `Título`, clica `Adicionar`; "inicio uma sessão de estudo" clica `Estudar` no card e espera heading `Estudo: <título>` (o painel aparece no Hoje: navegar ou o próprio clique redireciona para `/hoje` — **decisão: iniciar uma sessão sempre navega para `/hoje`**).
- [ ] **Step 5: Verificar** lint/tipos/Vitest/e2e verdes.

---

### Task 6: Página Caderno

**Files:**
- Move + restyle: `NotebookView` (+teste) → `src/pages/NotebookPage.tsx`; `NotebookEditor` (+teste) → `src/features/notebook/NotebookEditor.tsx`
- Modify: `src/app/router.tsx`, `e2e/steps/jornada.steps.ts`

**Interfaces:**
- Consumes: `useParams<{ contentId?: string }>()`; `recallTestOn`.
- Produces: seleção de matéria = rota `/caderno/:contentId` (não mais `useState`).

- [ ] **Step 1: Testes que falham**: `"clicar numa matéria vai para /caderno/<id> e abre o editor"`; `"no celular, com matéria aberta, a lista some e há Voltar"` (`matchMedia` < 640); `"estado de salvamento: Salvando…, Salvo às HH:MM, conflito"` (o e2e procura `status` com `Salvo` — **atualizar o e2e para `/Salvo/`**); bloqueio do teste de memória preservado.
- [ ] **Step 2: Rodar** → FAIL. **Step 3: Implementar**: `lg:grid-cols-[18rem_1fr]`; editor `min-h-[60dvh]` em Inter, contador de caracteres mono; o rótulo acessível do editor passa de `📓 Caderno de X` para `Caderno de X` (atualizar testes e e2e juntos).
- [ ] **Step 4: Verificar** lint/tipos/Vitest/e2e verdes.

---

### Task 7: Páginas Progresso e Conta

**Files:**
- Move + restyle: `CompetenciesView` (+teste) → `src/features/progress/Competencies.tsx`; `HistoryView` (+teste) → `src/features/progress/History.tsx`; `SettingsView` → `src/pages/AccountPage.tsx`
- Create: `src/pages/ProgressPage.tsx`, `src/features/account/ThemeSelect.tsx`

**Interfaces:**
- Consumes: `readTheme/saveTheme/applyTheme`, `ConfirmDialog`, `Tabs`.
- Produces: `ProgressPage` com `Tabs` sincronizadas a `?aba=competencias|historico` (padrão `competencias`).

- [ ] **Step 1: Testes que falham**: `"aba vem da URL e trocar de aba atualiza a URL"`; `"topo do histórico mostra sessões, pontos, minutos e sequência"`; `"ThemeSelect troca e salva o tema"` (classe `dark` some ao escolher Claro; `localStorage["dm-theme"] === "light"`); `"apagar conta pede confirmação em diálogo"`; asserções antigas de Competências/Histórico adaptadas.
- [ ] **Step 2: Rodar** → FAIL. **Step 3: Implementar**: Competências com cartão de nível geral/XP no topo e skills em cartões (`status` → `Badge`: em dia = verde, enferruja em breve = âmbar, enferrujando = `--rust`); gráfico diário do Histórico com `--series-1`/`--seq-*` (segue as regras de dados já usadas). Conta: e-mail, fuso, preferências (minutos/dia, folgas — os mesmos endpoints do antigo `PreferencesForm`), Tema, Exportar, Apagar conta, Sair.
- [ ] **Step 4: Verificar** lint/tipos/Vitest/e2e verdes.

---

### Task 8: Login, cadastro e primeira vez

**Files:**
- Move + restyle: `AuthScreen` → `src/pages/AuthPage.tsx` (+ novo teste)
- Create: `src/features/onboarding/needsOnboarding.ts` (+teste), `src/features/onboarding/OnboardingGuide.tsx`
- Modify: `src/pages/TodayPage.tsx`, `e2e/steps/jornada.steps.ts`

**Interfaces:**
- Produces: `needsOnboarding(plan: Plan): boolean` (= `plan.contents.length === 0`); `<OnboardingGuide />` com passo 1 `Adicione seu primeiro conteúdo` (reusa `AddContentDialog` em modo inline) e passo 2 `Quanto tempo por dia?` (minutos/dia e folgas, padrão vindo de `plan.preferences`), botão `Pular`.

- [ ] **Step 1: Testes que falham**: `needsOnboarding` (vazio → true; com conteúdo → false); `"trilha vazia mostra o guia no lugar do Próximo passo"`; `"concluir os 2 passos mostra o Próximo passo com Iniciar"`; `"Pular esconde o guia nesta visita"` (estado local; volta ao recarregar enquanto vazio); Auth: `"/cadastro mostra Criar conta e o painel do método"`, `"erro de credencial aparece no formulário"`.
- [ ] **Step 2: Rodar** → FAIL. **Step 3: Implementar**: Auth `lg:grid-cols-2` (formulário | painel com wordmark e 3 linhas do método em estilo terminal); celular coluna única com proposta resumida acima. Rótulos `E-mail`, `Senha`, botões `Criar conta`/`Entrar` preservados; alternar vira link para `/entrar`/`/cadastro` (atualizar o passo `Dado que eu criei uma conta nova` do e2e para ir direto a `/cadastro` e esperar o guia `Adicione seu primeiro conteúdo`).
- [ ] **Step 4: Verificar** lint/tipos/Vitest/e2e verdes.

---

### Task 9: Limpeza, acessibilidade e celular

**Files:**
- Delete: `src/styles.css` e componentes antigos sem uso (`ErrorText`, `TodayCard`, `DayPlanView`, `OutcomeBanner`… o que sobrar)
- Modify: `src/main.tsx`, `playwright.config.ts`, `e2e/features/jornada.feature`, `e2e/steps/jornada.steps.ts`

- [ ] **Step 1: Cenário e2e que falha** em `jornada.feature`, projeto Playwright `mobile` (`devices["Pixel 7"]`, só cenários com tag `@celular`):

```gherkin
@celular
Cenário: A jornada principal funciona no celular
  Quando eu adiciono o conteúdo "Clean Code"
  E eu inicio uma sessão de estudo em "Clean Code"
  Então o botão "Finalizar sessão" fica visível acima da barra de navegação
  E a página não rola na horizontal
```

  Passos: `boundingBox` do botão (após `scrollIntoViewIfNeeded`) termina acima do topo do `navigation "Seções"`; `document.documentElement.scrollWidth <= window.innerWidth`.
- [ ] **Step 2: Rodar** `make e2e` → FAIL se houver sobreposição/rolagem; corrigir o layout.
- [ ] **Step 3: Remover** `styles.css` e o import; `grep -rn "className=\"\(card\|stack\|row\|muted\|banner\|pill\)" src` deve vir vazio.
- [ ] **Step 4: Passada de acessibilidade**: todo botão só-ícone tem `aria-label`; foco visível (`ring`) em links/botões; contraste AA conferido nos tokens dos dois temas (anotar os pares no topo de `index.css`).
- [ ] **Step 5: Verificar** `make check` e `make e2e` verdes; `npm run build` sem avisos novos; conferir visualmente em 360, 768 e 1280 px nos dois temas (com `make up` ou `npm run dev`).
