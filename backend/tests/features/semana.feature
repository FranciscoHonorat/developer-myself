# language: pt
Funcionalidade: Semana planejada
  Como aprendiz
  Quero uma semana em que cada dia junta 3 ou 4 competências (mais o Inglês) e soma de 3h a 8h
  Para estudar em paralelo sem perder a revisão nem os dias de desafio

  Contexto:
    Dado que "Docker" está consolidado
    E que "SQL e NoSQL" está consolidado
    E que "Learning Go" está em andamento
    E que "SAST/DAST/SCA" está em andamento
    E que "Designing Web APIs" está em andamento

  Regra: Cada dia soma o tempo escolhido, em pomodoros de 30 min (25 de estudo + 5 de pausa)

    Cenário: 3h30 por dia com 3 conteúdos em andamento e revisões
      Dado que "Linux" está bloqueado
      E que eu estudo 210 minutos por dia
      Quando eu consulto a semana
      Então cada dia de estudo soma 210 minutos
      E cada dia de estudo tem entre 3 e 4 competências diferentes
      E cada dia começa com revisão
      E os 3 conteúdos em andamento aparecem todos os dias até chegarem a Intermediário
      E quem chega a Intermediário dá a vaga para "Linux" na mesma semana

    Cenário: 3h por dia continua com 3 competências
      Dado que eu estudo 180 minutos por dia
      Quando eu consulto a semana
      Então cada dia de estudo soma 180 minutos
      E cada dia de estudo tem entre 3 e 4 competências diferentes

    Cenário: 8h por dia
      Dado que eu estudo 480 minutos por dia
      Quando eu consulto a semana
      Então cada dia de estudo soma 480 minutos

    Cenário: Dia de folga não tem estudo
      Dado que eu estudo 240 minutos por dia
      E que domingo é meu dia de folga
      Quando eu consulto a semana
      Então domingo não tem estudo
      E cada dia de estudo soma 240 minutos

  Regra: A semana acompanha o cronograma de 30 dias de cada conteúdo

    Cenário: O avanço no cronograma é contado por sessão
      Dado que eu estudo 210 minutos por dia
      Quando eu consulto a semana
      Então o primeiro bloco de "Learning Go" cobre os dias a partir do dia 1
      E o cronograma de "Learning Go" avança ao longo da semana

    Cenário: Dias de desafio aparecem como desafio
      Dado que eu estudo 210 minutos por dia
      E que "Learning Go" tem 6 pontos
      Quando eu consulto a semana
      Então há um bloco de desafio de "Learning Go" na semana

  Regra: As revisões se revezam para nenhum conteúdo consolidado enferrujar

    Cenário: Dois conteúdos consolidados se revezam ao longo da semana
      Dado que eu estudo 210 minutos por dia
      Quando eu consulto a semana
      Então "Docker" é revisado em pelo menos 3 dias
      E "SQL e NoSQL" é revisado em pelo menos 3 dias

  Regra: Inglês aparece todos os dias, com 2 pomodoros, sem tirar as revisões

    Cenário: Inglês tem 2 pomodoros em cada dia de estudo
      Dado que "Conversação em Inglês" está em andamento
      E que eu estudo 240 minutos por dia
      E que domingo é meu dia de folga
      Quando eu consulto a semana
      Então "Conversação em Inglês" tem 2 pomodoros em cada dia de estudo
      E cada dia de estudo soma 240 minutos
      E cada dia começa com revisão
      E cada dia de estudo tem entre 4 e 5 competências diferentes

    Cenário: Inglês continua todos os dias depois de chegar a Intermediário
      Dado que "Conversação em Inglês" está em andamento com 9 pontos
      E que eu estudo 240 minutos por dia
      Quando eu consulto a semana
      Então "Conversação em Inglês" tem 2 pomodoros em cada dia de estudo
