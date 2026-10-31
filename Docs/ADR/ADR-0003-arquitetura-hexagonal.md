# ADR-0003: Arquitetura hexagonal (Ports & Adapters) e layout sem `__init__.py`

**Status:** Proposto
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

As regras do [ADR-0002](ADR-0002-modelo-de-dominio.md) precisam sobreviver a trocas de framework, banco e broker. Também queremos testar o domínio sem infraestrutura.

## Decisão

### Regra de dependência

```
adapters ──▶ application ──▶ domain        (setas = "importa")
```

- **domain**: entidades, VOs, eventos, políticas e o *port* do repositório. Usa só a stdlib.
- **application**: casos de uso (`StartSession`, `FinishSession`, `AddContent`) e *ports* de infraestrutura (`Clock`). Cada caso de uso é o **port de entrada**.
- **adapters**: de entrada (`http/` FastAPI, `consumers/` RabbitMQ) e de saída (`mongo/`, `rabbitmq/`).
- **bootstrap.py**: é o *composition root*, o único lugar que conhece todos os adapters (inversão de dependência do SOLID).

O tempo entra como valor: o caso de uso chama `clock.now()` e passa `now` para o domínio. O domínio fica **puro**, ou seja, não depende nem de um port.

Os ports são `typing.Protocol` (tipagem estrutural): o adapter não herda de nada, então o domínio não fica sabendo que ele existe.

### Layout

```
backend/
├── src/developer_myself/
│   ├── learning/{domain,application,adapters/{http,mongo,rabbitmq,consumers}}/
│   ├── identity/{domain,application,adapters}/
│   ├── shared/          ← só o que é genuinamente comum (Clock, EventEnvelope)
│   └── bootstrap.py
└── tests/{unit,features,integration,architecture}/
```

Sobre o DRY: `shared/` só recebe algo depois da **segunda** duplicação real. Código parecido em contextos diferentes **não é** duplicação de conhecimento.

### Sem `__init__.py`: o que é verdade e o que muda

O `__init__.py` não foi "removido". Desde o Python 3.3 ([PEP 420](https://peps.python.org/pep-0420/)), um diretório sem ele vira um *namespace package*. A novidade é que as ferramentas modernas lidam bem com isso, **desde que configuradas**:

| Ferramenta | Configuração obrigatória | Sem ela |
|---|---|---|
| pytest | `--import-mode=importlib` | `tests/unit/test_x.py` e `tests/integration/test_x.py` colidem |
| mypy | `mypy_path = "src"`, `explicit_package_bases = true` | "Source file found twice under different module names" |
| ruff | **não** ativar `INP001`; `src = ["src", "tests"]` | Lint exige `__init__.py`; o isort classifica imports errado |
| Poetry | `packages = [{ include = "developer_myself", from = "src" }]` | Pacote vazio no build |

O efeito colateral bom é que não existem *barrel files* nem código rodando no import, e todo import é absoluto e explícito.

### Garantia automática da regra de dependência

`tests/architecture/test_dependency_rule.py` percorre a AST de `*/domain/**/*.py` e falha se encontrar imports de `fastapi`, `pymongo`, `aio_pika`, `pydantic` ou `*.adapters`. É TDD aplicado à arquitetura, sem dependência extra.

## Opções consideradas

| | Hexagonal ✅ | Camadas (MVC) | Clean Arch completa (4 anéis + presenters) |
|---|---|---|---|
| Domínio testável sem I/O | Sim | Não | Sim |
| Cerimônia | Baixa | Mínima | Alta |
| Troca de banco/broker | Novo adapter | Reescrita | Novo adapter |

## Consequências

- ✅ Os adapters de Mongo e em memória passam **pela mesma suíte de contrato**. Isso é o princípio de substituição de Liskov verificado por teste.
- ⚠️ Mapeamento explícito domínio ↔ documento ↔ DTO: há três formas do mesmo dado. Esse é o custo do isolamento.
- 🔁 Se o mapeamento virar maioria do código, reavaliar o tamanho do agregado.
