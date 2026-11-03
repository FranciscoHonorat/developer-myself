# language: pt
Funcionalidade: Pontuar sessões de estudo
  Como aprendiz
  Quero ganhar pontos só por sessões de estudo de verdade
  Para que meu nível reflita o quanto eu realmente estudei

  Cenário: Sessão de 25 minutos com anotações pontua
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 25 minutos com anotações
    Então "Clean Code" tem 1 ponto

  Cenário: Sessão curta não pontua
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 24 minutos com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "TOO_SHORT"

  Cenário: Sessão sem anotações não pontua
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 30 minutos sem anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "NO_NOTES"

  Cenário: Anotações rasas não pontuam
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 30 minutos com anotações curtas
    Então "Clean Code" tem 0 pontos
    E o motivo é "NO_NOTES"

  Cenário: Estudar sem revisar no dia não pontua
    Dado que "DDD" está consolidado
    E que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 30 minutos com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "NO_REVIEW"

  Cenário: Revisar antes libera a pontuação do dia
    Dado que "DDD" está consolidado
    E que "Clean Code" está em andamento
    Quando eu reviso "DDD" por 25 minutos com anotações
    E eu estudo "Clean Code" por 25 minutos com anotações
    Então "Clean Code" tem 1 ponto

  Cenário: A revisão de ontem não vale hoje
    Dado que "DDD" está consolidado
    E que "Clean Code" está em andamento
    E que revisei "DDD" ontem
    Quando eu estudo "Clean Code" por 25 minutos com anotações
    Então "Clean Code" tem 0 pontos
    E o motivo é "NO_REVIEW"

  Cenário: A revisão também pontua no conteúdo revisado
    Dado que "DDD" está consolidado com 10 pontos
    Quando eu reviso "DDD" por 25 minutos com anotações
    Então "DDD" tem 11 pontos

  Cenário: O "dia" é o dia local do aprendiz, não o dia em UTC
    Dado que meu fuso horário é "America/Sao_Paulo"
    E que "DDD" está consolidado
    E que "Clean Code" está em andamento
    E que são 20:30 no meu horário local
    Quando eu reviso "DDD" por 25 minutos com anotações
    E eu estudo "Clean Code" por 25 minutos com anotações
    Então "Clean Code" tem 1 ponto

  Cenário: Conteúdo que chegou a Intermediário hoje só exige revisão a partir de amanhã
    Dado que "Linux" está em andamento com 10 pontos
    E que "Learning Go" está em andamento
    Quando eu resolvo 3 desafios de Intermediário em "Linux"
    E eu estudo "Learning Go" por 25 minutos com anotações
    Então "Learning Go" tem 1 ponto

  Cenário: No dia seguinte, o recém-consolidado passa a exigir revisão
    Dado que "Linux" está em andamento com 10 pontos
    E que "Learning Go" está em andamento
    E que resolvi 3 desafios de Intermediário em "Linux"
    E que se passaram 1 dias
    Quando eu estudo "Learning Go" por 25 minutos com anotações
    Então "Learning Go" tem 0 pontos
    E o motivo é "NO_REVIEW"
