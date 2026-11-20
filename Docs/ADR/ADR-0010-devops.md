# ADR-0010: DevOps — containers, CI e observabilidade

**Status:** Proposto. Adia AWS/Kubernetes/Prometheus do [ADR-0001](ADR%20-0001-tech.md).
**Data:** 2026-10-31
**Decisores:** Autor do projeto

## Contexto

Há um desenvolvedor e um usuário. O objetivo é feedback rápido e um caminho de deploy repetível, sem operar um cluster.

## Decisão

### Ambiente local: `docker compose`

`api` · `worker` (relay do outbox + consumers) · `mongo` (replica set de 1 nó + init) · `rabbitmq:4-management` · `web` (Vite). A API e o worker usam a **mesma imagem** com comandos diferentes, o que garante que rodam o mesmo código.

### Pipeline (GitHub Actions), cada job chamando `make`

```
lint+typecheck ─▶ unit+bdd ─▶ integration (Testcontainers) ─▶ security (gitleaks, pip-audit, npm audit, Trivy) ─▶ build image ─▶ publish (só master)
```

O pipeline roda em todo PR e em todo push na `master`.

### Entrega contínua (CD)

Depois que o pipeline inteiro fica verde num push na `master`, o job `publish` faz três coisas:

1. Publica a imagem no GitHub Container Registry como `ghcr.io/franciscohonorat/developer-myself`, com as tags `<sha do commit>` e `latest`.
2. Gera uma **atestação de proveniência** (SLSA, assinada via OIDC) ligada ao digest da imagem.
3. Escreve o digest no resumo do workflow.

**Deploy contínuo por *pull*.** Quem busca a imagem é a máquina que roda o app, não o CI. Assim não há chave SSH no CI, nenhuma porta fica aberta para a internet e não é preciso runner self-hosted, que é inseguro num repositório público porque PRs de forks rodariam código nele.

Um timer do systemd do usuário (`make autodeploy-on`) roda `scripts/deploy.sh` a cada 5 minutos:

1. faz `docker pull` de `latest` e sai se a imagem não mudou;
2. verifica a **atestação**: só sobe imagem que comprovadamente saiu do CI deste repositório;
3. marca a versão em execução como `developer-myself:previous`;
4. sobe a `api` e o `worker` **pelo digest**;
5. espera o `/readyz` responder; se não responder em 90 s, faz **rollback** para `:previous` e o script falha (aparece no `journalctl`).

`make deploy` roda o mesmo script na hora, e `make deploy TAG=<sha>` fixa uma versão. Do commit verde ao app no ar, o tempo fica em torno de 5 minutos mais o tempo do pipeline.

Limites conhecidos:
- O timer só roda com a sessão do usuário ativa, a menos que se use `loginctl enable-linger`.
- A verificação usa o `gh` autenticado. Sem sessão, o keyring fica trancado, a verificação falha e o deploy não acontece (falha segura).
- As migrações de esquema, se um dia existirem, precisam ser compatíveis com a versão anterior para o rollback funcionar.

### Configuração (12-factor)

Tudo vem do env via `pydantic-settings`. O mesmo artefato roda em dev, CI e produção.

### Observabilidade mínima

- Logs JSON (`structlog`) com `correlation_id` gerado no HTTP e **propagado no envelope dos eventos** ([ADR-0006](ADR-0006-eventos-outbox-rabbitmq.md)). Assim dá para seguir um clique até o consumer.
- `/healthz` (o processo está vivo) e `/readyz` (Mongo e Rabbit respondem).
- Métricas de negócio, como sessões e pontos por dia, viram projeções do `insights` e não Prometheus por enquanto.

### Fluxo de trabalho

Trunk-based, PRs pequenos, Conventional Commits, `tidy:` separado de `feat:`.

## Opções consideradas

| | Compose + 1 VM/PaaS ✅ | Kubernetes (ADR-0001) |
|---|---|---|
| Ops | Baixo | Alto |
| Custo p/ 1 usuário | Centavos | Dezenas de US$/mês |

## Consequências

- ✅ `git clone && make install && make up` sobe tudo.
- 🔁 Kubernetes e Prometheus voltam à mesa quando houver mais de um serviço com escala independente.
