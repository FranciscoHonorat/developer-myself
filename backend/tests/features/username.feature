# language: pt
Funcionalidade: Username como login
  Como aprendiz
  Quero entrar com um username
  Para não precisar digitar o e-mail

  Regra: Contas antigas ganham o username a partir do e-mail

    Cenário: Migração dá a parte antes do @, sem colisão
      Dado as contas antigas sem username, da mais antiga para a mais nova:
        | email       |
        | jose@a.com  |
        | jose@b.com  |
        | ana+x@c.com |
      Quando os usernames que faltam são preenchidos
      Então 3 contas ganham username
      E os usernames são:
        | email       | username |
        | jose@a.com  | jose     |
        | jose@b.com  | jose-2   |
        | ana+x@c.com | ana_x    |

    Cenário: Rodar a migração de novo não muda nada
      Dado as contas antigas sem username, da mais antiga para a mais nova:
        | email      |
        | jose@a.com |
      E que os usernames que faltam foram preenchidos
      Quando os usernames que faltam são preenchidos
      Então 0 contas ganham username

  Regra: O login é feito com username e senha

    Cenário: Cadastrar e entrar com o username
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando "jose" entra com a senha certa
      Então o login funciona

    Cenário: Username com maiúsculas e espaços entra igual
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando " Jose " entra com a senha certa
      Então o login funciona

    Cenário: E-mail no lugar do username não entra
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando "jose@exemplo.com" entra com a senha certa
      Então o login é recusado

    Cenário: Username em uso no cadastro
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando "jose" tenta se cadastrar com o e-mail "outro@exemplo.com"
      Então a ação é recusada porque o username está em uso

  Regra: Cada um pode trocar o próprio username

    Cenário: Trocar o username
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando "jose" troca o username para "jose.silva" com a senha certa
      E "jose.silva" entra com a senha certa
      Então o login funciona
      E "jose" não entra mais

    Cenário: Trocar com a senha errada
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando "jose" tenta trocar o username para "outro" com a senha errada
      Então o login é recusado

    Cenário: Trocar só as maiúsculas do próprio username
      Dado que "jose" se cadastrou com o e-mail "jose@exemplo.com"
      Quando "jose" troca o username para "Jose" com a senha certa
      Então "jose" entra com a senha certa
