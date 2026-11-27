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

  Cenário: O caderno guarda o que escrevi na matéria
    Quando eu adiciono o conteúdo "Clean Code"
    E eu inicio uma sessão de estudo em "Clean Code"
    E eu escrevo no caderno "Funções pequenas fazem uma coisa só"
    E eu finalizo a sessão com as minhas anotações
    E eu abro "Clean Code" na aba Caderno
    Então vejo "Funções pequenas fazem uma coisa só" no caderno

  Cenário: O aquecimento traz de volta a pergunta que deixei para mim
    Quando eu adiciono o conteúdo "Clean Code"
    E eu inicio uma sessão de estudo em "Clean Code"
    E eu deixo para o eu do futuro a pergunta "O que é CQS?"
    E eu finalizo a sessão com as minhas anotações
    E eu volto para a tela Hoje
    E eu começo o aquecimento
    Então a 1ª pergunta do aquecimento é "O que é CQS?"
    Quando eu corrijo e concluo o aquecimento
    Então vejo que o aquecimento foi feito, sem repetir o estudo de hoje
    Quando eu encerro por hoje
    Então a tela Hoje mostra que o aquecimento de hoje está feito

  @celular
  Cenário: A jornada principal funciona no celular
    Quando eu adiciono o conteúdo "Clean Code"
    E eu inicio uma sessão de estudo em "Clean Code"
    Então o botão "Finalizar sessão" fica visível acima da barra de navegação
    E o fim de cada seção fica visível acima da barra de navegação
    E a página não rola na horizontal
