# Organização da trilha

Gerado em 02/11/2026 a partir da sua trilha real (83 conteúdos) e de **simulações com as regras
do próprio sistema**: até 3 em andamento, competências diferentes, afinidade, revisão diária,
1 ponto por pomodoro pontuado, Intermediário em 10 pontos e Avançado em 30. As simulações supõem
que toda sessão pontua, então servem para **comparar** ordens e ritmos, e não como promessa de data.

> **Nada aqui foi aplicado ao banco além das 20 adições.** A nova ordem da fila só será
> aplicada com a sua confirmação.

## 1. Situação atual

- **83 conteúdos**: 63 que já existiam + 20 novos do perfil em T (4 fundamentos, 4 de
  Inteligência e 12 de DFIR). "Trilha de 30 dias: Inteligência e Investigação" foi removida por você
  e ficou coberta pela barra horizontal.
- **Em andamento (3 vagas):** Designing Web APIs · Learning Go · React. Learning Go e React foram liberados
  automaticamente pela regra nova (3 em paralelo), pela fila atual e pela afinidade com Backend.
- **Ritmo padrão:** 3h30/dia (7 pomodoros de 30 min) sem folga. Dá para mudar na tela **Semana**.

## 2. Sobreposições (tratadas sem duplicar)

| Tema | Onde aparece | Como ficou |
|---|---|---|
| Redes, Linux, Go, Python, Bash | Mapa e lista DFIR | Os conteúdos existentes ganharam os tópicos novos (ext4, journald, ferramentas DFIR em Python) |
| PowerShell | Programação, scripts maliciosos, logs | 1 conteúdo novo + tópicos em Malware e em Artefatos Windows |
| NTFS | Windows por dentro e Sistemas de arquivos | Uso/administração no primeiro e estruturas forenses ($MFT, $UsnJrnl) no segundo |
| Active Directory | Windows por dentro e Resposta corporativa | Como funciona no primeiro e rastros de ataque (Kerberoasting, DCSync) no segundo |
| Sigma | Malware e Resposta corporativa (SIEM) | Escrever regras em Malware e operar no SIEM em DFIR |
| LGPD | Privacidade (AppSec) e Processo e jurídico (DFIR) | Bases legais no primeiro e comunicação de incidente à ANPD no segundo |
| CloudTrail e audit log do Kubernetes | Cloud, DevSecOps e DFIR nuvem | Configurar e proteger no DevOps/DevSecOps e investigar no DFIR |
| Criptografia aplicada, escrita técnica | Mapa e lista DFIR | Já existiam; "escrita técnica" entrou em Documentação técnica |

## 3. Proposta: 3 trilhas paralelas, uma por vaga

Cada vaga em andamento puxa a próxima da **sua** trilha. A fila intercala as três (A, B, C, A, B, C…),
e a regra de afinidade escolhe o próximo que mais se interliga com o que já está aberto.

### Trilha A — Sistemas e Blue Team → DFIR (barra vertical)
| # | Conteúdo | Competência | Profundidade | Início previsto |
|---|---|---|---|---|
| 1 | Linux | Fundamentos de computação | Profundo | 04/11/2026 |
| 2 | Redes | Fundamentos de computação | Profundo | 10/11/2026 |
| 3 | Windows por dentro: processos, serviços, registro, NTFS, Active Directory e logs de evento | Windows e Active Directory | Profundo | 06/11/2026 |
| 4 | PowerShell | Windows e Active Directory | Funcional | 16/11/2026 |
| 5 | Computação e sistemas operacionais | Fundamentos de computação | Profundo | 20/11/2026 |
| 6 | Shell and awk | Fundamentos de computação | Funcional | 28/11/2026 |
| 7 | DFIR: processo e jurídico (NIST SP 800-61, cadeia de custódia, ISO/IEC 27037 e LGPD) | DFIR | Profundo | 07/12/2026 |
| 8 | DFIR: aquisição de evidências (disco, memória, triagem ao vivo e nuvem) | DFIR | Profundo | 13/12/2026 |
| 9 | DFIR: sistemas de arquivos (NTFS, ext4, MACB e carving) | DFIR | Profundo | 22/12/2026 |
| 10 | DFIR: artefatos Windows (registro, execução e uso, logs) | DFIR | Profundo | 04/01/2027 |
| 11 | DFIR: artefatos Linux e macOS | DFIR | Profundo | 12/01/2027 |
| 12 | DFIR: forense de memória (Volatility 3 e MemProcFS) | DFIR | Profundo | 17/01/2027 |
| 13 | DFIR: forense de rede (pcap, Zeek, Suricata e JA3/JA4) | DFIR | Profundo | 22/01/2027 |
| 14 | DFIR: linha do tempo (plaso e Timesketch) | DFIR | Profundo | 27/01/2027 |
| 15 | DFIR: resposta em escala corporativa (EDR, SIEM, threat hunting e Active Directory) | DFIR | Profundo | 01/02/2027 |
| 16 | DFIR: nuvem e containers (CloudTrail, Entra ID, M365 e Kubernetes) | DFIR | Profundo | 06/02/2027 |
| 17 | DFIR: antiforense e como detectar | DFIR | Profundo | 11/02/2027 |
| 18 | DFIR (opcional, noção): forense mobile Android e iOS e MVT | DFIR | Noção | 16/02/2027 |

### Trilha B — Segurança e Inteligência (AppSec + barra horizontal)
| # | Conteúdo | Competência | Profundidade | Início previsto |
|---|---|---|---|---|
| 1 | Fundamentos de segurança | AppSec | Profundo | 06/11/2026 |
| 2 | Criptografia aplicada | AppSec | Funcional | 11/11/2026 |
| 3 | Vulnerabilidades como ocorrem e como corrigir no código | AppSec | Profundo | 16/11/2026 |
| 4 | OSINT: requisitos, SOCMINT, geolocalização, infraestrutura e OPSEC | OSINT | Funcional | 02/12/2026 |
| 5 | Baixo nível: Assembly x86/x64 básico e formatos de executável PE e ELF | Análise de malware | Funcional | 03/12/2026 |
| 6 | Análise de malware: triagem, sandbox, YARA, Sigma e Ghidra básico | Análise de malware | Funcional | 08/12/2026 |
| 7 | Threat Intelligence: ciclo de inteligência, ATT&CK, STIX/TAXII e MISP/OpenCTI | Threat Intelligence | Funcional | 08/12/2026 |
| 8 | Dark web e economia do cibercrime | Dark web e cibercrime | Funcional | 13/12/2026 |
| 9 | Identidade e acesso: MFA, sessões, JWT, OAuth 2.0 e OIDC | AppSec | Profundo | 23/12/2026 |
| 10 | SAST/DAST/SCA | AppSec | Profundo | 30/12/2026 |
| 11 | Segurança de APIs (OWASP API Security Top 10) | AppSec | Profundo | 07/01/2027 |
| 12 | Ciclo de desenvolvimento seguro (SSDLC) e modelagem de ameaças | AppSec | Profundo | 14/01/2027 |
| 13 | Cadeia de suprimentos de software | AppSec | Profundo | 19/01/2027 |
| 14 | Gestão de vulnerabilidades | AppSec | Funcional | 24/01/2027 |
| 15 | Privacidade e conformidade (LGPD) | AppSec | Funcional | 29/01/2027 |
| 16 | Segurança de IA (noção) | AppSec | Noção | 03/02/2027 |

### Trilha C — Engenharia e Ops → DevSecOps
| # | Conteúdo | Competência | Profundidade | Início previsto |
|---|---|---|---|---|
| 1 | Learning Python | Python | Funcional | 23/11/2026 |
| 2 | Git e colaboração | Fundamentos de computação | Profundo | 15/11/2026 |
| 3 | Conversação em Inglês | Inglês | Funcional | 28/11/2026 |
| 4 | Docker | DevOps | Profundo | 21/11/2026 |
| 5 | ESTEIRA CI/CD (Jenkins, Bamboo e Github Actions) | DevOps | Profundo | 26/11/2026 |
| 6 | SQL e NoSQL | Dados e sistemas distribuídos | Funcional | 16/12/2026 |
| 7 | Kubernetes com Helm e Charts | DevOps | Profundo | 18/12/2026 |
| 8 | Estatística básica | Dados e sistemas distribuídos | Funcional | 21/12/2026 |
| 9 | Cloud (AWS) | DevOps | Profundo | 28/12/2026 |
| 10 | Infraestrutura como código: Terraform/OpenTofu e Ansible | DevOps | Profundo | 02/01/2027 |
| 11 | Observability | DevOps | Profundo | 09/01/2027 |
| 12 | DevSecOps: segurança no pipeline | DevSecOps | Profundo | 27/12/2026 |
| 13 | DevSecOps: segurança de containers | DevSecOps | Profundo | 06/01/2027 |
| 14 | DevSecOps: segurança do próprio CI/CD | DevSecOps | Profundo | 16/01/2027 |
| 15 | DevSecOps: segurança de Kubernetes | DevSecOps | Profundo | 26/01/2027 |
| 16 | DevSecOps: segurança na cloud | DevSecOps | Profundo | 04/02/2027 |
| 17 | DevSecOps: gestão de segredos | DevSecOps | Profundo | 12/02/2027 |
| 18 | DevSecOps: políticas como código e conformidade | DevSecOps | Profundo | 17/02/2027 |
| 19 | DevSecOps: detecção e resposta | DevSecOps | Profundo | 22/02/2027 |
| 20 | DevSecOps: identidade de workloads e Zero Trust | DevSecOps | Profundo | 27/02/2027 |
| 21 | DevSecOps: frameworks de referência (NIST SSDF, DSOMM, SLSA, SAMM, CIS) | DevSecOps | Profundo | 07/03/2027 |
| 22 | Cultura DevOps, métricas DORA e SRE | DevOps | Profundo | 09/02/2027 |
| 23 | YAML, JSON e HCL | DevOps | Funcional | 19/02/2027 |
| 24 | Testes: unitário, integração, ponta a ponta, contrato, carga; TDD; mocks, stubs e fakes | Engenharia de software | Funcional | 21/02/2027 |
| 25 | Arquitetura: camadas, hexagonal, monolito modular, microsserviços, orientada a eventos | Engenharia de software | Funcional | 28/02/2027 |
| 26 | Design: SOLID, coesão e acoplamento, padrões de projeto, refatoração | Engenharia de software | Funcional | 05/03/2027 |
| 27 | Documentação técnica: README, ADR, RFC e modelo C4 | Engenharia de software | Funcional | 11/03/2027 |
| 28 | Conversas Cruciais | Comunicação e negociação | Funcional | 04/03/2027 |
| 29 | Competências transversais: comunicação, negociação, escrita e ética | Comunicação e negociação | Funcional | 28/03/2027 |
| 30 | Métodos ágeis: Scrum, Kanban, estimativa, débito técnico | Metodologias ágeis | Funcional | 25/02/2027 |
| 31 | Sistemas distribuídos | Dados e sistemas distribuídos | Funcional | 16/03/2027 |
| 32 | Tráfego em produção: proxy, balanceamento, TLS e CDN | DevOps | Funcional | 10/03/2027 |
| 33 | Confiabilidade e operação: alta disponibilidade, backup e DR | DevOps | Funcional | 02/04/2027 |
| 34 | FastAPI | Backend e APIs | Funcional | 12/03/2027 |

### Fim da fila — fora do foco DevSecOps + DFIR
Frontend: HTML, CSS, JavaScript e o navegador, TypeScript, Vite, Gin, GORM, Kafka, RabbitMQ, Protocol Buffers, NATS e gRPC, Django, Integração de IA (noção): LLMs, RAG e agentes, Mobile (noção): Flutter e OWASP MASVS, Software sustentável (noção), TensorFlow e PyTorch, Conversação em Espanhol.

## 4. Ordem atual × proposta (3h30/dia, sem folga)

| Marco | Ordem atual | Ordem proposta |
|---|---|---|
| Windows por dentro começa | 23/02/2027 | **06/11/2026** |
| 1º conteúdo de DFIR começa | 14/03/2027 | **07/12/2026** |
| Todos os de DFIR iniciados | 15/04/2027 | **16/02/2027** |
| Todos os de DFIR em Intermediário | 17/04/2027 | **21/02/2027** |
| Inteligência toda iniciada | 13/03/2027 | **13/12/2026** |
| 1º de DevSecOps começa | 14/01/2027 | 27/12/2026 |
| Tudo no Avançado | 29/10/2027 | 28/10/2027 |

**Leitura:** a proposta antecipa DFIR e Inteligência em cerca de 3 meses sem atrasar o fim. O fim
não muda porque o volume de trabalho é o mesmo e porque o gargalo do Avançado é a **revisão**
(dias 11 a 30 de cada conteúdo), limitada a 2 pomodoros por dia.

## 5. Ritmo (ordem proposta)

| Ritmo | Todos iniciados | Todos em Intermediário | Todos em Avançado |
|---|---|---|---|
| 3h00/dia | 24/05/2027 | 29/05/2027 | 26/12/2027 |
| 3h30/dia | 12/04/2027 | 17/04/2027 | 28/10/2027 |
| 4h00/dia | 15/03/2027 | 19/03/2027 | 13/09/2027 |
| 3h30/dia, folga dom | 08/05/2027 | 14/05/2027 | 27/12/2027 |

## 6. O que está faltando (sugestões; nada foi adicionado)

Lacunas em relação ao objetivo **DevSecOps + DFIR**, que não aparecem nem no mapa nem na lista:

1. **Análise de e-mail e phishing**: cabeçalhos, SPF/DKIM/DMARC, anexos e links. É um dos incidentes mais comuns na resposta a incidentes.
2. **Engenharia de detecção (detection-as-code)**: ciclo de vida de regras Sigma, testes de detecção e cobertura do ATT&CK. A lista cita Sigma, mas não o processo.
3. **Emulação de adversário / purple team**: Atomic Red Team e Caldera, para gerar os rastros que você vai investigar.
4. **Hardening de Windows e AD**: tiering, LAPS e GPOs de segurança. É o lado defensivo do "Windows por dentro".
5. **Gestão de casos de incidente**: TheHive/Cortex e a integração com MISP.
6. **A 5ª área da barra horizontal**: a lista diz "5 áreas", mas descreve 4 (OSINT, Threat Intelligence, Malware e Dark web). Qual é a quinta?

## 7. O que poderia sair ou virar "Noção"

Hoje todo conteúdo custa 30 dias (30 pomodoros), inclusive os de profundidade "Noção". Estes estão
fora do foco ou se sobrepõem a outros:

| Conteúdo | Por quê | Sugestão |
|---|---|---|
| Django | Sobrepõe FastAPI (os dois são web em Python) | Sair ou virar Noção |
| Vite | É uma parte do React | Juntar ao React |
| TensorFlow e PyTorch | Fora do foco DevSecOps + DFIR | Noção (a estatística básica cobre o essencial) |
| GORM, Gin, Kafka/NATS/gRPC | Útil para backend em Go, periférico ao foco | Noção |
| Conversação em Espanhol | Fora do foco técnico | Manter se for objetivo pessoal |
| Mobile, Software sustentável, Segurança de IA, Integração de IA, forense mobile | Já marcados como Noção | Ver a recomendação abaixo |

**Recomendação de regra (não implementada):** conteúdos "Noção" com cronograma de **10 dias**,
concluídos no **Intermediário**. A conta é rápida: são cerca de 9 conteúdos × 20 pomodoros, ou ~180
pomodoros, quase um mês a menos no ritmo de 3h30.

## 8. Recomendação concreta

1. **Aplicar a ordem proposta** (seção 3). O comando `reorder_queue` já existe e a simulação está
   pronta; nada muda nos pontos, só a ordem da fila.
2. **React já está em andamento** pela regra nova, mas está no fim da trilha proposta. Como ainda
   não tem progresso, dá para tirá-lo e readicionar no fim da fila, liberando a vaga para a Trilha A
   (Linux → Windows por dentro).
3. **Manter 3h30/dia** com 1 dia de folga, se possível. O custo é de ~2 meses no fim (veja a seção
   5), mas sustenta o ritmo por um ano.
4. Decidir sobre as lacunas (seção 6) e sobre a regra de "Noção" (seção 7).
