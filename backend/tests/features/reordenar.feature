# language: pt
Funcionalidade: Reordenar a fila
  Como aprendiz
  Quero mudar a ordem da fila
  Para estudar primeiro o que é pré-requisito ou prioridade

  Cenário: Os conteúdos escolhidos passam para a frente da fila, na ordem dada
    Dado que "Clean Code" está em andamento
    E que "Refactoring" está bloqueado
    E que "DDD" está bloqueado
    E que "TDD" está bloqueado
    Quando eu reordeno a fila para "TDD, DDD"
    Então a fila fica "TDD, DDD, Refactoring"

  Cenário: A nova ordem decide quem entra quando abre a vaga
    Dado que "Clean Code" está em andamento com 10 pontos
    E que "Refactoring" está bloqueado
    E que "TDD" está bloqueado
    E que eu reordenei a fila para "TDD"
    Quando eu resolvo 3 desafios de Intermediário em "Clean Code"
    Então "TDD" fica em andamento
    E "Refactoring" continua bloqueado

  Cenário: Só conteúdos que estão na fila podem ser reordenados
    Dado que "Clean Code" está em andamento
    E que "Refactoring" está bloqueado
    Quando eu tento reordenar a fila para "Clean Code, Refactoring"
    Então a reordenação é recusada
