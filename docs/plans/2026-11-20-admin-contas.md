# Perfil de admin — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans, tarefa por tarefa. Passos com checkbox (`- [ ]`).

**Objetivo:** área `/admin` para o dono listar contas, excluir contas e abrir/fechar o cadastro.

**Arquitetura:** o contexto `identity` ganha o conceito de admin (e-mails do ambiente), a
"porta" do cadastro e a listagem paginada de usuários. Uma rota de composição
(`admin_routes.py`, como `account_routes.py`) junta identity + learning + insights só por IDs.
Frontend: página `/admin` com TanStack Query.

**Stack:** FastAPI, pymongo async, pytest-bdd (Gherkin pt), React + TanStack Query + Vitest.

**Spec:** `docs/specs/2026-11-20-admin-contas-design.md`

## Restrições globais
- Admin = e-mail em `DM_ADMIN_EMAILS` (separado por vírgula, normalizado como `Email`: trim + minúsculas). Nada no banco.
- Admin vê só contagens: nunca anotações, caderno ou histórico de outra pessoa.
- Cadastro fechado: `POST /api/auth/register` → 403 `REGISTRATION_CLOSED`, exceto e-mails admin.
- Admin não exclui a si mesmo pela área admin → 409 `CANNOT_DELETE_SELF`.
- Não admin em `/api/admin/*` → 403 `FORBIDDEN`; sem login → 401.
- Listagem: 20 por página, `{items, next_cursor}`, keyset por (`created_at` desc, `id` desc), cursor inválido → 422 `INVALID_CURSOR`.
- Log de auditoria `admin_deleted_account` com `admin_id` e `account_id`, **sem e-mail**.
- Estado do cadastro persistido (Mongo `app_settings`, `_id: "registration"`), padrão aberto.
- **Sem commits** até o usuário pedir (preferência do projeto). Os passos "Verificar" substituem os commits.
- Domínio/aplicação não importam adapters nem frameworks (`tests/architecture`).

## Foco da revisão
1. `DM_ADMIN_EMAILS` vazio ou com espaços/maiúsculas (`" Eu@X.com ,"`) → ninguém vira admin por engano; `eu@x.com` vira admin. Teste na Tarefa 1.
2. Excluir conta que já não existe (duas abas) → 404, sem 500. Teste na Tarefa 2.
3. Admin perde o status (variável mudou) com a página aberta → próximas chamadas 403 e o frontend mostra o erro. Teste HTTP na Tarefa 3.
4. Conta sem trilha (cadastro interrompido) na listagem → `contents: 0`, sem 500. Teste na Tarefa 3.
5. Fechar o cadastro e reiniciar o serviço → continua fechado (Mongo). Teste de contrato na Tarefa 1.

---

### Tarefa 1: Admin pelo ambiente e porta do cadastro (backend, identity)

**Arquivos:**
- Modificar: `backend/src/developer_myself/shared/settings.py` (`admin_emails: str = ""`)
- Modificar: `backend/src/developer_myself/identity/domain/model.py` (erros novos)
- Modificar: `backend/src/developer_myself/identity/application/ports.py` (`RegistrationGate`)
- Modificar: `backend/src/developer_myself/identity/application/use_cases.py`
- Criar: memória em `identity/adapters/memory/repositories.py` (`InMemoryRegistrationGate`); Mongo em `identity/adapters/mongo/repositories.py` (`MongoRegistrationGate(collection)`)
- Modificar: `shared/adapters/mongo_setup.py` (coleção `app_settings`, schema `{"bsonType": "object"}`), `bootstrap.py` e `mongo_bootstrap.py` (injeção)
- Testes: `backend/tests/features/admin.feature` + `test_admin.py`; `backend/tests/integration/test_registration_gate_contract.py`

**Interfaces:**
- Produz:
  - `parse_admin_emails(raw: str) -> frozenset[Email]` (domínio; ignora itens vazios, e-mail inválido levanta `InvalidEmailError` no boot)
  - Erros: `RegistrationClosedError`, `NotAdminError`, `CannotDeleteSelfError`, `UserNotFoundError` (todos `IdentityError`)
  - `RegistrationGate` (Protocol): `async is_open() -> bool`, `async set_open(open: bool) -> None`
  - `IdentityUseCases` ganha campos `registration: RegistrationGate` e `admin_emails: frozenset[Email] = frozenset()`, e métodos:
    - `async is_admin(user_id: UserId) -> bool`
    - `async require_admin(user_id: UserId) -> User` (levanta `NotAdminError`)
    - `async registration_open() -> bool`
    - `async set_registration(admin_id: UserId, open: bool) -> None` (exige admin)
  - `register` levanta `RegistrationClosedError` quando fechado e o e-mail não é admin.

- [ ] **Passo 1: Cenários que falham** (`admin.feature`, `# language: pt`)
  - "E-mail do ambiente é admin": admins `" Eu@Exemplo.com ,"`; cadastro `eu@exemplo.com` → é admin; `outra@exemplo.com` → não é.
  - "Cadastro fechado recusa contas novas": admin fecha; `nova@exemplo.com` tenta cadastrar → recusado por cadastro fechado.
  - "Admin cadastra mesmo com o cadastro fechado".
  - "Quem não é admin não fecha o cadastro" → recusado por falta de permissão; cadastro continua aberto.
  - "Reabrir o cadastro" → nova conta entra.
- [ ] **Passo 2:** `cd backend && poetry run pytest tests/features/test_admin.py -q` → falha (steps/métodos inexistentes).
- [ ] **Passo 3:** implementar o listado em Interfaces. `is_admin` busca o usuário e compara `user.email in admin_emails`.
- [ ] **Passo 4:** contrato do gate (memória e Mongo, padrão de `test_notebook_repository_contract.py`): padrão aberto; `set_open(False)` → `is_open()` falso; **instância nova sobre a mesma coleção continua fechada**; `set_open(True)` reabre.
- [ ] **Passo 5: Verificar** `poetry run pytest tests/features/test_admin.py tests/integration/test_registration_gate_contract.py tests/architecture -q` → tudo passa.

### Tarefa 2: Listagem paginada de contas e exclusão pelo admin (backend, identity)

**Arquivos:**
- Modificar: `identity/domain/model.py` (`UserCursor`), `identity/application/ports.py`, `use_cases.py`, repositórios de usuário memória/Mongo
- Modificar: `shared/adapters/mongo_setup.py` (índice `users`: `[("created_at", -1), ("_id", -1)]`, nome `by_created`)
- Testes: `admin.feature` (novos cenários), `backend/tests/integration/test_user_repository_contract.py`

**Interfaces:**
- Consome: `require_admin` (Tarefa 1).
- Produz:
  - `UserCursor(created_at: datetime, user_id: uuid.UUID)` com `of(user)` e `is_after(user)` — mesma ideia de `HistoryCursor` em `insights/application/history.py`.
  - `UserRepository.page(limit: int, after: UserCursor | None = None) -> list[User]` (mais recentes primeiro; empate pelo id desc).
  - `UserPage(items: list[User], next: UserCursor | None)`.
  - `IdentityUseCases.list_accounts(admin_id: UserId, limit: int, after: UserCursor | None = None) -> UserPage` (busca `limit + 1`).
  - `IdentityUseCases.admin_delete(admin_id: UserId, account_id: UserId) -> None`: exige admin; `account_id == admin_id` → `CannotDeleteSelfError`; inexistente → `UserNotFoundError`; senão `sessions.delete_all_for` + `users.delete`. (Apagar trilha/histórico/caderno fica na rota, via `erase_learner_data`, como no fluxo LGPD.)

- [ ] **Passo 1: Cenários que falham**
  - "Admin vê as contas, mais recentes primeiro, em páginas": 3 contas criadas em horários diferentes, página de 2 → as 2 mais novas + existe próxima; próxima → a mais antiga, sem próxima.
  - "Admin exclui uma conta" → a conta some da listagem e o login dela falha.
  - "Admin não exclui a si mesmo" → recusado.
  - "Excluir conta inexistente" → recusado por conta não encontrada.
  - "Quem não é admin não lista contas" → recusado por falta de permissão.
- [ ] **Passo 2:** rodar → falha.
- [ ] **Passo 3:** implementar; Mongo: `find(query).sort([("created_at", -1), ("_id", -1)]).limit(limit)` com `$or` de keyset igual ao `MongoSessionHistoryStore.page_for`.
- [ ] **Passo 4:** contrato memória/Mongo: ordem com empate de `created_at` resolvido por id, sem pular nem repetir entre páginas.
- [ ] **Passo 5: Verificar** `poetry run pytest tests/features tests/integration/test_user_repository_contract.py -q` → passa.

### Tarefa 3: Rotas HTTP de admin (composição)

**Arquivos:**
- Criar: `backend/src/developer_myself/admin_routes.py`
- Modificar: `insights/application/history.py` + stores (`count_for(learner_id: str) -> int`), `identity/adapters/http/routes.py` (`MeOut.is_admin`, `GET /api/auth/registration`), `bootstrap.py` (registrar router, mapear erros), `.env.example` (`DM_ADMIN_EMAILS=`)
- Testes: `backend/tests/http/test_admin_api.py`

**Interfaces:**
- Consome: Tarefas 1 e 2; `container.erase_learner_data`; `container.learning.get_plan` (conta sem trilha → `contents: 0`); `container.history.store.page_for(id, 1)` para `last_activity_at`.
- Produz (consumido pela Tarefa 4):
  - `GET /api/auth/me` → `{id, email, created_at, is_admin}`
  - `GET /api/auth/registration` (público) → `{open: bool}`
  - `GET /api/admin/accounts?limit=1..100 (padrão 20)&cursor=` → `{items: [{id, email, created_at, last_activity_at|null, contents, sessions}], next_cursor}`
  - `DELETE /api/admin/accounts/{id}` → 204
  - `GET /api/admin/registration` → `{open}`; `PUT /api/admin/registration {open}` → `{open}`
  - Mapeamento: `NotAdminError` 403 `FORBIDDEN`; `RegistrationClosedError` 403 `REGISTRATION_CLOSED`; `CannotDeleteSelfError` 409 `CANNOT_DELETE_SELF`; `UserNotFoundError` 404 `NOT_FOUND`. O `code` é o que o frontend lê.
  - Cursor: base64url de JSON `{"t": iso, "id": uuid}`; reaproveitar o padrão de `encode_cursor/decode_cursor` em `insights/adapters/http_routes.py`.

- [ ] **Passo 1: Testes que falham** (cliente com `Settings(admin_emails="admin@exemplo.com")`):
  - `test_me_reports_is_admin` (admin true, outro false)
  - `test_admin_routes_require_login` (401) e `test_admin_routes_forbid_non_admin` (403 `FORBIDDEN` nas 4 rotas)
  - `test_list_accounts_shows_counts_not_notes`: conta com 1 conteúdo e 1 sessão → `contents == 1`, `sessions == 1`, `last_activity_at` preenchido; resposta **não** contém `notes_studied` nem o texto das anotações
  - `test_list_accounts_paginates` (limit 1 → `next_cursor`, segunda página diferente) e `test_list_accounts_rejects_bad_cursor` (422)
  - `test_account_without_plan_lists_zero_contents`
  - `test_admin_deletes_account_and_its_data`: depois do DELETE, a conta some da lista e `/api/export` dela não existe mais (login falha)
  - `test_admin_cannot_delete_self` (409) e `test_delete_unknown_account` (404)
  - `test_closed_registration_blocks_new_accounts_but_not_admin`; `test_public_registration_status`
  - `test_admin_losing_status_gets_403` (trocar `app.state.container.identity.admin_emails` no meio)
  - `test_admin_delete_is_audited_without_email` (capturar log `admin_deleted_account`; sem o e-mail)
- [ ] **Passo 2:** `poetry run pytest tests/http/test_admin_api.py -q` → falha.
- [ ] **Passo 3:** implementar. `AdminDep` = `LearnerIdDep` + `require_admin`. DELETE: `admin_delete` e depois `erase_learner_data(account_id)`.
- [ ] **Passo 4: Verificar** `make lint typecheck && cd backend && poetry run pytest -q` → tudo passa.

### Tarefa 4: Página `/admin` e aviso no cadastro (frontend)

**Arquivos:**
- Modificar: `frontend/src/api/types.ts` (`Me.is_admin`, `AdminAccount`, `AdminAccountsPage`), `api/client.ts`, `api/hooks.ts`
- Criar: `frontend/src/pages/AdminPage.tsx` + `AdminPage.test.tsx`
- Modificar: `app/router.tsx` (rota `admin`), `app/MainNav.tsx` (item "Admin", ícone `Shield`, só se `me.is_admin`), `pages/AuthPage.tsx` (aviso com cadastro fechado), testes existentes que mockam `/auth/me`

**Interfaces:**
- Consome: rotas da Tarefa 3.
- Produz: `api.adminAccounts(cursor)`, `api.adminDeleteAccount(id)`, `api.registrationStatus()`, `api.setRegistration(open)`; hooks `useAdminAccounts()` (infinite, como `useHistory`), `useRegistration()`.

- [ ] **Passo 1: Testes que falham** (`AdminPage.test.tsx`, `routeFetch`):
  - lista e-mail, data, contagens; "Carregar mais" busca `?cursor=`
  - interruptor "Cadastro aberto" envia `PUT /admin/registration {open:false}`
  - "Excluir": o botão de confirmar só habilita depois de digitar o e-mail exato; confirma → `DELETE /admin/accounts/<id>`
  - 403 vira mensagem "Você não tem acesso à área de admin." (via `ErrorState`)
  - `MainNav`: "Admin" aparece só com `is_admin: true`
  - `AuthPage` em `/cadastro` com `{open:false}`: mostra "Novos cadastros estão fechados no momento." e o formulário continua (admin ainda pode cadastrar)
- [ ] **Passo 2:** `npx vitest run` → falha.
- [ ] **Passo 3:** implementar. Rota `/admin` para não admin redireciona para `/hoje`.
- [ ] **Passo 4: Verificar** `make lint typecheck test-web e2e` → passa.

### Tarefa 5: Verificação final
- [ ] `make check` e `make e2e` passam; `git status` mostra só os arquivos deste plano.
- [ ] Relatar ao usuário: configurar `DM_ADMIN_EMAILS` no painel do Render e reiniciar o serviço.
