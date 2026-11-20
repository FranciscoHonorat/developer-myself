# language: pt
Funcionalidade: Histórico de sessões em páginas
  Como aprendiz
  Quero ver o histórico de sessões aos poucos, da mais recente para a mais antiga
  Para a página abrir rápido mesmo depois de meses de estudo

  Regra: Cada página continua de onde a anterior parou, sem repetir nem pular sessão

    Cenário: Primeira página traz as mais recentes
      Dado que "Clean Code" está em andamento
      E que estudei "Clean Code" 5 vezes
      Quando eu abro o histórico com 2 sessões por página
      Então vejo as sessões 5, 4
      E existe uma próxima página

    Cenário: Percorrer todas as páginas
      Dado que "Clean Code" está em andamento
      E que estudei "Clean Code" 5 vezes
      Quando eu abro o histórico com 2 sessões por página
      E eu abro a próxima página
      E eu abro a próxima página
      Então vejo as sessões 1
      E não existe próxima página

    Cenário: Sessão nova não bagunça a página seguinte
      Dado que "Clean Code" está em andamento
      E que estudei "Clean Code" 3 vezes
      Quando eu abro o histórico com 2 sessões por página
      E eu estudo "Clean Code" por 25 minutos com anotações
      E eu abro a próxima página
      Então vejo as sessões 1
      E não existe próxima página

    Cenário: Histórico vazio
      Quando eu abro o histórico com 2 sessões por página
      Então não vejo nenhuma sessão
      E não existe próxima página
