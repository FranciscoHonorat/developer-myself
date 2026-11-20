# language: pt
Funcionalidade: Caderno da matéria
  Como aprendiz
  Quero um bloco de notas livre ligado a cada matéria
  Para escrever conceitos com as minhas palavras durante a sessão e reler depois

  Regra: O caderno guarda o que eu escrevo, sem mexer na pontuação

    Cenário: Escrever no caderno durante a sessão
      Dado que "Clean Code" está em andamento
      E que iniciei uma sessão em "Clean Code"
      Quando eu escrevo no caderno de "Clean Code": "Funções pequenas fazem uma coisa só"
      Então o caderno de "Clean Code" diz "Funções pequenas fazem uma coisa só"

    Cenário: O caderno não muda a pontuação
      Dado que "Clean Code" está em andamento
      Quando eu escrevo no caderno de "Clean Code": "Nomes revelam intenção"
      E eu estudo "Clean Code" por 25 minutos com anotações
      Então "Clean Code" tem 1 ponto

    Cenário: O caderno cresce entre sessões
      Dado que "Clean Code" está em andamento
      Quando eu escrevo no caderno de "Clean Code": "A"
      E eu escrevo no caderno de "Clean Code": "A\nB"
      Então o caderno de "Clean Code" diz "A\nB"

    Cenário: Esvaziar o caderno
      Dado que "Clean Code" está em andamento
      Quando eu escrevo no caderno de "Clean Code": "x"
      E eu apago o caderno de "Clean Code"
      Então o caderno de "Clean Code" está vazio

    Cenário: Matéria na fila também tem caderno
      Dado que "Clean Code" está em andamento
      E que "Refactoring" está bloqueado
      Quando eu escrevo no caderno de "Refactoring": "Ler o catálogo de refatorações"
      Então o caderno de "Refactoring" diz "Ler o catálogo de refatorações"

  Regra: O caderno não se perde nem se mistura

    Cenário: Duas abas abertas
      Dado que "Clean Code" está em andamento
      E que escrevi no caderno de "Clean Code"
      Quando eu escrevo no caderno de "Clean Code" a partir de uma versão antiga
      Então o salvamento do caderno é recusado por conflito

    Cenário: Matéria que não está na trilha
      Dado que "Clean Code" está em andamento
      Quando eu tento escrever no caderno de uma matéria que não existe
      Então o salvamento do caderno é recusado porque a matéria não existe

    Cenário: Texto grande demais
      Dado que "Clean Code" está em andamento
      Quando eu tento escrever 100001 caracteres no caderno de "Clean Code"
      Então o salvamento do caderno é recusado por tamanho

    Cenário: Remover a matéria apaga o caderno
      Dado que "Clean Code" está em andamento
      E que "Refactoring" está bloqueado
      Quando eu escrevo no caderno de "Refactoring": "rascunho"
      E eu removo "Refactoring"
      Então não existe caderno para "Refactoring"
