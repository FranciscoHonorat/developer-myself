# language: pt
Funcionalidade: Autoavaliação nas revisões
  Como aprendiz
  Quero dizer o quanto eu lembrava antes de cada revisão
  Para que a rede neural aprenda com a MINHA memória, e não só com dados simulados

  Regra: Toda revisão registra quanto eu lembrava (1 Esqueci, 2 Difícil, 3 Bem, 4 Fácil)

    Cenário: Uma revisão sem autoavaliação é recusada
      Dado que "DDD" está consolidado
      E que iniciei uma sessão em "DDD"
      Quando eu tento finalizar a revisão sem dizer quanto lembrava
      Então a finalização é recusada pedindo a autoavaliação
      E existe uma sessão ativa em "DDD"

    Cenário: A autoavaliação vira um rótulo com os sinais de antes da sessão
      Dado que "DDD" está consolidado
      E que se passaram 12 dias desde a última atividade em "DDD"
      Quando eu reviso "DDD" por 25 minutos lembrando "Difícil"
      Então o histórico registra a nota 2 com 12 dias desde o último contato
      E a revisão conta como lembrada

    Cenário: Esquecer conta como não lembrada
      Dado que "DDD" está consolidado
      Quando eu reviso "DDD" por 25 minutos lembrando "Esqueci"
      Então a revisão conta como esquecida

    Cenário: Sessão de estudo não pede autoavaliação
      Dado que "Clean Code" está em andamento
      Quando eu estudo "Clean Code" por 25 minutos com anotações
      Então "Clean Code" tem 1 ponto
