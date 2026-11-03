# language: pt
Funcionalidade: Organizar a trilha
  Como aprendiz
  Quero corrigir títulos e tirar conteúdos repetidos
  Para que a trilha reflita o que eu realmente vou estudar

  Regra: Só sai da trilha o conteúdo que ainda não teve progresso

    Cenário: Remover um conteúdo repetido da fila
      Dado que "Clean Code" está em andamento
      E que "Clean Code 2ª edição" está bloqueado
      E que "Refactoring" está bloqueado
      Quando eu removo "Clean Code 2ª edição"
      Então "Clean Code 2ª edição" não está mais na trilha
      E "Refactoring" continua bloqueado

    Cenário: Remover o conteúdo em andamento sem progresso libera o próximo
      Dado que "Clean Code" está em andamento
      E que "Refactoring" está bloqueado
      Quando eu removo "Clean Code"
      Então "Clean Code" não está mais na trilha
      E "Refactoring" fica em andamento

    Cenário: Não é possível remover um conteúdo com progresso
      Dado que "Clean Code" está em andamento com 1 pontos
      Quando eu tento remover "Clean Code"
      Então a remoção é recusada porque "Clean Code" já tem progresso

  Regra: Renomear mantém o progresso e não pode criar repetidos

    Cenário: Corrigir um título
      Dado que "Clean Code" está em andamento com 2 pontos
      Quando eu renomeio "Clean Code" para "Clean Code (Robert Martin)"
      Então "Clean Code (Robert Martin)" tem 2 pontos

    Cenário: Renomear para um título que já existe é recusado
      Dado que "Clean Code" está em andamento
      E que "Refactoring" está bloqueado
      Quando eu tento renomear "Refactoring" para "clean code"
      Então a renomeação é recusada por título repetido
