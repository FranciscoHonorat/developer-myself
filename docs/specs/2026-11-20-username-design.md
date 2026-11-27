# Username como identificador de login

## Por quê
O dono quer que cada conta tenha um username e que o login seja feito com ele (e senha),
não mais com o e-mail. O app já está publicado no Render com contas existentes.

## Objetivos
- Toda conta tem um username único; o login é **só** username + senha.
- Contas antigas ganham automaticamente a parte do e-mail antes do `@`.
- O usuário pode trocar o próprio username depois.

## Fora do escopo / anti-objetivos
- Recuperar username esquecido (não há envio de e-mail; o admin vê o username na listagem).
- Login por e-mail (decisão do usuário: só username).
- Nenhuma conta antiga pode ficar sem username após o deploy (trancada para fora).

## Restrições
- Arquitetura hexagonal (ADR-0003); e-mail continua guardado e define o admin (`DM_ADMIN_EMAILS`).
- Render sem Shell: a migração tem de rodar sozinha, sem script manual.

## Abordagens
1. **Migração na subida (escolhida).** Idempotente: só preenche usuários sem `username`.
2. Preencher no primeiro login. Descartada: o login passa a exigir username, então quem não
   tem não entraria.
3. Script manual. Descartada: no Render exigiria Shell (plano pago).

## Desenho
**Regra do username.** 3–30 caracteres, `[a-z0-9._-]`; entrada é normalizada para minúsculas
(`Jose` = `jose`). Único (índice único no Mongo).

**Migração.** Para cada usuário sem username: parte antes do `@`, minúscula, cada caractere
fora da regra vira `_`, corta em 30; menos de 3 caracteres → sufixo `-1`; colisão → `-2`,
`-3`… (cortando a base para caber em 30). Ordem: contas mais antigas primeiro (quem chegou
antes fica com o nome "limpo"). Roda no boot, nas duas implementações (memória e Mongo).

**Cadastro.** Campos username, e-mail, senha. Username inválido → 422 com a regra; em uso →
409 `USERNAME_TAKEN` "Este username já está em uso.".

**Login.** `{username, password}`. Erro genérico "Username ou senha inválidos." (sem revelar
se o username existe, com o mesmo custo de tempo do Argon2). Rate limit por IP e por username.

**Trocar username.** `PUT /api/auth/username {username, password}` na página Conta; exige a
senha atual; mesmas regras e 409 se em uso; a sessão atual continua válida.

**Onde aparece.** `/auth/me` devolve `username`; listagem do admin ganha a coluna username.
Tela de login mostra: "Agora o login é por username: o seu é a parte do e-mail antes do @
(você pode trocar na página Conta)."

## Deixado para quem implementa
- Mensagens exatas de validação além das citadas.
- Onde mostrar o username na casca do app (ex.: página Conta).
