# Perfil de admin para gerenciar contas

## Por quê
O app está publicado em https://developer-myself.onrender.com e o cadastro está aberto para
qualquer pessoa. O dono precisa ver quem criou conta, remover contas indesejadas e poder
fechar novos cadastros.

## Objetivos
- Listar contas: e-mail, data de cadastro, última atividade, nº de conteúdos e de sessões.
- Excluir uma conta com todos os dados (trilha, histórico, caderno), com confirmação.
- Abrir/fechar novos cadastros.

## Fora do escopo
- Bloquear/suspender conta, redefinir senha, editar dados de outra pessoa.
- Ver anotações, caderno ou histórico de outra pessoa (o admin vê só contagens).
- Tela ou API para promover alguém a admin.

## Restrições
- Admin = e-mail listado em `DM_ADMIN_EMAILS` (vírgulas), configurado no painel do Render.
  Nada no banco; ninguém se promove pela aplicação.
- Arquitetura hexagonal existente (ADR-0003): composição entre contextos só por IDs, numa
  rota de composição como `account_routes.py`.
- Rate limit e CSRF atuais continuam valendo nas rotas novas.

## Abordagens
1. **Variável de ambiente (escolhida pelo usuário).** Sem migração; trocar admin é editar a
   variável e reiniciar.
2. Papel no banco + script de promoção. Descartada: no Render exigiria Shell (plano pago)
   ou acesso direto ao Mongo.

## Desenho
**Permissão.** Dependência `AdminDep`: autentica pela sessão, busca o e-mail do usuário e
exige que esteja em `DM_ADMIN_EMAILS`; senão 403 `FORBIDDEN`. `/api/auth/me` passa a
devolver `is_admin` para o frontend mostrar o link "Admin".

**API (`/api/admin/*`).**
- `GET /api/admin/accounts?limit=&cursor=` → `{items, next_cursor}`; mais recentes primeiro
  (keyset por `created_at`, `id`), mesmo formato da paginação do histórico.
  Item: `id, email, created_at, last_activity_at, contents, sessions`.
- `DELETE /api/admin/accounts/{id}` → 204. Encerra sessões, apaga o usuário e chama o
  `erase_learner_data` já usado na exclusão LGPD. O admin não pode excluir a própria conta
  por aqui (409; ele usa o fluxo normal com senha). Log de auditoria `admin_deleted_account`
  com o id do admin e da conta (sem e-mail).
- `GET /api/admin/registration` / `PUT /api/admin/registration {open: bool}`.

**Cadastro fechado.** Estado salvo numa coleção `app_settings` (Mongo) / em memória, padrão
aberto. Com o cadastro fechado, `POST /api/auth/register` responde 403 `REGISTRATION_CLOSED`,
exceto para e-mails de `DM_ADMIN_EMAILS` (o dono nunca se tranca para fora). Rota pública
`GET /api/auth/registration` → `{open}` para `/cadastro` avisar antes de a pessoa preencher.

**Frontend.** Página `/admin` (só aparece para admin): interruptor "Cadastro aberto",
tabela de contas com "Carregar mais" e "Excluir" com diálogo de confirmação que pede para
digitar o e-mail da conta. `/cadastro` mostra aviso quando fechado.

**Testes.** BDD em pt para os casos de uso (listar, excluir, fechar cadastro, admin pelo
env), testes HTTP de permissão (não admin → 403, sem login → 401), contrato memória/Mongo
para a listagem paginada, testes de componente no frontend.

## Decisões deixadas para quem implementa
- Última atividade: `finished_at` da sessão de estudo mais recente; sem sessões, vazio.
- Tamanho de página da listagem: 20.
