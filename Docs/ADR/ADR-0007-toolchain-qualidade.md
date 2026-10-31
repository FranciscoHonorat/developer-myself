# ADR-0007: Toolchain, lint, format e automação

**Status:** Proposto
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

Precisamos de um ambiente reproduzível (a mesma versão de tudo em qualquer máquina e no CI) e de feedback antes do commit, com o menor número possível de ferramentas.

## Decisão

| Arquivo | Papel | Decisão-chave |
|---|---|---|
| `.tool-versions` | Versões de runtime (mise, compatível com asdf) | Python 3.15.x e Node 26.x LTS, com o patch exato fixado. Critério: a estável/LTS mais recente no início do projeto ([ADR-0004](ADR-0004-backend-python-fastapi.md)) |
| `pyproject.toml` | Metadados (PEP 621, `[project]`) + configuração de **todas** as ferramentas | Poetry 2 lê `[project]` nativamente; build com `poetry-core>=2` |
| `poetry.lock` | Grafo de dependências resolvido com hashes | Versionado no git. O CI roda `poetry sync`, que deixa o ambiente **igual** ao lock (Poetry 2) |
| `.pre-commit-config.yaml` | Barreira local | ruff, ruff-format, mypy (hook `local` via `poetry run`), `poetry check --lock`, gitleaks, check-yaml, end-of-file-fixer |
| `Makefile` | **Única interface de comandos** | O CI, o pre-commit e as pessoas chamam os mesmos alvos (DRY entre local e CI) |

### Python: o Ruff faz lint e format

O Ruff substitui black, isort, flake8, pyupgrade e boa parte do bandit, com uma única ferramenta e uma única configuração.

```toml
[tool.ruff]
target-version = "py315"   # verificar se a versão instalada do Ruff já aceita; senão, "py314"
src = ["src", "tests"]
[tool.ruff.lint]
select = ["E","F","I","B","UP","S","N","SIM","RUF","PL","ARG","PT","TID","ASYNC"]
# INP001 fica de fora de propósito (namespace packages, ADR-0003)
[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "PLR2004"]
```

**Tipos:** `mypy --strict` com `mypy_path = "src"` e `explicit_package_bases = true`.
**Testes:** `[tool.pytest.ini_options] addopts = "--import-mode=importlib --strict-markers -ra"`.

### Frontend: Biome

Biome é o equivalente do Ruff para TypeScript: lint e format em um binário só.

### Contrato do Makefile

`install · fmt · lint · typecheck · test · test-bdd · test-int · audit · check (= tudo) · up · down`

### Tidy First no fluxo de commits

Mudanças **estruturais** (renomear, extrair, mover) e **comportamentais** nunca vão no mesmo commit. Os prefixos `tidy:` e `feat:`/`fix:` deixam isso explícito, e um commit `tidy:` nunca altera teste.

## Opções consideradas

| | Ruff ✅ | black + isort + flake8 + bandit | | Poetry ✅ | uv |
|---|---|---|---|---|---|
| Ferramentas | 1 | 4 | | Lock + build + venv | Lock + venv + Python, muito rápido |
| Velocidade | ms | s | | Ok | Muito alta |

O uv seria uma escolha igualmente boa. O Poetry foi mantido porque é requisito explícito (`poetry.lock`).

## Consequências

- ✅ `make check` verde localmente significa CI verde, porque os comandos são os mesmos.
- ⚠️ O hook do mypy roda no venv do projeto (`local`) para enxergar as dependências reais. Ele é mais lento que os demais.
- 🔁 Revisar `select` do Ruff a cada versão nova (`ruff rule --all`).
