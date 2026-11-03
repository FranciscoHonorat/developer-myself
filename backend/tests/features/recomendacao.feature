# language: pt
Funcionalidade: Recomendação de revisão pela rede neural
  Como aprendiz
  Quero saber qual conteúdo estou mais perto de esquecer
  Para revisar primeiro o que mais precisa

  Cenário: O conteúdo parado há mais tempo vem primeiro
    Dado que "DDD" está consolidado
    E que "Clean Code" está consolidado
    E que se passaram 30 dias
    E que revisei "Clean Code" hoje
    Quando eu peço uma recomendação de revisão
    Então a recomendação vem da rede neural
    E "DDD" vem antes de "Clean Code"
    E a chance estimada de lembrar "DDD" é menor que 50%
    E a chance estimada de lembrar "Clean Code" é maior que 80%

  Cenário: Conteúdo em andamento ou bloqueado não entra na recomendação
    Dado que "Clean Code" está em andamento
    E que "Refactoring" está bloqueado
    Quando eu peço uma recomendação de revisão
    Então não há nada para revisar

  Cenário: A rede é retreinada com as minhas autoavaliações
    Dado que "DDD" está consolidado
    E que fiz 5 revisões avaliadas de "DDD", uma por semana
    Quando o retreino automático roda
    Então um novo modelo é ativado
    E ele foi treinado com 5 revisões minhas
    E a recomendação passa a usar esse modelo

  Cenário: Sem rótulos novos suficientes, o retreino espera
    Dado que "DDD" está consolidado
    E que fiz 5 revisões avaliadas de "DDD", uma por semana
    E que o retreino automático já rodou
    E que fiz 2 revisões avaliadas de "DDD", uma por semana
    Quando o retreino automático roda
    Então o retreino é adiado por falta de rótulos novos
