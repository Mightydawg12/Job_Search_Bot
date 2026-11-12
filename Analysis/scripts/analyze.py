"""Count skills, certifications, levels and experience asks in jobs_snapshot.json.

    python3 Analysis/scripts/analyze.py     # prints the tables, writes Analysis/data/stats.json
"""
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "data"
data = json.loads((HERE / "jobs_snapshot.json").read_text())
jobs = data["company_jobs"]
titles = data["all_titles"]

# label -> regex (searched in lower-cased description)
SKILLS = {
    # OS / core
    "Linux (any)": r"\blinux\b", "RHEL / Red Hat": r"\brhel\b|red hat", "Ubuntu/Debian": r"ubuntu|debian",
    "Windows Server": r"windows server", "Bash / shell": r"\bbash\b|shell script",
    "Python": r"\bpython\b", "Go (Golang)": r"\bgolang\b|\bgo\b(?= |,|/)(?!.{0,3}(to|live|-to))",
    "Rust": r"\brust\b", "Java": r"\bjava\b", "C/C++": r"\bc\+\+|\bc/c\+\+",
    # automation / IaC
    "Ansible": r"ansible", "Terraform": r"terraform", "Puppet": r"\bpuppet\b", "Chef": r"\bchef\b",
    "SaltStack": r"saltstack|\bsalt\b", "Pulumi": r"pulumi", "Packer": r"\bpacker\b",
    "Infrastructure as Code (phrase)": r"infrastructure[- ]as[- ]code|\biac\b",
    # containers
    "Kubernetes": r"kubernetes|\bk8s\b", "Docker / containers": r"docker|container",
    "Helm": r"\bhelm\b", "OpenShift": r"openshift", "Service mesh (Istio/Envoy)": r"istio|envoy|service mesh",
    "ArgoCD / GitOps": r"argo ?cd|gitops|flux",
    # cloud
    "AWS": r"\baws\b|amazon web services", "GCP": r"\bgcp\b|google cloud", "Azure": r"\bazure\b",
    "Multi-cloud / hybrid": r"multi-cloud|multicloud|hybrid cloud",
    # CI/CD
    "CI/CD (any)": r"ci/cd|continuous integration|continuous delivery|continuous deployment",
    "GitHub Actions": r"github actions", "Jenkins": r"jenkins", "GitLab CI": r"gitlab ci|gitlab-ci",
    "Git": r"\bgit\b",
    # observability
    "Prometheus": r"prometheus", "Grafana": r"grafana", "Datadog": r"datadog", "Splunk": r"splunk",
    "ELK / OpenSearch": r"elasticsearch|\belk\b|opensearch|kibana", "OpenTelemetry": r"opentelemetry|otel",
    "Observability (word)": r"observability", "On-call / incident response": r"on-call|on call|incident response|pager",
    "SLOs / SLIs": r"\bslos?\b|\bslis?\b|error budget",
    # networking / systems
    "Networking (TCP/IP, DNS)": r"tcp/ip|\bdns\b|network(ing)? (fundamentals|protocols|troubleshoot)|\bvpc\b|subnet|firewall", "Load balancers": r"load balanc|haproxy|nginx",
    "BGP / routing": r"\bbgp\b|routing", "Storage (NFS/Ceph/SAN)": r"\bnfs\b|ceph|\bsan\b|storage system|distributed storage|block storage|object storage|lustre|weka|vast data",
    "Virtualization (VMware/KVM)": r"vmware|vsphere|\bkvm\b|proxmox|hypervisor",
    "Bare metal / data center": r"bare[- ]metal|data ?center|datacenter",
    "Performance tuning / kernel": r"kernel|performance tuning|systemd",
    # security
    "Security / hardening": r"hardening|\bstig\b|\bcis\b benchmark|cis benchmarks",
    "Vulnerability mgmt / patching": r"vulnerabilit|patch", "IAM / identity (Okta, AD, LDAP)": r"\biam\b|active directory|\bldap\b|identity and access|identity management|\bsso\b|saml|oauth",
    "Compliance (SOC 2, FedRAMP, NIST)": r"soc ?2|fedramp|\bnist\b|hipaa|pci[- ]dss|iso ?27001|\bstig\b|\bcmmc\b|il[245]\b",
    "Secrets / Vault / PKI": r"vault|\bpki\b|secrets management|certificates",
    # AI / GPU
    "GPU / CUDA / NVIDIA": r"\bgpu|cuda|nvidia", "HPC / Slurm": r"\bhpc\b|slurm|high[- ]performance comput",
    "ML / AI infra (training/inference clusters)": r"machine learning infra|\bml infra|ml platform|llm|inference|training (cluster|job|workload|run)|ai infrastructure|ai workloads",
    # data
    "SQL / Postgres / MySQL": r"\bsql\b|postgres|mysql", "Kafka / messaging": r"kafka|rabbitmq|pub/sub",
    # endpoint / IT
    "MDM / Jamf / Intune": r"\bjamf\b|intune|\bmdm\b", "Google Workspace / M365": r"google workspace|microsoft 365|office 365|\bm365\b",
}
CERTS = {
    "RHCSA": r"\brhcsa\b", "RHCE": r"\brhce\b", "RHCA": r"\brhca\b", "Red Hat cert (generic)": r"red hat certified",
    "LFCS": r"\blfcs\b", "CKA": r"\bcka\b", "CKAD": r"\bckad\b", "CKS": r"\bcks\b",
    "Kubernetes cert (generic)": r"kubernetes certif|certified kubernetes",
    "AWS cert (any)": r"aws certified|aws certification|aws solutions architect|aws sysops|aws devops",
    "Azure cert (any)": r"azure administrator|az-104|az-400|azure certif",
    "GCP cert (any)": r"google cloud certified|professional cloud",
    "Terraform Associate": r"terraform associate|hashicorp certif",
    "Security+": r"security\+|security plus|sec\+", "CISSP": r"cissp", "CCNA": r"\bccna\b",
    "CompTIA (any)": r"comptia", "Linux+": r"linux\+", "ITIL": r"\bitil\b",
    "DoD 8570 / 8140": r"8570|8140", "Clearance required/preferred": r"clearance|ts/sci|top secret|secret clearance",
    "Degree required (BS/BA)": r"bachelor|b\.s\.|\bbs\b|\bba\b|degree",
}
LEVELS = [
    ("Intern / new grad", r"intern|new grad|early career|graduate|apprentice"),
    ("Junior / I / Associate", r"\bjunior\b|\bjr\b|\bassociate\b|\b(i|1)\b$|\bentry"),
    ("Manager / Head / Director", r"manager|\bhead\b|director|\bvp\b"),
    ("Principal / Distinguished", r"principal|distinguished|fellow"),
    ("Staff", r"\bstaff\b"),
    ("Lead", r"\blead\b"),
    ("Senior / Sr / III", r"senior|\bsr\b|\biii\b|\b3\b"),
    ("Mid / II / no level", r".*"),
]
FAMILIES = [
    ("SRE / Reliability", r"reliability|\bsre\b"),
    ("DevOps", r"devops|dev ops"),
    ("Platform", r"platform"),
    ("Cloud", r"cloud"),
    ("Security / Vuln", r"security|vulnerab|identity|iam"),
    ("Linux / Unix / Sysadmin", r"linux|unix|rhel|system(s)? admin|sysadmin"),
    ("Infrastructure", r"infrastructure|infra\b"),
    ("Production / Tech Ops / DC / HPC", r"production|technical operations|data ?center|hpc|fleet|hardware ops"),
    ("IT / Enterprise / Corp systems", r"\bit\b|enterprise|corporate|workplace"),
    ("Systems Engineer (generic)", r"systems? engineer"),
    ("Software Engineer (infra-flavored)", r"software engineer|developer"),
    ("Other", r".*"),
]
YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(?:\d{1,2})?\s*\+?\s*years?", re.I)


def pct(n, d):
    return f"{n:4d}  {100*n/d:5.1f}%"


def count(table, texts):
    c = Counter()
    for t in texts:
        for label, rx in table.items():
            if re.search(rx, t):
                c[label] += 1
    return c


def first(table, text):
    for label, rx in table:
        if re.search(rx, text):
            return label


def main():
    texts = [j["description"].lower() for j in jobs]
    n = len(texts)
    stats = {"n_company_jobs": n, "n_titles": len(titles)}

    for name, table in (("skills", SKILLS), ("certs", CERTS)):
        c = count(table, texts)
        stats[name] = {k: c[k] for k in table}
        print(f"\n== {name.upper()} (share of {n} postings with full text)")
        for k, v in c.most_common():
            print(f"  {k:38s}{pct(v, n)}")

    company_keys = {(j["company"].lower(), j["title"].lower()) for j in jobs}
    import re as _re
    def norm(x): return _re.sub(r"[^a-z0-9 ]+", " ", x.lower()).split()
    ck = {(" ".join(norm(c)), " ".join(norm(t))) for c, t in company_keys}
    board = [t for t in titles if (t["company"], t["title"]) not in ck]
    for label, subset in (("BOARD (LinkedIn/Indeed) titles", board), ("COMPANY-FEED titles", [t for t in titles if t not in board])):
        c = Counter(first(LEVELS, t["title"]) for t in subset)
        stats[label] = dict(c)
        print(f"\n== LEVEL, {label}, of {len(subset)}")
        for k, v in c.most_common():
            print(f"  {k:38s}{pct(v, len(subset))}")
    stats["board_titles"] = board
    lv = Counter(first(LEVELS, t["title"]) for t in titles)
    fam = Counter(first(FAMILIES, t["title"]) for t in titles)
    stats["levels"], stats["families"] = dict(lv), dict(fam)
    for name, c in (("LEVEL (from all titles)", lv), ("JOB FAMILY (from all titles)", fam)):
        print(f"\n== {name}, of {len(titles)}")
        for k, v in c.most_common():
            print(f"  {k:38s}{pct(v, len(titles))}")

    yrs = []
    for t in texts:
        m = [int(x) for x in YEARS.findall(t[:8000]) if 1 <= int(x) <= 20]
        if m:
            yrs.append(min(m))
    yc = Counter("1-2" if y <= 2 else "3-4" if y <= 4 else "5-6" if y <= 6 else "7-9" if y <= 9 else "10+" for y in yrs)
    stats["min_years"] = dict(yc)
    print(f"\n== MINIMUM YEARS ASKED ({len(yrs)} postings state a number)")
    for k in ("1-2", "3-4", "5-6", "7-9", "10+"):
        print(f"  {k:38s}{pct(yc[k], len(yrs))}")

    comp = Counter(j["company"] for j in jobs)
    stats["by_company"] = dict(comp.most_common())
    print("\n== POSTINGS BY COMPANY (top 20)")
    for k, v in comp.most_common(20):
        print(f"  {k:38s}{v}")

    (HERE / "stats.json").write_text(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
