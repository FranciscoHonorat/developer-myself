# Definição de Tecnologias

# Status

Substituído em parte: backend → [ADR-0004](ADR-0004-backend-python-fastapi.md), banco → [ADR-0005](ADR-0005-mongodb.md), infra/K8s/monitoramento → [ADR-0010](ADR-0010-devops.md).

# Contexto

Estamos desenvolvendo um projeto chamado "Developer Myself", que visa organizar e gerenciar o desenvolvimento de habilidades técnicas (hardskill) e comportamentais (softskill). Para alcançar esse objetivo, é essencial escolher as tecnologias adequadas que suportem as funcionalidades desejadas, como repetição espaçada, gamificação, aprendizado ativo e microlearning. A escolha das tecnologias vão levar em consideração fatores como escalabilidade, facilidade de manutenção, suporte da comunidade e compatibilidade com as necessidades do projeto.

# Decisão

Decidimos utilizar as seguintes tecnologias para o desenvolvimento do projeto "Developer Myself":

- **Frontend**: React.js - Uma biblioteca JavaScript popular para construir interfaces de usuário interativas e responsivas.
- **Backend**: Go (Golang) - Uma linguagem de programação eficiente e escalável, ideal para construir APIs e serviços de backend.
- **Banco de Dados**: PostgreSQL - Um sistema de gerenciamento de banco de dados relacional robusto e confiável, adequado para armazenar dados estruturados.
- **Autenticação e Autorização**: Auth2.0 - Um protocolo de autenticação amplamente utilizado para garantir a segurança e o controle de acesso dos usuários.
- **Hospedagem e Infraestrutura**: AWS (Amazon Web Services) - Uma plataforma de serviços em nuvem que oferece escalabilidade, confiabilidade e uma ampla gama de serviços para suportar o desenvolvimento e a operação do projeto.
- **Controle de Versão**: Git - Um sistema de controle de versão distribuído que permite o gerenciamento eficiente do código-fonte e a colaboração entre os desenvolvedores.
- **Gerenciamento de Dependências**: Docker e Kubernetes - Uma plataforma de contêineres que facilita a criação, implantação e execução de aplicativos em ambientes isolados e consistentes.
- **Monitoramento e Logging**: Prometheus e Grafana - Ferramentas para monitoramento de desempenho e visualização de métricas, permitindo a identificação de problemas e a otimização do sistema.
- **Testes Automatizados**: Jest e Go Test - Ferramentas para a criação e execução de testes automatizados, garantindo a qualidade e a confiabilidade do código.
- **Documentação**: Swagger - Uma ferramenta para gerar documentação interativa da API, facilitando a compreensão e o uso dos endpoints pelos desenvolvedores.

# Conformidade

As tecnologias escolhidas estão em conformidade com as melhores práticas de desenvolvimento de software, garantindo a escalabilidade, segurança e eficiência do projeto. Além disso, todas as tecnologias selecionadas possuem uma comunidade ativa e suporte contínuo, o que facilita a resolução de problemas e a implementação de novas funcionalidades.
