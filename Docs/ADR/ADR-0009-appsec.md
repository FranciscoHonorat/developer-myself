# ADR-0009: AppSec — modelo de ameaças e controles

**Status:** Proposto
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

O sistema guarda credenciais e **anotações pessoais**, que são dado pessoal pela LGPD. Ele também tem uma ameaça específica de domínio: **fraude de pontos**.

## Decisão

### Ameaças → controles

| Ameaça | Controle |
|---|---|
| **Fraude de pontos** (timer falso no cliente) | O servidor marca `started_at`/`finished_at`, o cliente só exibe. Uma sessão ativa por vez (I2). O tipo da sessão é derivado ([ADR-0002](ADR-0002-modelo-de-dominio.md)) |
| **Desafio "resolvido" sem resolver** | Hoje: evidência obrigatória e trilha auditável (`ChallengeSolved` imutável). O risco é aceito, porque o único prejudicado é o próprio aprendiz. Futuro: validação por ML ou LLM |
| **BOLA/IDOR** (OWASP API #1) | `learner_id` vem **só** da sessão autenticada, nunca do path ou do body. O repositório busca por `_id = learner_id` |
| **NoSQL injection** (`{"$ne": null}`) | DTOs Pydantic estritos na borda (`str` recusa `dict`). Nenhum dado de request vira filtro diretamente |
| Roubo de sessão / XSS | Cookie de sessão **opaco**, `HttpOnly; Secure; SameSite=Strict`, guardado em `auth_sessions` com TTL (revogável). O React escapa por padrão. Proibido usar `dangerouslySetInnerHTML`. Se as anotações virarem Markdown, passam por DOMPurify |
| CSRF | `SameSite=Strict` + exigência de cabeçalho `X-Requested-With` em métodos que alteram estado |
| Credential stuffing | Senhas com **Argon2id** (`argon2-cffi`), rate limit no login, mensagem genérica que não confirma se o usuário existe |
| Segredos vazados | Configuração por env (`pydantic-settings`), gitleaks no pre-commit e no CI |
| Supply chain | Lock com hashes, `pip-audit` + `npm audit` no CI, Renovate, imagem com digest fixo e scan com Trivy |
| Infra | Mongo e Rabbit com autenticação, usuário com privilégio mínimo (`readWrite` só no db da app), TLS em produção, container sem root |
| Vazamento em log | Logs estruturados **sem** conteúdo de anotações nem tokens |

### Por que não JWT nem OAuth 2.0 agora

O ADR-0001 cita "Auth2.0". O OAuth 2.0 é um protocolo de **delegação** e não resolve login próprio. Para uma SPA servida no mesmo domínio da API, um cookie de sessão opaco é mais simples e revogável na hora, sem a complexidade de rotacionar refresh tokens. Login social entra depois via **OIDC**, como mais um adapter de `identity`.

### LGPD

Exportar e excluir conta (os eventos do aprendiz incluídos). Para o ML, usar dados **pseudonimizados** e com consentimento explícito ([ADR-0012](ADR-0012-dados-para-ml.md)).

## Consequências

- ✅ A fraude de pontos é tratada no domínio, não em controles espalhados.
- ⚠️ O cookie `SameSite=Strict` exige frontend e API na **mesma origem** (proxy do Vite em dev, reverse proxy em produção).
- 🔁 Fazer revisão contra o OWASP ASVS nível 1 antes do primeiro deploy público.
