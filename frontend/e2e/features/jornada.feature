# language: pt
Funcionalidade: Jornada principal do aprendiz
  Smoke e2e: o fluxo crítico pela interface, contra a API real.

  Contexto:
    Dado que eu criei uma conta nova

  Cenário: Uma sessão curta é registrada, mas não pontua
    Quando eu adiciono o conteúdo "Clean Code"
    E eu inicio uma sessão de estudo em "Clean Code"
    E eu finalizo a sessão com as minhas anotações
    Então vejo que a sessão não valeu ponto porque foi curta
    E a sessão aparece no meu histórico

  Cenário: O segundo conteúdo entra bloqueado na fila
    Quando eu adiciono o conteúdo "Clean Code"
    E eu adiciono o conteúdo "Refactoring"
    Então "Refactoring" aparece bloqueado esperando "Clean Code"
