# language: pt
Funcionalidade: Cronograma diário de estudos
  Como aprendiz
  Quero saber exatamente o que estudar hoje em cada conteúdo
  Para chegar a Avançado em 30 dias de sessões pontuadas

  Regra: Cada sessão pontuada conclui um dia do cronograma de 30 dias

    Cenário: O dia do cronograma acompanha os pontos
      Dado que "Linux" está em andamento com 3 pontos
      Quando eu consulto o plano de hoje
      Então devo estudar "Linux" no dia 4 de 30
      E o foco do dia fala de "pacotes (apt, dnf)"

    Cenário: Os dias 8 a 10 são desafios de Intermediário
      Dado que "Linux" está em andamento com 7 pontos
      Quando eu consulto o plano de hoje
      Então o dia de "Linux" é um desafio de Intermediário

    Cenário: O plano do dia junta estudo e revisões
      Dado que "Redes" está consolidado
      E que "Linux" está em andamento
      Quando eu consulto o plano de hoje
      Então devo estudar "Linux" no dia 1 de 30
      E devo revisar "Redes" no dia 11 de 30

    Cenário: Conteúdo fora do mapa recebe um cronograma por módulos
      Dado que "Trilha de 30 dias: Inteligência e Investigação" está em andamento
      Quando eu consulto o plano de hoje
      Então o foco do dia fala de "módulo/capítulo 1"
