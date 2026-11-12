#!/usr/bin/env python3
"""
Job Search Bot — finds new Linux / infrastructure jobs and texts them to Telegram.

Sources:
  * LinkedIn + Indeed (via python-jobspy)
  * Target companies' own career feeds (Greenhouse / Lever / Ashby public APIs)

Each run sends up to two messages, one per resume: SENIOR and JUNIOR. Each category
finds jobs by title, then checks the posting (level, years asked, fit score); a job
can be in both. Listed newest first (bot/config.py, sections 2-2c).

Usage:
  python bot/bot.py              # normal run (needs TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
  python bot/bot.py --dry-run    # print alerts instead of sending; don't save state
  python bot/bot.py --no-boards  # company feeds only (skip job boards and remote feeds)
  python bot/bot.py --no-companies
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config as C

ROOT = Path(__file__).resolve().parent.parent   # repo root (this file is in bot/)
STATE_FILE = ROOT / "state" / "seen_jobs.json"
SEEN_TTL_DAYS = 60
UA = "Mozilla/5.0 (job-search-bot)"

TIER_REMOTE, TIER_CA, TIER_US, TIER_OVERSEAS = 0, 1, 2, 3
TIER_LABEL = {
    TIER_REMOTE: "🟢 REMOTE",
    TIER_CA: "🌴 CALIFORNIA",
    TIER_US: "🇺🇸 US",
    TIER_OVERSEAS: "🌍 OVERSEAS",
}

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
TRACKS = ("senior", "junior")
_cat = {t: dict(strong=[re.compile(p, re.I) for p in C.TITLES[t]["strong"]],
                weak=[re.compile(p, re.I) for p in C.TITLES[t]["weak"]],
                qual=re.compile(C.TITLES[t]["qualifiers"], re.I),
                lvl=[re.compile(p, re.I) for p in C.LEVEL_EXCLUDE[t]])
        for t in TRACKS}
_excl = [re.compile(p, re.I) for p in C.EXCLUDE_TITLE_PATTERNS]
_jr_senior = re.compile(C.JUNIOR_SENIOR_MARKERS, re.I)
_jr_senior_ok = re.compile(C.JUNIOR_SENIOR_OK, re.I)
_star = [s.lower() for s in C.STAR_COMPANIES]
_mine = {k: (re.compile(rx, re.I), w) for k, (rx, w) in C.MY_SKILLS.items()}
_gaps = {k: (re.compile(rx, re.I), w) for k, (rx, w) in C.GAP_SKILLS.items()}
_title_fit = [(re.compile(rx, re.I), sc) for rx, sc in C.TITLE_FIT]
_years = re.compile(r"(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*)?\+?\s*years?(?:\s+of)?[^.\n]{0,60}?experience", re.I)
_clearance = re.compile(
    r"(active|current|existing)[^.\n]{0,20}(ts/sci|top secret|secret|security) clearance|"
    r"clearance[^.\n]{0,15}(is )?required|must (hold|have|possess)[^.\n]{0,25}clearance|\bts/sci\b", re.I)


def found_in(track: str, title: str, description: str | None) -> bool:
    """Discovery: the title fits this category (STRONG, or WEAK plus a qualifier word)."""
    c = _cat[track]
    if any(p.search(title) for p in c["strong"]):
        return True
    if any(p.search(title) for p in c["weak"]):
        if c["qual"].search(title):
            return True
        if description:
            return bool(c["qual"].search(description[:6000]))
        return C.KEEP_WEAK_WITHOUT_DESCRIPTION
    return False


def level_ok(track: str, title: str, years: int | None = None) -> bool:
    """Eligibility: not above the category's top level, and not asking too many years."""
    if any(p.search(title) for p in _cat[track]["lvl"]):
        return False
    if track == "junior" and _jr_senior.search(title) and not _jr_senior_ok.search(title):
        return False   # Senior is fine in JUNIOR only for support roles
    if years is not None and years > C.MAX_YEARS[track]:
        return False
    return True


STATES = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas", "CA": "california", "CO": "colorado",
    "CT": "connecticut", "DE": "delaware", "DC": "district of columbia", "FL": "florida", "GA": "georgia",
    "HI": "hawaii", "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
    "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland", "MA": "massachusetts",
    "MI": "michigan", "MN": "minnesota", "MS": "mississippi", "MO": "missouri", "MT": "montana",
    "NE": "nebraska", "NV": "nevada", "NH": "new hampshire", "NJ": "new jersey", "NM": "new mexico",
    "NY": "new york", "NC": "north carolina", "ND": "north dakota", "OH": "ohio", "OK": "oklahoma",
    "OR": "oregon", "PA": "pennsylvania", "RI": "rhode island", "SC": "south carolina", "SD": "south dakota",
    "TN": "tennessee", "TX": "texas", "UT": "utah", "VT": "vermont", "VA": "virginia", "WA": "washington",
    "WV": "west virginia", "WI": "wisconsin", "WY": "wyoming",
}
_state_code = re.compile(r"(?:,|\b)\s*(" + "|".join(STATES) + r")\b(?:\s*,?\s*(?:US|USA|United States))?\s*$")
_state_code_any = re.compile(r",\s*(" + "|".join(STATES) + r")\b")
_state_name = re.compile(r"\b(" + "|".join(STATES.values()) + r")\b", re.I)
_us_word = re.compile(r"\b(united states|usa|u\.s\.a?\.?|us|america|nationwide)\b", re.I)
_ca_city = re.compile(
    r"\b(california|san diego|los angeles|san francisco|bay area|silicon valley|san jose|oakland|irvine|"
    r"sacramento|palo alto|mountain view|sunnyvale|santa clara|costa mesa|el segundo|"
    r"hawthorne|long beach|pasadena|redwood city|menlo park|fremont|berkeley|santa monica|burbank|"
    r"torrance|anaheim|riverside|san mateo|cupertino|milpitas|foster city|south san francisco|culver city|"
    r"newport beach|orange county|santa barbara|camarillo|point mugu|china lake|vandenberg|lompoc)\b", re.I)
_remote = re.compile(r"\b(remote|anywhere|work from home|wfh|distributed|virtual|home[- ]based|worldwide)\b", re.I)
_foreign = re.compile(
    r"\b(canada|toronto|vancouver|montreal|montréal|ottawa|calgary|quebec|québec|uk|united kingdom|england|"
    r"london|scotland|ireland|dublin|germany|berlin|munich|france|paris|lyon|spain|madrid|barcelona|"
    r"portugal|lisbon|netherlands|amsterdam|belgium|brussels|switzerland|zurich|zürich|geneva|genève|"
    r"poland|warsaw|romania|sweden|stockholm|denmark|norway|finland|italy|europe|emea|apac|latam|india|"
    r"bangalore|bengaluru|hyderabad|pune|singapore|japan|tokyo|korea|seoul|australia|sydney|melbourne|"
    r"new zealand|brazil|são paulo|sao paulo|mexico|argentina|colombia|israel|tel aviv|uae|dubai|"
    r"philippines|china|beijing|shanghai|hong kong|taiwan|taipei|south africa|nigeria|kenya|egypt|czech|"
    r"prague|hungary|austria|iceland|emirates|abu dhabi|saudi|riyadh|qatar|doha|turkey|istanbul|greece|"
    r"slovakia|bratislava|slovenia|ljubljana|cyprus|malta|morocco|tunisia|pakistan|bangladesh|sri lanka|"
    r"nepal|ghana|uruguay|montevideo|bogot[aá]|medell[ií]n|buenos aires|santiago|lima|guadalajara|"
    r"krak[oó]w|wroc[lł]aw|bucharest|cluj|sofia|belgrade|zagreb|kyiv|kiev|tallinn|riga|vilnius|"
    r"luxembourg|estonia|lithuania|latvia|serbia|croatia|bulgaria|ukraine|vietnam|thailand|malaysia|"
    r"indonesia|chile|peru|costa rica|ind|isr|sgp|gbr|deu|fra|can|aus|jpn|nld|irl)\b",
    re.I)


def classify(location: str, is_remote: bool, title: str = "") -> tuple[int, bool]:
    """Return (tier, is_remote)."""
    loc = (location or "").strip()
    remote = bool(is_remote) or bool(_remote.search(loc)) or bool(_remote.search(title or ""))
    is_ca = bool(_ca_city.search(loc) or re.search(r",\s*CA\b", loc))
    has_us = bool(is_ca or _us_word.search(loc) or _state_code_any.search(loc) or _state_code.search(loc)
                  or _state_name.search(loc))
    # Anything with a US marker, or no foreign marker at all ("Remote", "Seattle"), counts as US
    if not has_us and _foreign.search(loc):
        return TIER_OVERSEAS, remote
    if remote:
        return TIER_REMOTE, True
    if is_ca:
        return TIER_CA, False
    return TIER_US, False


def min_years(description: str | None) -> int | None:
    """Smallest 'N years ... experience' the posting asks for (1-20), or None."""
    if not description:
        return None
    ys = [int(m) for m in _years.findall(description[:10000]) if 1 <= int(m) <= 20]
    return min(ys) if ys else None


def fit_score(title: str, description: str | None) -> tuple[int, list[str], list[str], bool]:
    """(score 0-100, your skills found, gap skills found, title_only)."""
    tscore = next((sc for rx, sc in _title_fit if rx.search(title)), 35)
    if not description or len(description) < 200:
        have = [k for k, (rx, _) in _mine.items() if rx.search(title)]
        return min(100, tscore + 5 * len(have)), have, [], True
    text = f"{title}\n{description}"
    have = [k for k, (rx, _) in _mine.items() if rx.search(text)]
    gaps = [k for k, (rx, _) in _gaps.items() if rx.search(text)]
    hw = sum(_mine[k][1] for k in have)
    gw = sum(_gaps[k][1] for k in gaps)
    # share of the posting's skills you have, scaled down when few of your skills appear at all
    score = 70 * hw / max(1, hw + gw) * min(1, hw / 8) + 30 * min(hw, 15) / 15
    if tscore >= 75:
        score += 10
    return min(100, round(score)), have, gaps, False


def posted_date_age_days(iso: str | None) -> int | None:
    """For a date-only posting time ("2026-11-11"): days ago (0 = today, UTC). Else None."""
    if not iso or len(str(iso)) != 10:
        return None
    try:
        d = datetime.strptime(str(iso), "%Y-%m-%d").date()
    except ValueError:
        return None
    us_today = (datetime.now(timezone.utc) - timedelta(hours=8)).date()   # boards date postings in US time
    return (us_today - d).days


def age_hours(iso: str | None) -> float | None:
    """Hours since posting; None if unknown or only a date was given."""
    if not iso or len(str(iso)) <= 10:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)


def norm_key(title: str, company: str) -> str:
    t = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    c = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|company)\b", "", (company or "").lower())
    c = re.sub(r"[^a-z0-9]+", " ", c).strip()
    return f"{c}|{t}"


def is_star(company: str) -> bool:
    c = (company or "").lower()
    return any(s and s in c for s in _star)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def http_json(url: str, data: dict | None = None, timeout: int = 30):
    body = None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ---------------------------------------------------------------------------
# Sources: company career feeds
# ---------------------------------------------------------------------------
def fetch_company(ats: str, slug: str, name: str) -> list[dict]:
    jobs = []
    if ats == "greenhouse":
        d = http_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        for j in d.get("jobs", []):
            jobs.append(dict(
                id=f"gh:{slug}:{j['id']}", title=j.get("title", ""), company=name,
                location=(j.get("location") or {}).get("name", ""), url=j.get("absolute_url", ""),
                is_remote=False, posted=j.get("first_published") or j.get("updated_at"),
                salary=None, description=None, source="Careers page"))
    elif ats == "lever":
        d = http_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        for j in d:
            cat = j.get("categories") or {}
            locs = cat.get("allLocations") or [cat.get("location", "")]
            sal = j.get("salaryRange") or {}
            salary = None
            if sal.get("min"):
                salary = f"{sal.get('currency', '')} {sal['min']:,}–{sal.get('max', 0):,} {sal.get('interval', '')}".strip()
            jobs.append(dict(
                id=f"lever:{slug}:{j['id']}", title=j.get("text", ""), company=name,
                location=" / ".join(l for l in locs if l), url=j.get("hostedUrl", ""),
                is_remote=(j.get("workplaceType") == "remote"),
                posted=datetime.fromtimestamp(j["createdAt"] / 1000, timezone.utc).isoformat() if j.get("createdAt") else None,
                salary=salary, description=j.get("descriptionPlain"), source="Careers page"))
    elif ats == "ashby":
        d = http_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
        for j in d.get("jobs", []):
            if j.get("isListed") is False:
                continue
            locs = [j.get("location", "")] + [s.get("location", "") for s in (j.get("secondaryLocations") or [])]
            comp = (j.get("compensation") or {}).get("compensationTierSummary")
            addr = ((j.get("address") or {}).get("postalAddress") or {})
            loc = " / ".join(l for l in locs if l)
            if addr.get("addressCountry") and addr["addressCountry"] not in loc:
                loc = f"{loc}, {addr['addressCountry']}" if loc else addr["addressCountry"]
            jobs.append(dict(
                id=f"ashby:{slug}:{j['id']}", title=j.get("title", ""), company=name,
                location=loc, url=j.get("jobUrl", ""),
                is_remote=bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
                posted=j.get("publishedAt"), salary=comp,
                description=j.get("descriptionPlain"), source="Careers page"))
    return jobs


def ensure_description(j: dict) -> None:
    """Greenhouse's job list has no text; fetch it for one job (only fresh candidates get here)."""
    if j.get("description") or not j["id"].startswith("gh:"):
        return
    _, slug, jid = j["id"].split(":", 2)
    try:
        d = http_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{jid}")
        txt = html.unescape(d.get("content") or "")
        txt = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", txt, flags=re.I)
        j["description"] = re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", txt)).strip() or None
    except Exception as e:  # noqa: BLE001
        print(f"!! description for {j['id']}: {e}", file=sys.stderr)


def title_candidate(title: str) -> bool:
    """Title alone could fit a category at an allowed level (cheap check before fetching text)."""
    if not title or any(p.search(title) for p in _excl):
        return False
    return any(level_ok(t, title) and any(p.search(title) for p in _cat[t]["strong"] + _cat[t]["weak"])
               for t in TRACKS)


def fetch_all_companies() -> tuple[dict[str, list[dict]], list[str]]:
    results, errors = {}, []

    def one(t):
        ats, slug, name = t
        try:
            return f"{ats}:{slug}", fetch_company(ats, slug, name), None
        except Exception as e:  # noqa: BLE001
            return f"{ats}:{slug}", [], f"{name}: {e}"

    with ThreadPoolExecutor(max_workers=10) as ex:
        for key, jobs, err in ex.map(one, C.TARGET_COMPANIES):
            if err:
                errors.append(err)
            else:
                results[key] = jobs
    return results, errors


# ---------------------------------------------------------------------------
# Sources: LinkedIn / Indeed via jobspy
# ---------------------------------------------------------------------------
def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    s = str(v)
    return None if s in ("nan", "NaT", "None", "") else v


def _salary(r: dict) -> str | None:
    lo, hi = _clean(r.get("min_amount")), _clean(r.get("max_amount"))
    if not lo and not hi:
        return None
    cur = _clean(r.get("currency")) or "USD"
    sym = "$" if cur == "USD" else f"{cur} "
    iv = _clean(r.get("interval")) or ""
    fmt = lambda x: f"{sym}{float(x):,.0f}"  # noqa: E731
    rng = f"{fmt(lo)}–{fmt(hi)}" if lo and hi else fmt(lo or hi)
    return f"{rng} {iv}".strip()


def board_searches():
    """Yield (label, kwargs) for each jobspy call: every board x every query, US only."""
    base = dict(results_wanted=C.RESULTS_PER_SEARCH, hours_old=C.HOURS_OLD,
                linkedin_fetch_description=False, verbose=0)
    for q in C.SEARCH_QUERIES:
        for site in C.BOARD_SITES:
            kw = dict(base, site_name=[site], search_term=q, location=C.US_LOCATION)
            if site in ("indeed", "glassdoor"):
                kw["country_indeed"] = "USA"
            yield C.BOARD_LABEL.get(site, site), kw


def fetch_boards() -> tuple[list[dict], int, int]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("!! python-jobspy not installed — skipping LinkedIn, Indeed, ZipRecruiter, Glassdoor", file=sys.stderr)
        return [], 0, 0
    jobs, ok, failed = [], 0, 0
    for label, kw in board_searches():
        try:
            df = scrape_jobs(**kw)
            rows = df.to_dict("records") if df is not None else []
            ok += 1
            print(f"   {label:<22} {len(rows):>3} results  [{kw['search_term'][:50]}…]")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"!! {label} failed: {str(e)[:200]}", file=sys.stderr)
            rows = []
        for r in rows:
            site = C.BOARD_LABEL.get(str(_clean(r.get("site")) or ""), str(_clean(r.get("site")) or "").title())
            url = _clean(r.get("job_url")) or _clean(r.get("job_url_direct")) or ""
            posted = _clean(r.get("date_posted"))
            jobs.append(dict(
                id=f"{site.lower()}:{_clean(r.get('id')) or url}",
                title=str(_clean(r.get("title")) or ""), company=str(_clean(r.get("company")) or ""),
                location=str(_clean(r.get("location")) or ""), url=str(url),
                is_remote=bool(_clean(r.get("is_remote"))), posted=str(posted) if posted else None,
                salary=_salary(r), description=_clean(r.get("description")),
                source=site or "Job board", windowed=True))   # searched for the last HOURS_OLD hours
        time.sleep(2)  # be gentle — avoids rate limiting
    return jobs, ok, failed


# ---------------------------------------------------------------------------
# Sources: free remote-job feeds (official APIs / RSS)
# ---------------------------------------------------------------------------
def strip_html(s: str | None) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", s, flags=re.I)
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def http_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def fetch_remote_feeds() -> tuple[list[dict], list[str]]:
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    jobs, errors = [], []

    def remoteok():
        for j in http_json("https://remoteok.com/api")[1:]:   # item 0 is the terms notice
            jobs.append(dict(id=f"remoteok:{j.get('id')}", title=j.get("position", ""), company=j.get("company", ""),
                             location=j.get("location") or "Remote", url=j.get("url", ""), is_remote=True,
                             posted=j.get("date"), salary=(f"${j['salary_min']:,}–${j['salary_max']:,} yearly"
                                                           if j.get("salary_min") and j.get("salary_max") else None),
                             description=strip_html(j.get("description")), source="Remote OK"))

    def wwr():
        for cat in ("remote-devops-sysadmin-jobs", "remote-customer-support-jobs"):
            root = ET.fromstring(http_text(f"https://weworkremotely.com/categories/{cat}.rss"))
            for it in root.iter("item"):
                raw = it.findtext("title") or ""
                company, _, title = raw.partition(": ")
                pub = it.findtext("pubDate")
                jobs.append(dict(id=f"wwr:{it.findtext('guid') or it.findtext('link')}", title=title or raw,
                                 company=company, location=it.findtext("region") or "Remote",
                                 url=it.findtext("link") or "", is_remote=True,
                                 posted=parsedate_to_datetime(pub).isoformat() if pub else None, salary=None,
                                 description=strip_html(it.findtext("description")), source="We Work Remotely"))

    def remotive():
        for cat in ("devops", "customer-support"):
            for j in http_json(f"https://remotive.com/api/remote-jobs?category={cat}").get("jobs", []):
                pub = j.get("publication_date")
                jobs.append(dict(id=f"remotive:{j.get('id')}", title=j.get("title", ""), company=j.get("company_name", ""),
                                 location=j.get("candidate_required_location") or "Remote", url=j.get("url", ""),
                                 is_remote=True, posted=(pub + "+00:00") if pub and "+" not in pub else pub,
                                 salary=j.get("salary") or None, description=strip_html(j.get("description")),
                                 source="Remotive"))

    def himalayas():
        for j in http_json("https://himalayas.app/jobs/api?limit=100").get("jobs", []):
            pub = j.get("pubDate")
            locs = j.get("locationRestrictions") or []
            jobs.append(dict(id=f"himalayas:{j.get('guid') or j.get('applicationLink')}", title=j.get("title", ""),
                             company=j.get("companyName", ""),
                             location=", ".join(locs) if locs else "Remote - Worldwide",
                             url=j.get("applicationLink") or j.get("guid") or "", is_remote=True,
                             posted=datetime.fromtimestamp(pub, timezone.utc).isoformat() if isinstance(pub, (int, float)) else pub,
                             salary=None, description=strip_html(j.get("description") or j.get("excerpt")),
                             source="Himalayas"))

    for name, fn in (("Remote OK", remoteok), ("We Work Remotely", wwr), ("Remotive", remotive), ("Himalayas", himalayas)):
        n = len(jobs)
        try:
            fn()
            print(f"   {name:<22} {len(jobs) - n:>3} jobs")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {str(e)[:150]}")
    return jobs, errors


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            print("!! state file corrupt — starting fresh", file=sys.stderr)
    return {"seen": {}, "seeded_sources": [], "board_failures": 0, "last_warning": None}


def save_state(state: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)).isoformat()
    state["seen"] = {k: v for k, v in state["seen"].items() if v >= cutoff}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=0, sort_keys=True))


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
class Telegram:
    def __init__(self, dry: bool):
        self.dry = dry
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not dry and not (self.token and self.chat):
            sys.exit("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (or use --dry-run)")

    def send(self, text: str) -> None:
        if self.dry:
            print("\n----- TELEGRAM -----\n" + re.sub(r"<[^>]+>", "", text))
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        for attempt in range(4):
            try:
                http_json(url, payload)
                time.sleep(1.1)  # Telegram: ~1 msg/sec per chat
                return
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")
                if e.code == 429:
                    wait = json.loads(body).get("parameters", {}).get("retry_after", 5)
                    time.sleep(wait + 1)
                    continue
                print(f"!! Telegram error {e.code}: {body[:300]}", file=sys.stderr)
                return
            except Exception as e:  # noqa: BLE001
                print(f"!! Telegram send failed: {e}", file=sys.stderr)
                time.sleep(3)

    def send_chunked(self, header: str, lines: list[str]) -> None:
        buf = header
        for line in lines:
            if len(buf) + len(line) + 1 > 3900:
                self.send(buf)
                buf = header.split("\n")[0] + " (cont.)\n"
            buf += "\n" + line
        if buf.strip():
            self.send(buf)


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def age_label(j: dict) -> str:
    h = j.get("age")
    if h is None:
        days = posted_date_age_days(j.get("posted"))
        if j.get("windowed"):
            return f"≤{C.HOURS_OLD}h ago"   # the board search only returns the last HOURS_OLD hours
        if days is not None:
            return "posted today" if days <= 0 else "posted yesterday" if days == 1 else f"posted {days}d ago"
        return "time not given · new since last check"
    if h < 1:
        return f"🔥 {max(1, int(h * 60))}m ago"
    if h < 48:
        return f"{int(h)}h ago"
    return f"{int(h // 24)}d ago"


def format_job(j: dict, track: str = "") -> str:
    star = " ⭐" if j["star"] else ""
    tier = TIER_LABEL[j["tier"]]
    lines = [
        f"🕒 {age_label(j)} · {tier}",
        f"<b>{esc(j['title'])}</b>{star}",
        f"🏢 {esc(j['company'])}" + (f" · 📍 {esc(j['location'])}" if j["location"] else ""),
    ]
    fit = f"🎯 {'~' if j['title_only'] else ''}{j['fit']}% fit"
    if j["title_only"]:
        fit += " (title only)"
    if j["have"]:
        fit += " · ✅ " + ", ".join(j["have"][:5])
    if j["gaps"]:
        fit += " · ⚠️ " + ", ".join(j["gaps"][:3])
    lines.append(fit)
    extra = []
    if j.get("years") is not None:
        extra.append(f"📅 {j['years']}+ yrs")
    if j.get("clearance"):
        extra.append("🔒 clearance")
    if j.get("salary"):
        extra.append(f"💰 {esc(j['salary'])}")
    if extra:
        lines.append(" · ".join(extra))
    others = [t for t in j.get("tracks", []) if t != track]
    if others:
        lines.append(f"🔁 also in the {others[0].upper()} list")
    lines.append(f'🔗 <a href="{esc(j["url"])}">Apply</a> · {esc(j["source"])}')
    return "\n".join(lines)


TRACK_HEADER = {"senior": "🧑‍💼 <b>SENIOR</b>", "junior": "🌱 <b>JUNIOR</b>"}


def send_track(tg: Telegram, track: str, jobs: list[dict]) -> None:
    if not jobs:
        return
    shown = jobs[: C.MAX_PER_TRACK]
    header = (f"{TRACK_HEADER[track]} · {len(jobs)} new · newest first\n"
              f"📄 Use: {esc(C.RESUME_LABEL[track])}")
    blocks = [format_job(j, track) for j in shown]
    if len(jobs) > len(shown):
        blocks.append(f"… and {len(jobs) - len(shown)} more (older ones left out)")
    buf = header
    for b in blocks:
        if len(buf) + len(b) + 2 > 3900:
            tg.send(buf)
            buf = f"{TRACK_HEADER[track]} (cont.)"
        buf += "\n\n" + b
    tg.send(buf)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def prepare(j: dict) -> dict | None:
    """Add tier, track, fit and freshness. None = drop (wrong level, place, fit or too old)."""
    j["tier"], j["remote"] = classify(j["location"], j["is_remote"], j["title"])
    j["star"] = is_star(j["company"])
    j["key"] = norm_key(j["title"], j["company"])
    if j["tier"] == TIER_OVERSEAS:
        return None   # US only
    j["years"] = min_years(j["description"])
    j["fit"], j["have"], j["gaps"], j["title_only"] = fit_score(j["title"], j["description"])
    j["tracks"] = [t for t in TRACKS
                   if found_in(t, j["title"], j["description"])
                   and level_ok(t, j["title"], j["years"])
                   and j["fit"] >= C.MIN_FIT[t]]
    if not j["tracks"]:
        return None
    j["clearance"] = bool(j["description"] and _clearance.search(j["description"]))
    j["age"] = age_hours(j.get("posted"))
    if j["age"] is not None and j["age"] > C.MAX_AGE_HOURS:
        return None
    days = posted_date_age_days(j.get("posted"))
    if j["age"] is None and days is not None and days >= C.MAX_AGE_HOURS // 24:
        return None
    return j


def sort_key(j: dict):
    # Newest first, then remote > California > rest of US, then fit.
    # No exact time: board results are within the search window; date-only = start of that day; none = last.
    age = j["age"]
    if age is None:
        days = posted_date_age_days(j.get("posted"))
        age = C.HOURS_OLD if j.get("windowed") else (days * 24 + 12 if days is not None else 999)
    return (int(age), j["tier"], -j["fit"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-boards", action="store_true")
    ap.add_argument("--no-companies", action="store_true")
    args = ap.parse_args()

    tg = Telegram(args.dry_run)
    state = load_state()
    seen = state["seen"]
    now = datetime.now(timezone.utc).isoformat()
    print(f"== Job bot run {now} — {len(seen)} jobs already seen")

    alerts = {"senior": [], "junior": []}
    run_keys = set()
    dropped = 0

    def handle(j):
        """Queue an alert if the job is new and passes every filter; only alerted jobs are saved
        as seen (filtered ones are re-checked next run, which is cheap and keeps the state small)."""
        nonlocal dropped
        if j["id"] in seen or norm_key(j["title"], j["company"]) in seen:
            return
        if not title_candidate(j["title"]):
            return
        age = age_hours(j.get("posted"))
        days = posted_date_age_days(j.get("posted"))
        if (age is not None and age > C.MAX_AGE_HOURS) or (age is None and days is not None and days >= C.MAX_AGE_HOURS // 24):
            dropped += 1
            return
        ensure_description(j)
        if prepare(j) is None:
            dropped += 1
            return
        if j["key"] not in run_keys:
            run_keys.add(j["key"])
            for t in j["tracks"]:
                alerts[t].append(j)
        seen[j["id"]] = now
        seen[j["key"]] = now

    # 1) Company career feeds
    if not args.no_companies:
        companies, errs = fetch_all_companies()
        for e in errs:
            print(f"!! {e}", file=sys.stderr)
        seeded = set(state.get("seeded_sources", []))
        for src, jobs in companies.items():
            before = sum(len(v) for v in alerts.values())
            for j in jobs:
                handle(j)
            seeded.add(src)
            added = sum(len(v) for v in alerts.values()) - before
            if added:
                print(f"   {src:<32} {len(jobs):>4} jobs, {added:>3} new alerts")
        state["seeded_sources"] = sorted(seeded)

    # 2) Free remote-job feeds
    if C.REMOTE_FEEDS and not args.no_boards:
        feed_jobs, ferrs = fetch_remote_feeds()
        for e in ferrs:
            print(f"!! {e}", file=sys.stderr)
        for j in feed_jobs:
            handle(j)

    # 3) LinkedIn / Indeed / ZipRecruiter / Glassdoor
    if not args.no_boards:
        board_jobs, ok, failed = fetch_boards()
        for j in board_jobs:
            handle(j)
        # Health check: warn once a day if the boards keep failing
        if ok == 0 and failed > 0:
            state["board_failures"] = state.get("board_failures", 0) + 1
            last = state.get("last_warning")
            if state["board_failures"] >= 3 and (not last or last < (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()):
                tg.send("⚠️ <b>Job bot:</b> all job-board searches (LinkedIn, Indeed...) have failed "
                        f"{state['board_failures']} runs in a row (probably rate-limited). "
                        "Company career feeds are still being checked.")
                state["last_warning"] = now
        elif ok:
            state["board_failures"] = 0

    # 4) Send: one message per resume, newest first
    for track in ("senior", "junior"):
        alerts[track].sort(key=sort_key)
    print(f"== {len(alerts['senior'])} senior + {len(alerts['junior'])} junior alerts; "
          f"{dropped} title matches filtered out (level, location, fit or age)")
    for track in ("senior", "junior"):
        for j in alerts[track]:
            print(f"   -> {track.upper():<6} {j['fit']:>3}% {age_label(j):<14} {j['company'][:24]:<24} | {j['title'][:60]}")
        send_track(tg, track, alerts[track])

    if args.dry_run:
        print("\n(dry run — state not saved)")
    else:
        save_state(state)


if __name__ == "__main__":
    main()
