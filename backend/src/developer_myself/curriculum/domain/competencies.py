"""Competências (as "skills" da ficha do aprendiz) e quanto cada conteúdo vale para cada uma.

Cada competência pertence a uma das 6 áreas do mapa e tem uma **meta** derivada da
profundidade que o mapa pede para o perfil DevSecOps (Profundo → Especialista, etc.).
Um conteúdo pode contar para mais de uma competência (pesos somam 1).
"""

from dataclasses import dataclass
from enum import StrEnum

from developer_myself.curriculum.domain.catalog import find_entry


class Tier(StrEnum):
    APRENDIZ = "Aprendiz"
    PRATICANTE = "Praticante"
    PROFICIENTE = "Proficiente"
    ESPECIALISTA = "Especialista"

    @property
    def floor(self) -> int:
        return {"Aprendiz": 0, "Praticante": 25, "Proficiente": 50, "Especialista": 75}[self.value]

    @classmethod
    def of(cls, score: float) -> Tier:
        return next(t for t in reversed(list(cls)) if score >= t.floor)


class Area(StrEnum):
    """As áreas, na ordem do mapa + perfil em T (barra horizontal e barra vertical)."""

    FUNDAMENTOS = "Fundamentos"
    FULLSTACK = "Fullstack"
    APPSEC = "AppSec"
    DEVOPS = "DevOps"
    DEVSECOPS = "DevSecOps"
    INTELIGENCIA = "Inteligência"
    DFIR = "DFIR"
    TRANSVERSAIS = "Transversais e idiomas"


@dataclass(frozen=True, slots=True)
class Competency:
    key: str
    name: str
    area: Area
    target: Tier | None  # None = sem meta no mapa


COMPETENCIES: tuple[Competency, ...] = (
    Competency("fundamentos", "Fundamentos de computação", Area.FUNDAMENTOS, Tier.ESPECIALISTA),
    Competency("go", "Go", Area.FUNDAMENTOS, Tier.ESPECIALISTA),
    Competency("python", "Python", Area.FUNDAMENTOS, Tier.PROFICIENTE),
    Competency("engenharia", "Engenharia de software", Area.FUNDAMENTOS, Tier.PROFICIENTE),
    Competency("ageis", "Metodologias ágeis", Area.FUNDAMENTOS, Tier.PROFICIENTE),
    Competency("dados", "Dados e sistemas distribuídos", Area.FUNDAMENTOS, Tier.PROFICIENTE),
    Competency("frontend", "Frontend: TypeScript e React", Area.FULLSTACK, Tier.PROFICIENTE),
    Competency("backend", "Backend e APIs", Area.FULLSTACK, Tier.ESPECIALISTA),
    Competency("ia", "IA e Machine Learning", Area.FULLSTACK, Tier.PRATICANTE),
    Competency("appsec", "AppSec", Area.APPSEC, Tier.ESPECIALISTA),
    Competency("devops", "DevOps", Area.DEVOPS, Tier.ESPECIALISTA),
    Competency("devsecops", "DevSecOps", Area.DEVSECOPS, Tier.ESPECIALISTA),
    Competency("windows", "Windows e Active Directory", Area.FUNDAMENTOS, Tier.ESPECIALISTA),
    Competency("osint", "OSINT", Area.INTELIGENCIA, Tier.PRATICANTE),
    Competency("threat_intel", "Threat Intelligence", Area.INTELIGENCIA, Tier.PRATICANTE),
    Competency("malware", "Análise de malware", Area.INTELIGENCIA, Tier.PRATICANTE),
    Competency("darkweb", "Dark web e cibercrime", Area.INTELIGENCIA, Tier.PRATICANTE),
    Competency("dfir", "DFIR", Area.DFIR, Tier.ESPECIALISTA),
    Competency("comunicacao", "Comunicação e negociação", Area.TRANSVERSAIS, Tier.PROFICIENTE),
    Competency("ingles", "Inglês", Area.TRANSVERSAIS, Tier.PROFICIENTE),
    Competency("espanhol", "Espanhol", Area.TRANSVERSAIS, Tier.PRATICANTE),
    Competency("outros", "Outros", Area.TRANSVERSAIS, None),
)
BY_KEY = {c.key: c for c in COMPETENCIES}

Weights = tuple[tuple[str, float], ...]

SKILLS_BY_TITLE: dict[str, Weights] = {
    # 1. Fundamentos comuns
    "Computação e sistemas operacionais": (("fundamentos", 1.0),),
    "Linux": (("fundamentos", 1.0),),
    "Redes": (("fundamentos", 1.0),),
    "Git e colaboração": (("fundamentos", 0.6), ("engenharia", 0.4)),
    "Learning Go": (("go", 1.0),),
    "Shell and awk": (("fundamentos", 1.0),),
    "TypeScript": (("frontend", 1.0),),
    "Learning Python": (("python", 1.0),),
    "YAML, JSON e HCL": (("devops", 0.5), ("fundamentos", 0.5)),
    "Testes: unitário, integração, ponta a ponta, contrato, carga; TDD; mocks, stubs e fakes": (
        ("engenharia", 1.0),
    ),
    "Design: SOLID, coesão e acoplamento, padrões de projeto, refatoração": (("engenharia", 1.0),),
    "Arquitetura: camadas, hexagonal, monolito modular, microsserviços, orientada a eventos": (
        ("engenharia", 1.0),
    ),
    "Documentação técnica: README, ADR, RFC e modelo C4": (
        ("engenharia", 0.7),
        ("comunicacao", 0.3),
    ),
    "Métodos ágeis: Scrum, Kanban, estimativa, débito técnico": (("ageis", 1.0),),
    "SQL e NoSQL": (("dados", 1.0),),
    "Sistemas distribuídos": (("dados", 0.6), ("backend", 0.4)),
    # 2. Fullstack
    "Frontend: HTML, CSS, JavaScript e o navegador": (("frontend", 1.0),),
    "React": (("frontend", 1.0),),
    "Vite": (("frontend", 1.0),),
    "Designing Web APIs": (("backend", 1.0),),
    "FastAPI": (("backend", 0.6), ("python", 0.4)),
    "Django": (("backend", 0.6), ("python", 0.4)),
    "Gin": (("backend", 0.5), ("go", 0.5)),
    "GORM": (("dados", 0.6), ("go", 0.4)),
    "Kafka, RabbitMQ, Protocol Buffers, NATS e gRPC": (("backend", 0.5), ("dados", 0.5)),
    "Mobile (noção): Flutter e OWASP MASVS": (("frontend", 1.0),),
    "Integração de IA (noção): LLMs, RAG e agentes": (("ia", 1.0),),
    # 3. AppSec
    "Fundamentos de segurança": (("appsec", 1.0),),
    "Criptografia aplicada": (("appsec", 1.0),),
    "Vulnerabilidades como ocorrem e como corrigir no código": (("appsec", 1.0),),
    "Segurança de APIs (OWASP API Security Top 10)": (("appsec", 0.7), ("backend", 0.3)),
    "Identidade e acesso: MFA, sessões, JWT, OAuth 2.0 e OIDC": (("appsec", 1.0),),
    "Ciclo de desenvolvimento seguro (SSDLC) e modelagem de ameaças": (("appsec", 1.0),),
    "SAST/DAST/SCA": (("appsec", 0.6), ("devsecops", 0.4)),
    "Cadeia de suprimentos de software": (("appsec", 0.5), ("devsecops", 0.5)),
    "Privacidade e conformidade (LGPD)": (("appsec", 1.0),),
    "Segurança de IA (noção)": (("appsec", 0.5), ("ia", 0.5)),
    "Gestão de vulnerabilidades": (("appsec", 1.0),),
    # 4. DevOps
    "Cultura DevOps, métricas DORA e SRE": (("devops", 0.7), ("ageis", 0.3)),
    "Docker": (("devops", 1.0),),
    "Kubernetes com Helm e Charts": (("devops", 1.0),),
    "ESTEIRA CI/CD (Jenkins, Bamboo e Github Actions)": (("devops", 1.0),),
    "Infraestrutura como código: Terraform/OpenTofu e Ansible": (("devops", 1.0),),
    "Cloud (AWS)": (("devops", 1.0),),
    "Observability": (("devops", 1.0),),
    "Tráfego em produção: proxy, balanceamento, TLS e CDN": (("devops", 1.0),),
    "Confiabilidade e operação: alta disponibilidade, backup e DR": (("devops", 1.0),),
    "Software sustentável (noção)": (("devops", 1.0),),
    # 5. DevSecOps
    "DevSecOps: segurança no pipeline": (("devsecops", 1.0),),
    "DevSecOps: segurança do próprio CI/CD": (("devsecops", 1.0),),
    "DevSecOps: segurança de containers": (("devsecops", 1.0),),
    "DevSecOps: segurança de Kubernetes": (("devsecops", 1.0),),
    "DevSecOps: segurança na cloud": (("devsecops", 1.0),),
    "DevSecOps: gestão de segredos": (("devsecops", 1.0),),
    "DevSecOps: políticas como código e conformidade": (("devsecops", 1.0),),
    "DevSecOps: identidade de workloads e Zero Trust": (("devsecops", 1.0),),
    "DevSecOps: detecção e resposta": (("devsecops", 1.0),),
    "DevSecOps: frameworks de referência (NIST SSDF, DSOMM, SLSA, SAMM, CIS)": (
        ("devsecops", 1.0),
    ),
    # 6. Transversais e conteúdos próprios
    "Competências transversais: comunicação, negociação, escrita e ética": (("comunicacao", 1.0),),
    "Conversas Cruciais": (("comunicacao", 1.0),),
    "Conversação em Inglês": (("ingles", 1.0),),
    "Conversação em Espanhol": (("espanhol", 1.0),),
    "TensorFlow e PyTorch": (("ia", 0.7), ("python", 0.3)),
    # Perfil em T: fundamentos novos, barra horizontal (Inteligência) e barra vertical (DFIR)
    "Windows por dentro: processos, serviços, registro, NTFS, Active Directory e logs de evento": (
        ("windows", 1.0),
    ),
    "PowerShell": (("windows", 0.6), ("dfir", 0.4)),
    "Baixo nível: Assembly x86/x64 básico e formatos de executável PE e ELF": (
        ("malware", 0.6),
        ("fundamentos", 0.4),
    ),
    "Estatística básica": (("dados", 0.6), ("threat_intel", 0.4)),
    "OSINT: requisitos, SOCMINT, geolocalização, infraestrutura e OPSEC": (("osint", 1.0),),
    "Threat Intelligence: ciclo de inteligência, ATT&CK, STIX/TAXII e MISP/OpenCTI": (
        ("threat_intel", 1.0),
    ),
    "Análise de malware: triagem, sandbox, YARA, Sigma e Ghidra básico": (("malware", 1.0),),
    "Dark web e economia do cibercrime": (("darkweb", 1.0),),
    "DFIR: processo e jurídico (NIST SP 800-61, cadeia de custódia, ISO/IEC 27037 e LGPD)": (
        ("dfir", 1.0),
    ),
    "DFIR: aquisição de evidências (disco, memória, triagem ao vivo e nuvem)": (("dfir", 1.0),),
    "DFIR: sistemas de arquivos (NTFS, ext4, MACB e carving)": (("dfir", 1.0),),
    "DFIR: artefatos Windows (registro, execução e uso, logs)": (("dfir", 0.6), ("windows", 0.4)),
    "DFIR: artefatos Linux e macOS": (("dfir", 0.8), ("fundamentos", 0.2)),
    "DFIR: forense de memória (Volatility 3 e MemProcFS)": (("dfir", 0.8), ("malware", 0.2)),
    "DFIR: forense de rede (pcap, Zeek, Suricata e JA3/JA4)": (
        ("dfir", 0.8),
        ("fundamentos", 0.2),
    ),
    "DFIR: linha do tempo (plaso e Timesketch)": (("dfir", 1.0),),
    "DFIR: resposta em escala corporativa (EDR, SIEM, threat hunting e Active Directory)": (
        ("dfir", 0.6),
        ("windows", 0.4),
    ),
    "DFIR: nuvem e containers (CloudTrail, Entra ID, M365 e Kubernetes)": (
        ("dfir", 0.7),
        ("devsecops", 0.3),
    ),
    "DFIR: antiforense e como detectar": (("dfir", 1.0),),
    "DFIR (opcional, noção): forense mobile Android e iOS e MVT": (("dfir", 1.0),),
}


def skills_for(title: str) -> Weights:
    """Pesos do conteúdo por competência; fora do catálogo conta como "Outros"."""
    entry = find_entry(title)
    if entry is None:
        return (("outros", 1.0),)
    return SKILLS_BY_TITLE.get(entry.title, (("outros", 1.0),))
