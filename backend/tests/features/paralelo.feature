# language: pt
Funcionalidade: Estudar até 3 conteúdos em paralelo
  Como aprendiz
  Quero estudar até 3 conteúdos ao mesmo tempo, de competências diferentes que se interligam
  Para avançar mais rápido sem misturar assuntos da mesma competência

  Regra: No máximo 3 em andamento, cada um de uma competência diferente

    Cenário: Até 3 conteúdos de competências diferentes são liberados
      Quando eu adiciono "Linux"
      E eu adiciono "Learning Go"
      E eu adiciono "SAST/DAST/SCA"
      E eu adiciono "Docker"
      Então "Linux" fica em andamento
      E "Learning Go" fica em andamento
      E "SAST/DAST/SCA" fica em andamento
      E "Docker" fica bloqueado
      E sou avisado de que "Docker" espera uma vaga entre os 3 em andamento

    Cenário: Dois conteúdos da mesma competência não ficam em andamento juntos
      Dado que "Linux" está em andamento
      Quando eu adiciono "Redes"
      Então "Redes" fica bloqueado
      E sou avisado de que preciso concluir "Linux" ou chegar a Intermediário

  Regra: Quando abre uma vaga, entra o conteúdo da fila que mais se interliga com os em andamento

    Cenário: A vaga vai para o conteúdo que mais se interliga, não só para o primeiro da fila
      Dado que "Linux" está em andamento com 10 pontos
      E que "Learning Go" está em andamento
      E que "SAST/DAST/SCA" está em andamento
      E que "Conversação em Espanhol" está bloqueado
      E que "Designing Web APIs" está bloqueado
      Quando eu resolvo 3 desafios de Intermediário em "Linux"
      Então "Linux" fica consolidado
      E "Designing Web APIs" fica em andamento
      E "Conversação em Espanhol" continua bloqueado

    Cenário: Em empate de afinidade, vale a ordem de chegada
      Dado que "Linux" está em andamento com 10 pontos
      E que "Learning Go" está em andamento
      E que "SAST/DAST/SCA" está em andamento
      E que "Conversação em Inglês" está bloqueado
      E que "Conversação em Espanhol" está bloqueado
      Quando eu resolvo 3 desafios de Intermediário em "Linux"
      Então "Conversação em Inglês" fica em andamento
      E "Conversação em Espanhol" continua bloqueado

    Cenário: Concluir um conteúdo já consolidado não abre vaga nova
      Dado que "Learning Go" está consolidado com 30 pontos
      E que resolvi 3 desafios de Avançado em "Learning Go"
      E que "Linux" está em andamento
      E que "Redes" está bloqueado
      Quando eu concluo "Learning Go"
      Então "Learning Go" fica concluído
      E "Redes" continua bloqueado
