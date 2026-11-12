"""Download the full text of every job the bot has alerted on, for analysis.

state/seen_jobs.json only keeps IDs and "company|title" keys. This re-reads the
company feeds (Greenhouse, Lever, Ashby) with descriptions and keeps the jobs whose
ID is in seen_jobs.json. LinkedIn/Indeed jobs have no stored text, so only their
titles (from the keys) are kept. Postings that have since closed are skipped.

    cd ~/Downloads/Job_Search_Bot && git pull && python3 Analysis/scripts/fetch_details.py
Writes Analysis/data/jobs_snapshot.json.
"""
import html
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repo root
sys.path.insert(0, str(ROOT / "bot"))
import bot  # noqa: E402  (reuses its fetchers and HTTP helper)
import config  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "jobs_snapshot.json"


def strip_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", s).strip()


def greenhouse_full(slug: str, name: str) -> list[dict]:
    d = bot.http_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    return [dict(id=f"gh:{slug}:{j['id']}", title=j.get("title", ""), company=name,
                 location=(j.get("location") or {}).get("name", ""), url=j.get("absolute_url", ""),
                 description=strip_html(j.get("content", "")))
            for j in d.get("jobs", [])]


def main() -> None:
    state = json.loads((ROOT / "state" / "seen_jobs.json").read_text())
    seen = state["seen"]
    wanted = defaultdict(set)
    for k in seen:
        if "|" not in k and k.split(":")[0] in ("gh", "lever", "ashby"):
            ats, slug, _ = k.split(":", 2)
            wanted[(ats, slug)].add(k)

    names = {}
    for ats_full, slug, name in config.TARGET_COMPANIES:
        ats = {"greenhouse": "gh"}.get(ats_full, ats_full)
        names[(ats, slug)] = (ats_full, name)

    def grab(key):
        ats_full, name = names.get(key, (None, key[1]))
        try:
            if key[0] == "gh":
                jobs = greenhouse_full(key[1], name)
            else:
                jobs = bot.fetch_company(ats_full, key[1], name)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {key}: {e}")
            return []
        return [j for j in jobs if j["id"] in wanted[key]]

    with ThreadPoolExecutor(8) as pool:
        company_jobs = [j for batch in pool.map(grab, list(wanted)) for j in batch]
    for j in company_jobs:
        j["description"] = j.get("description") or ""
        j["source"] = "company"

    titles_only = [dict(company=k.split("|", 1)[0], title=k.split("|", 1)[1])
                   for k in seen if "|" in k]
    want_n = sum(len(v) for v in wanted.values())
    print(f"company jobs: {len(company_jobs)} of {want_n} still open; all titles: {len(titles_only)}")
    OUT.write_text(json.dumps({"company_jobs": company_jobs, "all_titles": titles_only}, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
