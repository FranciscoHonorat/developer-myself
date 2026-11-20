# Redesenho de UX/UI do frontend

Data: 2026-11-20 · Status: rascunho para aprovação

## Intenção e porquê

O Developer Myself vai ser mostrado a outros devs e, se pegar, vendido como SaaS (freemium).
O frontend é a vitrine: hoje funciona, mas parece projeto pessoal (uma aba "Trilha" que empilha
tudo, 6 abas que quebram no celular, emoji como marca, um único breakpoint). O objetivo é uma
cara **profissional e responsiva** que deixe o valor claro nos primeiros minutos.

O uso real (do primeiro usuário, o autor): **abrir → ver o que tem que fazer → clicar em Iniciar.**
Tudo gira em torno disso.

## Objetivos

- Tela inicial **Hoje** com o próximo passo e o botão Iniciar em destaque.
- **Gamificação em destaque** no Hoje (sequência, XP/nível, skills enferrujando): é diferencial de venda.
- Identidade **Dev / terminal**: escura por padrão, verde de ação, toques de fonte mono.
- Responsivo de **360 px a monitores largos**; navegação de app no celular.
- Primeira experiência guiada para quem acabou de se cadastrar.
- Visual consistente: componentes, espaçamentos, estados de carregando / vazio / erro.

## Não-objetivos (agora)

- Landing page de vendas, planos, pagamento, limites do plano grátis (próximo passo do caminho de venda).
- Mudar regras de negócio ou a API. O backend só muda se uma tela precisar de um dado que não existe
  (não previsto: streak em `/stats`, XP/nível/ferrugem em `/competencies`, fallback SPA já existe).
- Internacionalização (segue só pt-BR).

## Anti-objetivos (falharia mesmo funcionando)

- Esconder o botão Iniciar atrás de métricas ou de rolagem, em qualquer tamanho de tela.
- "Terminal" virar fantasia: texto longo em mono, contraste baixo, cansativo para escrever no Caderno.
- Gamificação poluir a tela a ponto de competir com o próximo passo.
- Quebrar as regras que a UI já garante (teste de memória sem consultar, uma sessão por vez).
- Ficar com dois sistemas visuais convivendo no fim (o `styles.css` antigo tem que sumir).

## Restrições

- React 19 + Vite + TypeScript + TanStack Query (mantidos). Biome para lint/format.
- Testes de componente (Vitest + Testing Library) e e2e (`playwright-bdd`, Gherkin pt) acham elementos
  por papel e nome acessível: **textos de botões/títulos usados nos testes mudam junto com os testes**,
  nunca silenciosamente.
- Acessibilidade: navegação por teclado, foco visível, contraste AA nos dois temas, `prefers-reduced-motion`.
- A paleta de dados já validada (`--series-*`, `--seq-*`, `--rust`) continua sendo a dos gráficos.
- Sem commits automáticos neste repositório (preferência do autor).

## Abordagens consideradas

1. **Migração em etapas (escolhida).** Tailwind v4 + shadcn/ui + lucide instalados ao lado do CSS atual;
   primeiro tema, casca e rotas; depois uma tela por vez; `styles.css` encolhe até sumir.
   Testes verdes a cada etapa, dá para usar no meio do caminho. Custo: fase com telas antigas dentro da casca nova.
2. **Reescrever tudo de uma vez.** Sem fase mista, mas sem feedback intermediário e testes vermelhos por muito tempo.
3. **CSS puro, sem libs.** Zero dependências, porém muito mais trabalho para o mesmo acabamento
   (diálogos, menus, acessibilidade). Descartada: o autor liberou bibliotecas.

Escolhida a 1 pelo autor.

## Decisões

### Pilha (decisão do Claude, autor liberou libs)
- **Tailwind CSS v4** (plugin do Vite), tema via variáveis CSS.
- **shadcn/ui** (Radix por baixo) para componentes: Button, Card, Dialog, DropdownMenu, Tabs, Progress,
  Tooltip, Toast (Sonner), Sheet, Badge, Skeleton, Textarea, Input, Select.
- **lucide-react** para ícones (substitui emojis da interface).
- **React Router** (modo declarativo) com uma URL por seção.
- Fontes: **Inter** (texto) e **JetBrains Mono** (rótulos, números, metadados), auto-hospedadas via `@fontsource`.

### Identidade visual: Dev / terminal
- Tema **escuro por padrão**; modo **claro** e **automático (sistema)** no menu da conta, lembrado no navegador.
- Fundo quase preto azulado, superfícies um tom acima, bordas finas; **verde (esmeralda) é a única cor de ação**.
  Âmbar = aviso, vermelho = erro/perigo. Modo claro: off-white com o mesmo verde (escurecido para contraste AA).
- **Mono só em rótulos curtos, números e metadados** (`d12/30`, `2×25m`, contadores, timer). Títulos, textos
  e editor do Caderno em Inter.
- Marca: wordmark `dev/myself` em mono com um cursor/acento verde; o nome completo "Developer Myself"
  aparece no título da página e na tela de login.

### Navegação e rotas
| Rota | Seção | Conteúdo |
|---|---|---|
| `/` → `/hoje` | **Hoje** | próximo passo, gamificação, resto do dia, semana |
| `/trilha` | **Trilha** | em andamento, para revisar, fila, adicionar conteúdo, desafios, cronograma |
| `/caderno` e `/caderno/:contentId` | **Caderno** | lista de matérias + editor |
| `/progresso` | **Progresso** | Competências (mapa, XP, ferrugem) + Histórico (estatísticas e sessões) |
| `/conta` | Conta | e-mail, fuso, preferências de estudo, tema, exportar/apagar conta, sair |
| `/entrar`, `/cadastro` | Auth | login e cadastro |

- **Desktop (≥ 1024 px):** menu lateral fixo com as 4 seções; Conta no rodapé do menu.
- **Tablet (640–1023 px):** menu lateral recolhido só com ícones.
- **Celular (< 640 px):** barra fixa embaixo com 4 ícones+rótulos; topo enxuto com a marca e o avatar (Conta).
- Rotas protegidas: sem sessão, vai para `/entrar` e volta para onde estava depois do login.

### Hoje
De cima para baixo:
1. Saudação + data (mono) e **faixa de gamificação em destaque**: sequência de dias (com chama quando ativa),
   nível geral e barra de XP, e um alerta de **skill enferrujando** quando houver (com link para Progresso).
2. **Cartão "Próximo passo"** (o maior elemento da tela): tipo (revisão/estudo), título, duração sugerida
   (`2×25m`), dia `d12/30`, foco do dia e o botão **Iniciar**. No celular o botão ocupa a largura toda.
   Se é preciso revisar antes de estudar, o próximo passo já é a revisão e uma linha explica por quê.
3. **Resto do dia**: lista dos blocos com estado (feito ✓, próximo, depois), cada um com Iniciar secundário.
   "Feito" sai dos dados existentes (`reviewed_today` do plano, `done` do `DayPlan`, sessão de hoje em
   `last_session_at`); se algum caso não for derivável sem API nova, ele fica sem ✓ em vez de mudar o backend
   (decisão do Claude).
4. **Semana**: faixa compacta de 7 dias (minutos por dia, folgas); "ver semana" expande a grade dia × competência
   e as preferências (minutos/dia, dias de folga).
5. Sugestão da IA (o que mais corre risco de esquecer), discreta, abaixo da semana.

Estado "tudo feito hoje": o cartão vira um resumo do dia com a sequência preservada e um convite para o Caderno.

### Sessão ativa
- Quando há sessão, **ela substitui o cartão Próximo passo** e domina o Hoje (e aparece como um indicador
  persistente no menu/barra em qualquer outra seção, com o tempo correndo, para voltar a ela com um toque).
- Timer grande em mono, horário de expiração, cancelar.
- **Revisão com teste de memória** em passos visíveis: 1 Responder (sem material) → 2 Conferir (Caderno e último
  "preciso revisar" aparecem; no desktop o Caderno abre ao lado, no celular em painel deslizante) → 3 Corrigir
  (Errei/Parcial/Acertei) → autoavaliação 1–4 → anotações → Finalizar.
- Estudo: anotações (estudei/entendi/preciso revisar) com contador dos 50 caracteres e Caderno ao lado.
- Resultado (pontuou ou não, e por quê; subiu de nível) num diálogo/toast com destaque de gamificação.
- A regra "caderno só pelo painel durante o teste" (já implementada) continua valendo.

### Trilha
Cartões de conteúdo redesenhados: status como badge, barra de progresso até o próximo nível (pontos e desafios),
ações principais visíveis (Iniciar/Revisar) e secundárias num menu "⋯" (renomear, cronograma, desafios, concluir,
remover). Seções: Em andamento (com vagas `1/3`), Para revisar, Fila (ordem e motivo do bloqueio).
Adicionar conteúdo vira um botão que abre um diálogo (título + tipo), não um formulário fixo na tela.

### Caderno
Duas colunas no desktop (matérias | editor), uma no celular (lista → editor com voltar). Editor ocupa a altura útil,
mostra estado de salvamento ("salvo às 14:02", "salvando…", conflito) e contador de caracteres.

### Progresso
Abas internas **Competências** e **Histórico**. Competências: nível geral e XP no topo, skills em cartões com nível
(Aprendiz → Especialista) e estado de ferrugem; meta do mapa. Histórico: números do topo (sessões, pontos, minutos,
sequência), gráfico diário, lista de sessões com filtros simples. Gráficos usam a paleta de dados já validada.

### Primeira vez (onboarding)
Detectado por trilha sem conteúdos. O Hoje mostra um guia de 2 passos no lugar do Próximo passo:
1. **Adicionar o primeiro conteúdo** (título + tipo).
2. **Quanto tempo por dia** (minutos/dia e dias de folga; padrão já sugerido).
Concluídos, aparece o Próximo passo com Iniciar. O guia pode ser pulado e volta a aparecer enquanto não houver conteúdo.

### Login e cadastro
Duas colunas no desktop: formulário (e-mail, senha, alternar entrar/cadastrar) e um painel com a proposta
(repetição espaçada, sessões de 25 min, IA que aprende com você) no estilo terminal. Celular: uma coluna, proposta
resumida acima do formulário.

### Estados e feedback (todas as telas)
Skeletons no carregamento, estados vazios com uma ação clara, erros com mensagem da API e "tentar de novo",
toasts para confirmações, diálogos de confirmação para ações destrutivas (substitui `window.confirm`).

## Plano de migração (forma, não tarefas)

Cada etapa termina com lint, tipos, Vitest e e2e verdes; textos que os testes usam são atualizados junto.
1. Fundação: dependências, tema (tokens escuro/claro), fontes, componentes base do shadcn, casca (menu/barra) e rotas,
   telas antigas renderizadas dentro da casca.
2. Hoje + sessão ativa + resultado.
3. Trilha.
4. Caderno.
5. Progresso.
6. Conta.
7. Login/cadastro e primeira vez.
8. Remover `styles.css` e restos; revisar acessibilidade e responsividade em 360/768/1280 px.

O e2e (`jornada.feature`) ganha um cenário no viewport de celular para a jornada principal.

## Deixado para quem constrói

- Valores exatos de cor (dentro da direção acima, validando contraste AA), espaçamentos e raios.
- Quais componentes shadcn entram em cada etapa, e a organização de pastas (`components/ui`, por seção).
- Microinterações e animações (respeitando `prefers-reduced-motion`).
- Ícone de cada seção e o desenho exato do wordmark.
- Detalhes do gráfico de histórico (tipo, eixos), seguindo a paleta e as regras de visualização já existentes.
