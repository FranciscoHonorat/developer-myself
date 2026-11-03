# language: pt
Funcionalidade: Sessões de estudo
  Como aprendiz
  Quero que o servidor controle o tempo das sessões
  Para que ninguém consiga trapacear nos pontos

  Cenário: Sessão aberta há mais de 4 horas não pontua
    Dado que iniciei uma sessão em "Clean Code"
    Quando eu finalizo a sessão 4 horas e 1 minuto depois com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "EXPIRED"

  Cenário: Só é possível ter uma sessão ativa por vez
    Dado que iniciei uma sessão em "Clean Code"
    Quando eu tento iniciar uma sessão em "Clean Code"
    Então a sessão é recusada porque já existe uma sessão ativa

  Cenário: Uma sessão esquecida é abandonada ao iniciar a próxima
    Dado que iniciei uma sessão em "Clean Code"
    Quando eu inicio uma sessão em "Clean Code" 5 horas depois
    Então a sessão anterior foi abandonada
    E existe uma sessão ativa em "Clean Code"

  Cenário: O tipo da sessão é derivado do estado do conteúdo
    Dado que "DDD" está consolidado
    Quando eu inicio uma sessão em "DDD"
    Então a sessão é de revisão

  Cenário: Cancelar uma sessão não pontua
    Dado que iniciei uma sessão em "Clean Code"
    Quando eu cancelo a sessão
    Então não existe sessão ativa
    E "Clean Code" tem 0 pontos
