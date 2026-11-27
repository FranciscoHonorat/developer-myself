# language: pt
Funcionalidade: Aquecimento de recuperação
  Para lembrar do que estudei e ter um primeiro passo pequeno
  Como aprendiz
  Quero um aquecimento de 2 perguntas, sem consultar, antes de estudar

  Cenário: Conteúdo estudado ao menos uma vez oferece aquecimento
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    Quando eu abro o aquecimento
    Então o aquecimento está disponível para "Clean Code"
    E o aquecimento tem 2 perguntas

  Cenário: Conteúdo nunca estudado não oferece aquecimento
    Dado que "Clean Code" está em andamento
    Quando eu abro o aquecimento
    Então o aquecimento não está disponível

  Cenário: Sem nada em andamento, o consolidado com menor chance de lembrar é aquecido
    Dado que "DDD" está consolidado
    E que "Clean Code" está consolidado
    E que se passaram 30 dias
    E que revisei "Clean Code" hoje
    Quando eu abro o aquecimento
    Então o aquecimento está disponível para "DDD"

  Cenário: A pergunta do eu do futuro vem primeiro
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem deixando a pergunta "O que é CQS?"
    Quando eu inicio o aquecimento
    Então a 1ª pergunta do aquecimento é "O que é CQS?"

  Cenário: Recarregar devolve as mesmas perguntas
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei o aquecimento
    Quando eu inicio o aquecimento
    Então as perguntas do aquecimento não mudaram

  Cenário: Concluir sem corrigir é recusado
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento sem corrigir
    Então a ação é recusada pedindo o teste

  Cenário: Concluir não dá ponto e registra o aquecimento no histórico
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento corrigindo tudo
    Então "Clean Code" tem 1 ponto
    E o histórico registra um aquecimento com 2 perguntas

  Cenário: A pergunta usada no aquecimento sai da fila
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem deixando a pergunta "O que é CQS?"
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento corrigindo tudo
    Então "Clean Code" não tem perguntas do eu do futuro

  Cenário: Só um aquecimento por dia
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que concluí o aquecimento de hoje
    Quando eu abro o aquecimento
    Então o aquecimento não está disponível
    E o aquecimento de hoje está feito

  Cenário: Com sessão ativa não há aquecimento
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei uma sessão em "Clean Code"
    Quando eu abro o aquecimento
    Então o aquecimento não está disponível

  Cenário: Cancelar não registra nada
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei o aquecimento
    Quando eu cancelo o aquecimento
    Então não há aquecimento em andamento
    E o histórico não tem aquecimentos
    E o aquecimento está disponível para "Clean Code"

  Cenário: Depois do aquecimento, o próximo passo é a revisão pendente
    Dado que "DDD" está consolidado
    E que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento corrigindo tudo
    Então o próximo passo é revisar "DDD"

  Cenário: Sem revisão pendente, o próximo passo é estudar
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento corrigindo tudo
    Então o próximo passo é estudar "Clean Code"

  Cenário: Depois de estudar hoje, o aquecimento não sugere repetir o estudo
    Dado que "Clean Code" está em andamento
    E que estudei "Clean Code" ontem
    E que estudei "Clean Code" hoje
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento corrigindo tudo
    Então não há próximo passo sugerido

  Cenário: Revisão já feita hoje não é sugerida de novo
    Dado que "DDD" está consolidado
    E que revisei "DDD" hoje
    E que iniciei o aquecimento
    Quando eu concluo o aquecimento corrigindo tudo
    Então não há próximo passo sugerido
