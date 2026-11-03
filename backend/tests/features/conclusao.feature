# language: pt
Funcionalidade: Concluir um conteúdo
  Como aprendiz
  Quero que "concluído" signifique domínio de verdade
  Para que a conclusão não seja só um clique

  Regra: Só é possível concluir um conteúdo no nível máximo (Avançado)

    Cenário: Não é possível concluir sem ter estudado
      Dado que "Clean Code" está em andamento
      Quando eu tento concluir "Clean Code"
      Então a conclusão é recusada porque "Clean Code" ainda não chegou a Avançado
      E "Clean Code" continua em andamento

    Cenário: Intermediário ainda não permite concluir
      Dado que "DDD" está consolidado
      Quando eu tento concluir "DDD"
      Então a conclusão é recusada porque "DDD" ainda não chegou a Avançado
      E "DDD" continua consolidado

    Cenário: Pontos de Avançado sem os desafios não permitem concluir
      Dado que "DDD" está consolidado com 30 pontos
      E que resolvi 2 desafios de Avançado em "DDD"
      Quando eu tento concluir "DDD"
      Então a conclusão é recusada porque "DDD" ainda não chegou a Avançado

    Cenário: No nível Avançado o conteúdo pode ser concluído
      Dado que "DDD" está consolidado com 30 pontos
      E que resolvi 3 desafios de Avançado em "DDD"
      Quando eu concluo "DDD"
      Então "DDD" fica concluído

    Cenário: Um conteúdo concluído continua disponível para revisão
      Dado que "DDD" está consolidado com 30 pontos
      E que resolvi 3 desafios de Avançado em "DDD"
      E que concluí "DDD"
      Quando eu inicio uma sessão em "DDD"
      Então a sessão é de revisão
