# Job Search Bot 🤖

Every hour (about 5am–10pm Pacific), the bot checks **LinkedIn, Indeed, ZipRecruiter, Glassdoor, 4 remote-job boards (We Work Remotely, Remote OK, Remotive, Himalayas) and 63 target companies' own careers pages** for new Linux, infrastructure and IT support jobs. **US only** (remote, California, rest of US). It sends **two Telegram messages**, one for each resume:

- **🧑‍💼 SENIOR**: use your senior resume in `resumes/senior/` (6+ years)
- **🌱 JUNIOR**: use your junior resume in `resumes/junior/` (2+ years)

```
🧑‍💼 SENIOR · 3 new · newest first
📄 Use: Senior resume (6+ yrs)

🕒 🔥 25m ago · 🟢 REMOTE
Linux Systems Administrator ⭐
🏢 Vultr · 📍 Remote - United States
🎯 82% fit · ✅ Linux, RHEL, Bash · ⚠️ Python
📅 3+ yrs · 💰 $95,000–$120,000 yearly
🔗 Apply · Careers page
```

**How jobs are picked and sorted:**
- **Newest first.** Jobs posted more than 2 days ago are skipped. Apply early!
  - **Job boards** only return the last 2 hours, so when they give just a date the alert says `≤2h ago`.
  - **Other sources:** a date with no time shows as `posted today` or `posted yesterday`.
  - **No time at all:** `time not given · new since last check`, listed last.
- **Two categories.** The title finds the job; the posting decides if you're eligible. A job can be in **both** lists (marked 🔁), so you choose the resume.

  | | 🧑‍💼 SENIOR (Linux / infrastructure) | 🌱 JUNIOR (IT support / junior infrastructure) |
  |---|---|---|
  | Titles | Linux/Unix/RHEL admin & engineer, Systems Admin/Engineer, Infrastructure, Server, Cloud, AWS, DevOps, SRE, Platform, Production, Ansible/Puppet/Terraform, Config Mgmt, Virtualization/VMware, Linux/Infra Security, Linux/Technical Support Engineer, Data Center Systems | Help desk, Service desk, Desktop/IT/Technical support, IT/PC/Computer/Field technician, End user/Endpoint/Workstation, Application support, Junior/Associate sysadmin & Linux, NOC, Network support, Data center tech, Cloud support, Junior Cloud/DevOps/Systems engineer, IT asset/deployment/provisioning, IAM/Access analyst, Monitoring, Production support analyst, SOC Tier 1, Junior security analyst |
  | Levels | Junior → Senior → **Lead / Technical Lead** | Entry → Intermediate → **Senior support** |
  | Never | Staff, Principal, Distinguished, Manager, Director, Architect, level V+ | Lead, Manager, Director, Architect, Staff; "Senior" non-support roles |
  | Years asked | up to 10 | up to 5 |
  | Min fit | 40% | 35% |

- **🎯 Fit score** = your skills found in the posting (✅) vs. skills you don't have yet (⚠️). Below the category's minimum, the job is dropped from that list.
  - LinkedIn gives no description, so its score comes from the title only (marked `~` and "title only").
- **Tags:**
  - 📅 years asked
  - 🔒 security clearance required
  - ⭐ target or big-name employer
- **Location:** within the same hour, 🟢 Remote → 🌴 California → 🇺🇸 rest of US.
  - Jobs outside the US are never sent. That includes remote jobs limited to another country, like "Remote - Canada".
  - Postings that need another language (German, Spanish...) are skipped.

---

## What's where

```
Job_Search_Bot/
├── README.md                 this file
├── requirements.txt          Python packages GitHub installs
├── .github/workflows/        job-bot.yml: the hourly schedule on GitHub
├── bot/
│   ├── bot.py                the bot
│   └── config.py             ← the settings you edit (titles, levels, fit score, companies)
├── setup/get_chat_id.py      one-time Telegram setup
├── state/seen_jobs.json      jobs already sent (the bot updates this on GitHub; don't move it)
├── Analysis/
│   ├── REPORT.md             job market vs. your resume (on your Mac only, not uploaded)
│   ├── scripts/              fetch_details.py, analyze.py
│   └── data/                 downloaded job text (not uploaded)
└── resumes/                  not uploaded
    ├── senior/               your 6+ year resume (PDF)
    └── junior/               your 2+ year resume (PDF)
```

## Setup (one time, about 10 minutes)

### 1. Get your chat ID
Send "hi" to your bot in Telegram, then in Terminal:
```bash
cd ~/Downloads/Job_Search_Bot && python3 setup/get_chat_id.py
```
Paste your bot token when asked (it isn't saved anywhere). It prints your **chat ID** and sends a test message.

### 2. Put it on GitHub
Create a **private** repo at github.com/new named `Job_Search_Bot`, then:
```bash
cd ~/Downloads/Job_Search_Bot && git init -b main && git add . && git commit -m "Job search bot" && git remote add origin https://github.com/YOUR_USERNAME/Job_Search_Bot.git && git push -u origin main
```
(PDFs are in `.gitignore`, so your resumes are **not** uploaded.)

### 3. Add the two secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `TELEGRAM_BOT_TOKEN`: the token from @BotFather
- `TELEGRAM_CHAT_ID`: the number from step 1

### 4. Start it
Repo → **Actions** tab → enable workflows if asked → **Job alert bot** → **Run workflow**.
After that you only get **new** postings (from the last 3 days at most).

---

## Tweaking (edit `bot/config.py`)
| Want to… | Change |
|---|---|
| Search other job titles | `SEARCH_QUERIES` (the last line is the junior search) |
| Titles each list looks for | `TITLES` (strong = title is enough; weak = also needs a qualifier word) |
| Highest level / years per list | `LEVEL_EXCLUDE`, `JUNIOR_SENIOR_OK`, `MAX_YEARS` |
| Update the fit score as you learn (e.g. after the CKA) | Move the skill from `GAP_SKILLS` to `MY_SKILLS` |
| See more or fewer jobs | `MIN_FIT` (lower = more), `MAX_AGE_HOURS` |
| Which job boards are searched | `BOARD_SITES` (each one adds run time), `REMOTE_FEEDS` |
| Allow or block titles | `STRONG_TITLE_PATTERNS`, `EXCLUDE_TITLE_PATTERNS` |
| Add a company | `TARGET_COMPANIES`. Find the slug in their careers URL: `boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>` |
| Change how often it runs | `cron:` line in `.github/workflows/job-bot.yml` |

Test locally without sending anything:
```bash
python3 bot/bot.py --dry-run --no-boards
```
(LinkedIn, Indeed, ZipRecruiter and Glassdoor need Python 3.10+, which GitHub has. Your Mac's 3.9 can only test the company feeds.)

## Titles it looks for
See the table above. It always skips sales, solutions engineering, internships, hardware design, embedded, QA, non-IT technician jobs (medical, HVAC, automotive...) and VP/Director roles.

## Target companies and why
- **Linux and open-source companies (remote-first):** Canonical, GitLab, Elastic, Grafana Labs, Tailscale, Docker, Supabase, Chainguard, Mattermost, Wikimedia
- **Big-fleet infrastructure** (large server fleets, heavy patching): Cloudflare, Fastly, Datadog, MongoDB, PagerDuty, New Relic, Backblaze, Pure Storage, Rubrik, Twilio, Cockroach Labs
- **GPU cloud and AI infrastructure** (hiring Linux fleet people the most right now): CoreWeave, Nebius, Crusoe, Lambda, Together AI, Modal, Anthropic, OpenAI, Cohere, Scale AI
- **Security and compliance** (Tenable and vulnerability-management experience): Okta, Zscaler, SentinelOne, Tanium, 1Password, Coinbase, Robinhood
- **Defense and aerospace in SoCal** (large RHEL shops in Southern California): Shield AI (San Diego), Anduril (Costa Mesa), Palantir, Axon, Relativity Space, Rocket Lab, Planet, Zoox
- **Large SaaS:** Databricks, Stripe, Samsara, Reddit, Pinterest, Airbnb, Dropbox, Spotify
- **Linux fleets, data centers, IT-ops tools** (added after the job-market analysis): Vultr, DigitalOcean, CIQ (Rocky Linux), Astranis, SpaceX, Kaseya, SolarWinds, LogicMonitor, Expel
- Defense integrators, hospitals, universities and banks have no open job feed. They come in through LinkedIn and Indeed.
- **⭐ flagged when they appear on LinkedIn or Indeed:** Red Hat, ServiceNow, Oracle, IBM, SUSE, AWS, Google, Microsoft, Apple, NVIDIA, Qualcomm, Intuit, Akamai, Equinix, DigitalOcean, Tenable, CrowdStrike, Leidos, SAIC, Booz Allen, GDIT, Northrop, Lockheed, RTX, L3Harris, Boeing, SpaceX, JPL, Illumina, Viasat and more

## Good to know
- **Cost:** $0. A private repo gets 2,000 free Actions minutes a month, and this uses roughly 1,500. A public repo has unlimited minutes, but your search settings would be visible.
- **If LinkedIn or Indeed start blocking it**, you'll get one ⚠️ message a day. The company feeds keep working.
- **Seen jobs** are stored in `state/seen_jobs.json` (committed by the bot), so you're never alerted twice. It holds IDs and "company|title" only. Run `git pull` to see the latest, and see `Analysis/` for the full-text analysis tools.
