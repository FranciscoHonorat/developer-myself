# ADR-0008: Estratégia de testes — TDD + BDD

**Status:** Proposto
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

O valor do sistema está nas regras do [ADR-0002](ADR-0002-modelo-de-dominio.md). Elas precisam de especificação legível (BDD) e de feedback em segundos (TDD).

## Decisão

| Camada | Ferramenta | Alvo | I/O | Volume |
|---|---|---|---|---|
| `unit/` | pytest | VOs, entidades, políticas | Nenhum | Muitos |
| `features/` | **pytest-bdd** + Gherkin `# language: pt` | Casos de uso com fakes em memória | Nenhum | Um por regra |
| `integration/` | pytest + Testcontainers | Adapters Mongo e RabbitMQ | Real | Poucos |
| `architecture/` | pytest (AST) | Regra de dependência | Nenhum | 1 |
| e2e | Playwright | Fluxo crítico na UI | Tudo | 1–3 smoke |

### Princípios

- **O BDD exercita o caso de uso, não o HTTP.** Os cenários rodam em milissegundos. O HTTP é só um adapter fino, testado à parte.
- **Teste de contrato do repositório**: **a mesma** suíte é parametrizada com `InMemoryStudyPlanRepository` e com `MongoStudyPlanRepository`. Se o fake passa e o Mongo também, o fake é confiável.
- **`FakeClock`**: o tempo é controlado (`clock.advance(minutes=25)`). Nenhum teste usa `sleep`.
- **Red → Green → Refactor, um teste por vez.** O refactor é um commit `tidy:` separado ([ADR-0007](ADR-0007-toolchain-qualidade.md)).
- A cobertura serve de **sinal**, não de meta. A exceção é o domínio, que tem *gate* de 100% de branches, porque é barato e é onde mora o valor.

## Opções consideradas

| | pytest-bdd ✅ | behave | Só pytest com nomes descritivos |
|---|---|---|---|
| Integra fixtures pytest | Sim | Não (runner próprio) | Sim |
| Spec legível por não-dev | Sim | Sim | Não |

## Consequências

- ✅ Os cenários Gherkin **são** a documentação viva das regras.
- ⚠️ É preciso **verificar na versão instalada** do pytest-bdd o suporte a `# language: pt` (palavras-chave Dado/Quando/Então). Esse é o primeiro teste do projeto.
- 🔁 Se os *step definitions* virarem lógica, mover essa lógica para o caso de uso.
