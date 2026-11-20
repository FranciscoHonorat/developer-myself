# language: pt
Funcionalidade: Perfil de admin
  Como dono do app publicado
  Quero gerenciar as contas e o cadastro
  Para controlar quem usa o app

  Contexto:
    Dado que os admins configurados são " Eu@Exemplo.com ,"

  Regra: Admin é quem está na lista do ambiente

    Cenário: E-mail do ambiente é admin
      Quando "eu@exemplo.com" se cadastra
      E "outra@exemplo.com" se cadastra
      Então "eu@exemplo.com" é admin
      E "outra@exemplo.com" não é admin

  Regra: O admin abre e fecha o cadastro

    Cenário: Cadastro fechado recusa contas novas
      Dado que "eu@exemplo.com" se cadastrou
      Quando "eu@exemplo.com" fecha o cadastro
      E "nova@exemplo.com" tenta se cadastrar
      Então a ação é recusada porque o cadastro está fechado

    Cenário: Admin cadastra mesmo com o cadastro fechado
      Dado que o cadastro está fechado
      Quando "eu@exemplo.com" se cadastra
      Então "eu@exemplo.com" é admin

    Cenário: Quem não é admin não fecha o cadastro
      Dado que "outra@exemplo.com" se cadastrou
      Quando "outra@exemplo.com" tenta fechar o cadastro
      Então a ação é recusada por falta de permissão
      E o cadastro está aberto

    Cenário: Reabrir o cadastro
      Dado que "eu@exemplo.com" se cadastrou
      E que o cadastro está fechado
      Quando "eu@exemplo.com" abre o cadastro
      E "nova@exemplo.com" se cadastra
      Então o cadastro está aberto

  Regra: O admin vê e exclui contas

    Cenário: Admin vê as contas, mais recentes primeiro, em páginas
      Dado que "eu@exemplo.com" se cadastrou
      E que "a@exemplo.com" se cadastrou
      E que "b@exemplo.com" se cadastrou
      Quando "eu@exemplo.com" lista as contas com 2 por página
      Então vê as contas "b@exemplo.com", "a@exemplo.com"
      E existe outra página de contas
      Quando "eu@exemplo.com" abre a próxima página de contas
      Então vê as contas "eu@exemplo.com"
      E não existe outra página de contas

    Cenário: Admin exclui uma conta
      Dado que "eu@exemplo.com" se cadastrou
      E que "a@exemplo.com" se cadastrou
      Quando "eu@exemplo.com" exclui a conta de "a@exemplo.com"
      E "eu@exemplo.com" lista as contas com 10 por página
      Então vê as contas "eu@exemplo.com"
      E "a@exemplo.com" não consegue mais entrar

    Cenário: Admin não exclui a si mesmo
      Dado que "eu@exemplo.com" se cadastrou
      Quando "eu@exemplo.com" tenta excluir a conta de "eu@exemplo.com"
      Então a ação é recusada porque não se exclui a própria conta por aqui

    Cenário: Excluir conta que não existe mais
      Dado que "eu@exemplo.com" se cadastrou
      E que "a@exemplo.com" se cadastrou
      E que "eu@exemplo.com" excluiu a conta de "a@exemplo.com"
      Quando "eu@exemplo.com" tenta excluir a conta de "a@exemplo.com" de novo
      Então a ação é recusada porque a conta não existe

    Cenário: Quem não é admin não lista contas
      Dado que "outra@exemplo.com" se cadastrou
      Quando "outra@exemplo.com" tenta listar as contas
      Então a ação é recusada por falta de permissão
