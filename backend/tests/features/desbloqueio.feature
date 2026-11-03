# language: pt
Funcionalidade: Desbloqueio progressivo
  Como aprendiz
  Quero focar em um conteúdo por vez
  Para consolidar antes de começar outro

  Cenário: O primeiro conteúdo já entra em andamento
    Quando eu adiciono "Clean Code"
    Então "Clean Code" fica em andamento

  Cenário: Conteúdo novo entra bloqueado
    Dado que "Clean Code" está em andamento com 3 pontos
    Quando eu adiciono "Refactoring"
    Então "Refactoring" fica bloqueado
    E sou avisado de que preciso concluir "Clean Code" ou chegar a Intermediário

  Cenário: Não é possível estudar um conteúdo bloqueado
    Dado que "Clean Code" está em andamento
    E que "Refactoring" está bloqueado
    Quando eu tento iniciar uma sessão em "Refactoring"
    Então a sessão é recusada porque o conteúdo está bloqueado

  Cenário: Pontos sem desafios não sobem de nível
    Dado que "Clean Code" está em andamento com 9 pontos
    E que resolvi 2 desafios de Intermediário em "Clean Code"
    E que "Refactoring" está bloqueado
    Quando eu ganho 1 ponto em "Clean Code"
    Então "Clean Code" continua Iniciante
    E "Refactoring" continua bloqueado

  Cenário: Desafios sem pontos não sobem de nível
    Dado que "Clean Code" está em andamento com 5 pontos
    E que resolvi 3 desafios de Intermediário em "Clean Code"
    Então "Clean Code" continua Iniciante

  Cenário: Pontos e 3 desafios desbloqueiam o próximo
    Dado que "Clean Code" está em andamento com 10 pontos
    E que resolvi 2 desafios de Intermediário em "Clean Code"
    E que "Refactoring" está bloqueado
    Quando eu resolvo o 3º desafio de Intermediário em "Clean Code" com evidência
    Então "Clean Code" fica Intermediário
    E "Clean Code" fica consolidado
    E "Refactoring" fica em andamento

  Cenário: A fila respeita a ordem de chegada
    Dado que "Clean Code" está em andamento com 10 pontos
    E que resolvi 2 desafios de Intermediário em "Clean Code"
    E que "Refactoring" está bloqueado
    E que "DDD" está bloqueado
    Quando eu resolvo o 3º desafio de Intermediário em "Clean Code" com evidência
    Então "Refactoring" fica em andamento
    E "DDD" continua bloqueado
