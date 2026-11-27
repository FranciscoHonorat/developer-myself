# language: pt
Funcionalidade: Teste de memória na revisão
  Para fixar o que estudei de verdade
  Como aprendiz
  Quero que toda revisão comece tentando lembrar, sem consultar

  Cenário: A revisão começa com 3 perguntas
    Dado que "Clean Code" está consolidado
    Quando eu inicio uma sessão em "Clean Code"
    Então a sessão tem 3 perguntas de memória

  Cenário: O "preciso revisar" vira a primeira pergunta
    Dado que "Clean Code" está consolidado
    E que anotei para revisar em "Clean Code": "CQS"
    Quando eu inicio uma sessão em "Clean Code"
    Então a 1ª pergunta é "Explique sem consultar: CQS"

  Cenário: Sem corrigir o teste não dá para finalizar
    Dado que "Clean Code" está consolidado
    E que iniciei uma sessão em "Clean Code"
    Quando eu finalizo a revisão 25 minutos depois sem responder o teste
    Então a finalização é recusada pedindo o teste
    E existe uma sessão ativa em "Clean Code"

  Cenário: Errar tudo ainda pontua
    Dado que "Clean Code" está consolidado
    E que iniciei uma sessão em "Clean Code"
    Quando eu finalizo a revisão 25 minutos depois errando todas
    Então "Clean Code" tem 11 pontos

  Cenário: Estudo não tem teste
    Dado que "Clean Code" está em andamento
    Quando eu inicio uma sessão em "Clean Code"
    Então a sessão não tem perguntas de memória

  Cenário: Revisão aberta antes da mudança finaliza sem teste
    Dado que "Clean Code" está consolidado
    E que uma revisão de "Clean Code" foi aberta antes do teste existir
    Quando eu finalizo a revisão 25 minutos depois sem responder o teste
    Então "Clean Code" tem 11 pontos

  Cenário: O "preciso revisar" volta na próxima sessão
    Dado que "Clean Code" está em andamento
    Quando eu estudo "Clean Code" por 25 minutos anotando para revisar "goroutines"
    Então o último "preciso revisar" de "Clean Code" é "goroutines"

  Cenário: O histórico guarda o teste
    Dado que "Clean Code" está consolidado
    E que iniciei uma sessão em "Clean Code"
    Quando eu finalizo a revisão 25 minutos depois errando todas
    Então o histórico registra 3 perguntas com as minhas correções

  Cenário: A pergunta do eu do futuro entra na revisão
    Dado que "Clean Code" está consolidado
    E que deixei para "Clean Code" a pergunta "O que é CQS?"
    Quando eu inicio uma sessão em "Clean Code"
    Então a 1ª pergunta é "O que é CQS?"

  Cenário: A pergunta usada na revisão sai da fila
    Dado que "Clean Code" está consolidado
    E que deixei para "Clean Code" a pergunta "O que é CQS?"
    E que iniciei uma sessão em "Clean Code"
    Quando eu finalizo a revisão 25 minutos depois errando todas
    Então "Clean Code" não tem perguntas do eu do futuro
