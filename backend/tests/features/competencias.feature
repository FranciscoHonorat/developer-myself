# language: pt
Funcionalidade: Ficha de competências
  Como aprendiz
  Quero ver minhas competências subirem com a pontuação e enferrujarem sem prática
  Para saber onde estou forte, o que estou esquecendo e o quanto falta para a meta do mapa

  Regra: A competência sobe com pontos e desafios dos conteúdos que contam para ela

    Cenário: Estudar Go aumenta a competência Go
      Dado que "Learning Go" está em andamento com 5 pontos
      Quando eu consulto minha ficha de competências
      Então a competência "Go" está acima de 0
      E sou "Aprendiz em Go"

    Cenário: Avançado em todos os conteúdos de Go faz de mim Especialista
      Dado que "Learning Go" está consolidado com 30 pontos
      E que resolvi 3 desafios de Avançado em "Learning Go"
      Quando eu consulto minha ficha de competências
      Então a competência "Go" vale 100
      E sou "Especialista em Go"

    Cenário: Conteúdos ainda na fila também contam, como cobertura que falta
      Dado que "Learning Go" está consolidado com 30 pontos
      E que resolvi 3 desafios de Avançado em "Learning Go"
      E que "Gin" está em andamento
      Quando eu consulto minha ficha de competências
      Então a competência "Go" está abaixo de 100

  Regra: Sem revisar nem resolver desafios por mais de 3 semanas, a competência enferruja

    Cenário: Até 3 semanas parado, nada enferruja
      Dado que "Learning Go" está consolidado
      E que se passaram 21 dias desde a última atividade em "Learning Go"
      Quando eu consulto minha ficha de competências
      Então a competência "Go" não perdeu nada para a ferrugem

    Cenário: Depois de 3 semanas, a competência cai mas os pontos ficam
      Dado que "Learning Go" está consolidado
      E que se passaram 31 dias desde a última atividade em "Learning Go"
      Quando eu consulto minha ficha de competências
      Então a competência "Go" perdeu 10% para a ferrugem
      E "Learning Go" tem 10 pontos

    Cenário: A ferrugem tem um piso
      Dado que "Learning Go" está consolidado
      E que se passaram 365 dias desde a última atividade em "Learning Go"
      Quando eu consulto minha ficha de competências
      Então a competência "Go" perdeu 50% para a ferrugem

    Cenário: Revisar tira a ferrugem na hora
      Dado que "Learning Go" está consolidado
      E que se passaram 40 dias desde a última atividade em "Learning Go"
      E que revisei "Learning Go" hoje
      Quando eu consulto minha ficha de competências
      Então a competência "Go" não perdeu nada para a ferrugem

    Cenário: Resolver um desafio também tira a ferrugem
      Dado que "Learning Go" está consolidado
      E que se passaram 40 dias desde a última atividade em "Learning Go"
      E que resolvi 1 desafios de Avançado em "Learning Go"
      Quando eu consulto minha ficha de competências
      Então a competência "Go" não perdeu nada para a ferrugem

    Cenário: Aviso antes de enferrujar
      Dado que "Learning Go" está consolidado
      E que se passaram 17 dias desde a última atividade em "Learning Go"
      Quando eu consulto minha ficha de competências
      Então a competência "Go" enferruja em 4 dias
