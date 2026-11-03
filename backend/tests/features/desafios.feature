# language: pt
Funcionalidade: Desafios práticos
  Como aprendiz
  Quero provar o que aprendi resolvendo desafios
  Para que o nível dependa de aplicação, não só de tempo de estudo

  Cenário: Um desafio só é resolvido com evidência
    Dado que "Clean Code" está em andamento
    E que cadastrei um desafio de Intermediário em "Clean Code"
    Quando eu tento resolver o desafio sem evidência
    Então a resolução é recusada
    E o desafio continua pendente

  Cenário: Um desafio não pode ser resolvido duas vezes
    Dado que "Clean Code" está em andamento
    E que resolvi 1 desafios de Intermediário em "Clean Code"
    Quando eu tento resolver o mesmo desafio de novo
    Então a resolução é recusada

  Cenário: Avançado exige 30 pontos e 3 desafios de Avançado
    Dado que "DDD" está consolidado com 30 pontos
    E que resolvi 2 desafios de Avançado em "DDD"
    Quando eu resolvo o 3º desafio de Avançado em "DDD" com evidência
    Então "DDD" fica Avançado
