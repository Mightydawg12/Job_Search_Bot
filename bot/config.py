"""
Job Search Bot settings. Edit freely — it's plain Python.

Two resumes, two search categories, two Telegram messages per run:
  SENIOR  resumes/senior/  Linux / infrastructure, 6+ yrs.
          Junior up to Lead (hands-on). Not Staff, Principal, Manager, Director, Architect.
  JUNIOR  resumes/junior/  IT support / junior infrastructure, 2+ yrs.
          Entry level up to Senior *support* roles. Not Lead, Manager, Director, Architect.
Titles find the jobs; the posting decides eligibility (years asked, fit score). A job that
fits both categories appears in both messages. Newest first.
"""


# ---------------------------------------------------------------------------
# 1. What to search on LinkedIn / Indeed / ZipRecruiter / Glassdoor.
#    Each line = one search per board per run. Boolean OR works on all of them.
#    More lines = more jobs, but longer runs (GitHub minutes) and more blocking.
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    # --- SENIOR: Linux / infrastructure ---
    '"linux administrator" OR "linux systems administrator" OR "linux engineer" OR "linux systems engineer" OR "unix administrator" OR "rhel" OR "red hat administrator"',
    '"systems administrator" OR "systems engineer" OR "infrastructure engineer" OR "server administrator" OR "infrastructure administrator" OR "systems integration engineer"',
    '"site reliability engineer" OR "devops engineer" OR "platform engineer" OR "cloud engineer" OR "cloud operations engineer" OR "production engineer" OR "production support engineer"',
    '"ansible" OR "puppet" OR "terraform" OR "configuration management engineer" OR "infrastructure automation engineer" OR "virtualization engineer" OR "vmware engineer"',
    '"linux security engineer" OR "infrastructure security engineer" OR "linux support engineer" OR "technical support engineer" OR "it operations engineer" OR "data center systems engineer"',
    # --- JUNIOR: IT support / junior infrastructure ---
    '"help desk" OR "service desk" OR "desktop support" OR "it support" OR "technical support" OR "it technician"',
    '"computer technician" OR "pc technician" OR "field service technician" OR "end user support" OR "endpoint" OR "workstation support" OR "application support"',
    '"junior system administrator" OR "associate system administrator" OR "junior linux" OR "noc technician" OR "noc analyst" OR "data center technician" OR "network support technician"',
    '"cloud support" OR "junior devops" OR "junior cloud engineer" OR "it operations analyst" OR "iam analyst" OR "identity and access management analyst" OR "soc analyst" OR "it asset"',
]

# How far back each search looks (hours). Runs are hourly, so 2 gives overlap;
# duplicates are filtered out anyway.
HOURS_OLD = 2
RESULTS_PER_SEARCH = 40

# US only (remote, California, rest of US). Jobs located outside the US are always dropped,
# from every source. ("Remote - Worldwide" counts as remote and is kept.)
US_LOCATION = "United States"

# Job boards searched through python-jobspy, each with every SEARCH_QUERIES line.
# Each adds run time (GitHub minutes). Remove one if it keeps failing.
BOARD_SITES = ["linkedin", "indeed", "zip_recruiter", "glassdoor"]
BOARD_LABEL = {"linkedin": "LinkedIn", "indeed": "Indeed", "zip_recruiter": "ZipRecruiter", "glassdoor": "Glassdoor"}

# Free remote-job feeds (official APIs / RSS, no key needed). Remote OK asks to be credited
# as the source, which the alert does ("Remote OK").
REMOTE_FEEDS = True


# ---------------------------------------------------------------------------
# 2. Categories. A job is FOUND by its title (STRONG pattern, or WEAK pattern plus a
#    qualifier word in the title or description), then must be ELIGIBLE (level, years
#    asked, fit). Case-insensitive regex.
# ---------------------------------------------------------------------------
TITLES = {
    "senior": {
        "strong": [
            r"\blinux\b", r"\bunix\b", r"\brhel\b", r"red ?hat", r"\bsys ?admin", r"\bsystems? administrat",
            r"server (administrat|engineer)",
            r"infrastructure (engineer|administrat|automation|security|reliability|systems|operations|specialist)",
            r"cloud (systems|infrastructure|operations|ops)? ?(engineer|administrat)", r"\baws (systems |cloud |infrastructure )?engineer",
            r"dev ?ops", r"site reliability", r"\bsre\b", r"production (systems )?engineer", r"production support engineer",
            r"\bansible\b", r"\bpuppet\b", r"\bterraform\b", r"configuration management",
            r"(linux|systems|it) operations engineer", r"virtualization", r"vmware",
            r"(linux|infrastructure) security engineer", r"(linux|technical) support engineer",
            r"data ?center (systems )?engineer", r"patch(ing)? (management|engineer|administrat)",
            r"vulnerability (management|remediation) (engineer|analyst|specialist)",
            r"\bhpc\b", r"high[- ]performance computing", r"technical operations|\btechops\b",
        ],
        "weak": [
            r"systems? engineer", r"platform engineer", r"automation engineer", r"reliability engineer",
            r"systems integration", r"\bit engineer", r"operations engineer",
        ],
        "qualifiers": r"linux|unix|rhel|red ?hat|ubuntu|centos|ansible|terraform|puppet|chef|kubernetes|k8s|docker|aws|azure|gcp|cloud|infrastructure|devops|sre|server|bash|vmware",
    },
    "junior": {
        "strong": [
            r"help ?desk", r"service desk", r"desktop (support|technician|analyst|specialist)", r"deskside",
            r"\bit support", r"tech(nical)? support", r"\btier ?(1|2|i|ii) support", r"technology support",
            r"\bit (technician|specialist|assistant|associate|coordinator)\b", r"\bit operations (technician|analyst|specialist)",
            r"computer (support|technician|specialist)", r"\bpc (support|technician|tech)\b",
            r"end[- ]user (support|computing|services|technician|specialist)", r"endpoint (support|administrat|engineer|technician)",
            r"workstation (support|technician)", r"(hardware|software) support (technician|specialist)",
            r"\bsystems? administrat", r"\bsys ?admin", r"\blinux (systems? )?(administrat|admin\b|support)",
            r"network (support|operations center) (technician|analyst|specialist)", r"\bnoc\b", r"network operations center",
            r"(junior|jr|associate|entry).{0,15}network administrat",
            r"data ?center (technician|operations|ops)", r"infrastructure (support|operations) (technician|analyst|specialist)",
            r"cloud support", r"cloud operations (technician|analyst|associate)",
            r"(junior|jr|associate|entry).{0,15}(cloud|devops|systems|linux|infrastructure) (engineer|administrat)",
            r"\bit systems (specialist|administrat|analyst)", r"\bit asset", r"\bit deployment", r"\bit provisioning",
            r"(imaging|deployment) technician",
            r"identity (and|&) access management (analyst|specialist|administrat)", r"\biam (support )?(analyst|specialist|administrat)",
            r"access management (analyst|specialist)", r"\bit monitoring", r"production support analyst",
            r"\bsoc analyst", r"(junior|jr|associate|entry).{0,15}security analyst", r"security analyst (i|1|tier ?1)\b",
        ],
        "weak": [
            r"field (support|service) (technician|engineer)", r"application support (specialist|analyst|engineer)",
            r"support (technician|specialist|analyst)", r"\bit analyst", r"operations technician",
        ],
        "qualifiers": r"windows|active directory|help ?desk|desktop|computer|laptop|network|\bit support|ticket|microsoft 365|office 365|servicenow|linux|server|workstation|printer|end[- ]users?",
    },
}

# Never wanted, in either category (title).
EXCLUDE_TITLE_PATTERNS = [
    r"\bsales\b", r"sales engineer", r"solutions? engineer", r"account (executive|manager)", r"recruit",
    r"marketing", r"\bintern(ship)?\b", r"embedded", r"firmware", r"kernel", r"front[- ]?end", r"android", r"\bios\b",
    r"mobile", r"machine learning engineer", r"data scientist", r"test automation", r"\bqa\b", r"quality assurance",
    r"hardware (engineer|design|developer)", r"mechanical", r"electrical", r"\brf\b", r"propulsion", r"avionics",
    r"teacher", r"professor", r"thermal", r"\bpower\b", r"hvac", r"financ", r"product manager", r"program manager",
    r"physical security", r"\bhse\b", r"vice president", r"\bvp\b", r"\bchief\b", r"\bhead of\b",
    # Non-IT "technician" and "support" jobs
    r"biomedical|medical (equipment|device)|elevator|automotive|diesel|\bmechanic\b|solar|wind turbine|appliance|copier",
    r"pharmac|\bnurs|clinical|dental|veterinar|pest|janitor|custodian|warehouse|forklift|cable install|telecom installer",
    r"m/w/d|w/m/d|f/m/d|m/f/d|\(w/m\)|\(m/w\)",   # German-language postings
    # Postings that require a language you don't speak (French is fine)
    r"\b(german|dutch|spanish|portuguese|italian|japanese|korean|mandarin|cantonese|chinese|polish|"
    r"swedish|danish|norwegian|finnish|nordic|arabic|hebrew|turkish|russian|czech|hungarian|greek)\b",
]

# ---------------------------------------------------------------------------
# 2b. Eligibility per category: highest level allowed, and years asked.
# ---------------------------------------------------------------------------
LEVEL_EXCLUDE = {
    # Up to Lead / Technical Lead (hands-on). Staff kept out, as asked.
    "senior": [r"\bstaff\b", r"principal", r"distinguished", r"\bfellow\b", r"\bmanager\b", r"\bmgr\b", r"\bdirector\b",
               r"\bhead\b", r"\barchitect", r"\bsupervisor\b", r"member of technical staff", r"\b(v|vi|level ?[5-9])\b"],
    # Up to Senior *support* roles (see JUNIOR_SENIOR_OK). No Lead or above.
    "junior": [r"\bstaff\b", r"principal", r"distinguished", r"\bfellow\b", r"\bmanager\b", r"\bmgr\b", r"\bdirector\b",
               r"\bhead\b", r"\barchitect", r"\bsupervisor\b", r"member of technical staff", r"\blead\b"],
}
# In JUNIOR, a "Senior"/"III" title is fine only if it's a support role (e.g. Senior IT Support Specialist).
JUNIOR_SENIOR_MARKERS = r"\bsenior\b|\bsr\b|\b(iii|iv)\b|level ?(3|4)"
JUNIOR_SENIOR_OK = r"help ?desk|service desk|desktop|\bit support|tech(nical)? support|support (specialist|technician|analyst)|\bnoc\b|data ?center technician|end[- ]user|it technician"
# Drop the job for a category if the posting asks for more years than this.
MAX_YEARS = {"senior": 10, "junior": 5}

# ---------------------------------------------------------------------------
# 2c. Fit score (0-100): your skills found in the posting vs. skills you lack.
#     (regex, weight). Edit as you upskill: move a skill from GAP to MINE.
# ---------------------------------------------------------------------------
MY_SKILLS = {
    "Linux": (r"\blinux\b", 3), "RHEL": (r"\brhel\b|red hat|centos|rocky|alma ?linux|oracle linux", 3),
    "Ansible": (r"ansible", 3), "patching": (r"\bpatch", 3),
    "vuln mgmt": (r"vulnerabilit|tenable|nessus|qualys|\bcve", 2), "Terraform": (r"terraform", 2),
    "Puppet": (r"\bpuppet\b", 2), "Chef": (r"\bchef\b", 1), "SELinux": (r"selinux", 2),
    "Bash": (r"\bbash\b|shell script", 2), "AWS": (r"\baws\b|amazon web services|\bec2\b", 2),
    "VMware": (r"vmware|esxi|vsphere", 1), "LVM/storage": (r"\blvm\b|\bnfs\b|\bxfs\b|file ?systems?", 1),
    "DNS": (r"\bdns\b", 1), "AD/LDAP": (r"active directory|\bldap\b|\bsso\b", 1),
    "Git": (r"\bgit\b|gitlab|github", 1), "Jenkins": (r"jenkins", 1),
    "monitoring": (r"splunk|prometheus|checkmk|nagios|zabbix|site24x7", 1),
    "SQL": (r"\bsql\b|postgres|oracle db|mariadb|mysql", 1), "on-call": (r"on-call|on call", 1),
    "Docker": (r"docker|podman|container", 1), "web servers": (r"nginx|apache|tomcat", 1),
    "Kickstart": (r"kickstart|satellite|pxe", 1),
    "tickets/ITSM": (r"servicenow|\bitil\b|change management|ticket|jira|zendesk", 1),
    # Support skills (help desk / IT support)
    "Windows": (r"\bwindows\b", 2), "macOS": (r"mac ?os|\bmacs?\b", 1),
    "Microsoft 365": (r"microsoft 365|office 365|\bo365\b|\bm365\b|outlook|exchange online", 1),
    "troubleshooting": (r"troubleshoot", 1), "end-user support": (r"end[- ]users?|customer service|walk-?up|tier ?1", 1),
    "hardware/printers": (r"printer|peripheral|hardware|imaging|laptop", 1),
    "networking": (r"tcp/ip|wi-?fi|\bvpn\b|\bdhcp\b|\blan\b", 1),
}
GAP_SKILLS = {
    "Kubernetes": (r"kubernetes|\bk8s\b|openshift|\beks\b|\bgke\b", 2), "Go": (r"\bgolang\b|\bgo\b(?=[ ,/)])", 2),
    "Python": (r"\bpython\b", 1), "GCP": (r"\bgcp\b|google cloud", 1), "Azure": (r"\bazure\b", 1),
    "Helm/GitOps": (r"\bhelm\b|argo ?cd|gitops|\bflux\b", 1), "GPU/HPC": (r"\bgpu|cuda|slurm|infiniband", 1),
    "Rust/C++/Java": (r"\brust\b|c\+\+|\bjava\b", 1), "Kafka": (r"kafka", 1),
    "Intune/Jamf": (r"intune|\bjamf\b|\bsccm\b|\bmecm\b", 1),
}
# Postings below this score are dropped from that category (title-only scores come from TITLE_FIT).
MIN_FIT = {"senior": 40, "junior": 35}
# LinkedIn gives no description, so the score comes from the title alone (first match wins).
TITLE_FIT = [
    (r"linux|unix|rhel|red ?hat|sys ?admin|systems? administrat|server administrat|help ?desk|service desk|desktop support|\bit support|tech(nical)? support|it technician|computer technician|pc technician", 75),
    (r"infrastructure|systems? engineer|patch|vulnerab|ansible|terraform|puppet|configuration management|virtualization|vmware|data ?center|\bhpc\b|high[- ]performance comput|\bnoc\b|network operations|end[- ]user|endpoint|workstation|field|cloud support|it operations|\biam\b|identity|access management|it asset|deployment|provisioning|production support|application support|soc analyst|security analyst|it systems|it specialist|monitoring", 60),
    (r"cloud|dev ?ops|production engineer|operations engineer|automation|platform|site reliability|\bsre\b", 50),
]

# Alerts for jobs posted longer ago than this are skipped.
MAX_AGE_HOURS = 48
# If a WEAK title has no description to check (LinkedIn), keep it anyway?
KEEP_WEAK_WITHOUT_DESCRIPTION = False


# ---------------------------------------------------------------------------
# 3. Target companies watched DIRECTLY on their careers pages (often posts
#    before LinkedIn). All slugs verified 2026-11-11.
#    Format: ("greenhouse"|"lever"|"ashby", slug, Display Name)
# ---------------------------------------------------------------------------
TARGET_COMPANIES = [
    # Linux / open-source / infra-native — best fit, remote-friendly
    ("greenhouse", "canonical", "Canonical (Ubuntu)"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "elastic", "Elastic"),
    ("greenhouse", "grafanalabs", "Grafana Labs"),
    ("greenhouse", "chainguard", "Chainguard"),
    ("greenhouse", "tailscale", "Tailscale"),
    ("greenhouse", "mattermost", "Mattermost"),
    ("greenhouse", "wikimedia", "Wikimedia"),
    ("ashby", "docker", "Docker"),
    ("ashby", "supabase", "Supabase"),
    # Big-fleet infra / cloud / CDN (patching & fleet scale = your story)
    ("greenhouse", "cloudflare", "Cloudflare"),
    ("greenhouse", "fastly", "Fastly"),
    ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "pagerduty", "PagerDuty"),
    ("greenhouse", "newrelic", "New Relic"),
    ("greenhouse", "mongodb", "MongoDB"),
    ("greenhouse", "cockroachlabs", "Cockroach Labs"),
    ("greenhouse", "backblaze", "Backblaze"),
    ("greenhouse", "purestorage", "Pure Storage"),
    ("greenhouse", "rubrik", "Rubrik"),
    ("greenhouse", "twilio", "Twilio"),
    # GPU cloud / AI infra — hiring Linux fleet people hard right now
    ("greenhouse", "coreweave", "CoreWeave"),
    ("greenhouse", "nebius", "Nebius"),
    ("ashby", "crusoe", "Crusoe"),
    ("ashby", "lambda", "Lambda"),
    ("greenhouse", "togetherai", "Together AI"),
    ("ashby", "modal", "Modal"),
    ("greenhouse", "anthropic", "Anthropic"),
    ("ashby", "openai", "OpenAI"),
    ("ashby", "cohere", "Cohere"),
    ("greenhouse", "scaleai", "Scale AI"),
    # Security / compliance (Tenable, vuln mgmt, regulated envs)
    ("greenhouse", "okta", "Okta"),
    ("greenhouse", "zscaler", "Zscaler"),
    ("greenhouse", "sentinellabs", "SentinelOne"),
    ("greenhouse", "tanium", "Tanium"),
    ("ashby", "1password", "1Password"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "robinhood", "Robinhood"),
    # Defense / aerospace — Southern California, big RHEL shops
    ("lever", "shieldai", "Shield AI (San Diego)"),
    ("greenhouse", "andurilindustries", "Anduril"),
    ("lever", "palantir", "Palantir"),
    ("greenhouse", "axon", "Axon"),
    ("greenhouse", "relativity", "Relativity Space"),
    ("greenhouse", "rocketlab", "Rocket Lab"),
    ("greenhouse", "planetlabs", "Planet"),
    ("lever", "zoox", "Zoox"),
    # Large SaaS with big Linux fleets
    ("greenhouse", "databricks", "Databricks"),
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "samsara", "Samsara"),
    ("greenhouse", "reddit", "Reddit"),
    ("greenhouse", "pinterest", "Pinterest"),
    ("greenhouse", "airbnb", "Airbnb"),
    ("greenhouse", "dropbox", "Dropbox"),
    ("lever", "spotify", "Spotify"),
    # Added 2026-11-11: Linux fleets, data centers, IT ops tools (verified feeds)
    ("ashby", "vultr", "Vultr"),
    ("greenhouse", "digitalocean98", "DigitalOcean"),
    ("greenhouse", "ciq", "CIQ (Rocky Linux)"),
    ("greenhouse", "astranis", "Astranis"),
    ("greenhouse", "spacex", "SpaceX"),
    ("greenhouse", "kaseya", "Kaseya"),
    ("greenhouse", "solarwinds", "SolarWinds"),
    ("greenhouse", "logicmonitor", "LogicMonitor"),
    ("greenhouse", "expel", "Expel"),
]

# Big employers that don't have an open careers feed — they still come in via
# LinkedIn/Indeed, and get a ⭐ when they do. (Case-insensitive substring.)
STAR_COMPANIES = [
    "red hat", "servicenow", "oracle", "ibm", "canonical", "suse", "amazon", "aws", "google", "microsoft",
    "apple", "meta", "netflix", "nvidia", "qualcomm", "intuit", "cisco", "akamai", "equinix", "digitalocean",
    "rackspace", "vmware", "broadcom", "hashicorp", "tenable", "crowdstrike", "palo alto networks",
    "leidos", "saic", "booz allen", "gdit", "general dynamics", "northrop", "lockheed", "raytheon", "rtx",
    "l3harris", "boeing", "spacex", "jet propulsion", "jpl", "nasa", "kaiser", "illumina", "viasat",
    "sempra", "sdg&e", "workday", "salesforce", "adobe", "paypal", "visa", "capital one", "jpmorgan",
] + [name.lower() for _, _, name in TARGET_COMPANIES]

# ---------------------------------------------------------------------------
# 4. Messaging
# ---------------------------------------------------------------------------
MAX_PER_TRACK = 40   # jobs listed per message per run (newest kept)
RESUME_LABEL = {"senior": "Senior resume (6+ yrs)", "junior": "Junior resume (2+ yrs)"}
