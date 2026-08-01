#!/usr/bin/env python3
"""
mailchimp_draft.py — push a weekly AI-podcast newsletter to Mailchimp.

Creates BOTH:
  1. a reusable user template ("AI News Podcast Newsletter") — created once,
     refreshed in place every week with the latest HTML, and
  2. a send-ready campaign draft (status `save`) for this week's episode that
     references that template.

Nothing is ever sent to the audience unless you explicitly pass --test-email
(which sends only to the addresses you name). There is intentionally no
"send to everyone" path in this script.

Why a campaign draft and not just a template:
  A *template* is only a design — it can never be delivered. A *campaign* is the
  thing that sends (it has recipients, subject, from). We make both: the template
  for reuse, the campaign so you just review and click Send in Mailchimp.

Stdlib only — runs with any python3, no venv or pip needed.

Usage:
  python3 scripts/mailchimp_draft.py                       # newest newsletter, draft only
  python3 scripts/mailchimp_draft.py --episode 9
  python3 scripts/mailchimp_draft.py --episode 9 --test-email you@x.com
  python3 scripts/mailchimp_draft.py --subject "Custom subject line"
  python3 scripts/mailchimp_draft.py --dry-run             # resolve + plan, no API calls

Config (from the repo's gitignored .env):
  MAILCHIMP_API_KEY      e.g. abc...-us12  (datacenter is the suffix after the last '-')
  MAILCHIMP_AUDIENCE_ID  the "AI podcast" list id
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent          # .../02-ai-podcast-newsletter
ENV_FILE = REPO / ".env"
NEWSLETTERS = REPO / "newsletters"

# Sender defaults (confirmed working 2026-06-03).
FROM_NAME = "Ruth Tupe"
REPLY_TO = "ruth_tupe@mckinsey.com"
# Template is named per-episode by date, e.g. "June 02 2026" (matches Ruth's
# existing per-week template set in Mailchimp). Computed at runtime from the
# newsletter date; re-running the same episode refreshes that template in place.

TIMEOUT = 30


# ──────────────────────────────────────────────────────────────────────────────
# Config + HTTP
# ──────────────────────────────────────────────────────────────────────────────
def load_env() -> dict:
    if not ENV_FILE.exists():
        sys.exit(f"ERROR: {ENV_FILE} not found. It must hold MAILCHIMP_API_KEY + MAILCHIMP_AUDIENCE_ID.")
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$", line)
        if m:
            env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    for key in ("MAILCHIMP_API_KEY", "MAILCHIMP_AUDIENCE_ID"):
        if not env.get(key):
            sys.exit(f"ERROR: {key} missing/empty in {ENV_FILE}.")
    return env


class Mailchimp:
    def __init__(self, api_key: str):
        if "-" not in api_key:
            sys.exit("ERROR: MAILCHIMP_API_KEY has no datacenter suffix (expected '...-us12').")
        self.dc = api_key.rsplit("-", 1)[-1]
        self.base = f"https://{self.dc}.api.mailchimp.com/3.0"
        self.auth = "Basic " + base64.b64encode(f"anystring:{api_key}".encode()).decode()

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.base}{path}", data=data, method=method)
        req.add_header("Authorization", self.auth)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            try:
                j = json.loads(detail)
                detail = f"{j.get('title')}: {j.get('detail')}"
                if j.get("errors"):
                    detail += " | " + "; ".join(f"{x.get('field')}: {x.get('message')}" for x in j["errors"])
            except Exception:
                pass
            sys.exit(f"ERROR {e.code} on {method} {path}\n  {detail}")
        except urllib.error.URLError as e:
            sys.exit(f"ERROR: could not reach Mailchimp ({e.reason}).")

    def get(self, path):           return self._req("GET", path)
    def post(self, path, body):    return self._req("POST", path, body)
    def patch(self, path, body):   return self._req("PATCH", path, body)
    def put(self, path, body):     return self._req("PUT", path, body)


# ──────────────────────────────────────────────────────────────────────────────
# Newsletter resolution + parsing
# ──────────────────────────────────────────────────────────────────────────────
def resolve_newsletter(episode: int | None, html_arg: str | None) -> tuple[Path, int]:
    if html_arg:
        p = Path(html_arg)
        if not p.is_absolute():
            p = REPO / html_arg
        if not p.exists():
            sys.exit(f"ERROR: --html not found: {p}")
        m = re.search(r"episode-(\d+)-", p.name)
        return p, (episode if episode is not None else (int(m.group(1)) if m else 0))

    matches = sorted(NEWSLETTERS.glob("ai-podcast-episode-*.html"))
    if not matches:
        sys.exit(f"ERROR: no newsletters in {NEWSLETTERS}.")
    if episode is not None:
        for p in matches:
            if re.search(rf"episode-{episode}-", p.name):
                return p, episode
        sys.exit(f"ERROR: no newsletter for episode {episode} in {NEWSLETTERS}.")
    # newest by episode number
    def epnum(p):
        m = re.search(r"episode-(\d+)-", p.name)
        return int(m.group(1)) if m else -1
    newest = max(matches, key=epnum)
    return newest, epnum(newest)


def hero_alt(html: str) -> str | None:
    """Subject line default = the editorial theme.

    Prefers the <!-- EPISODE_THEME: ... --> marker (added so the hero image's
    alt text could become a plain accessibility description instead of
    doubling as the theme — see /podcast-email Step 7). Falls back to the
    hero alt text for older newsletters that predate the marker.
    """
    m = re.search(r"<!--\s*EPISODE_THEME:\s*(.+?)\s*-->", html)
    if m:
        return m.group(1).strip()
    m = re.search(r'<img[^>]*_hero\.jpg[^>]*\balt="([^"]*)"', html, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def template_name_for(html_path: Path) -> str:
    """Per-episode template name from the newsletter date, e.g. 'June 02 2026'."""
    from datetime import datetime
    m = re.search(r"(\d{4}-\d{2}-\d{2})", html_path.name)
    if not m:
        return html_path.stem
    return datetime.strptime(m.group(1), "%Y-%m-%d").strftime("%B %d %Y")


# ──────────────────────────────────────────────────────────────────────────────
# Template + campaign
# ──────────────────────────────────────────────────────────────────────────────
def upsert_template(mc: Mailchimp, name: str, html: str) -> str:
    """Create the per-episode template, or refresh it in place if it already exists."""
    existing = mc.get("/templates?type=user&count=1000&fields=templates.id,templates.name")
    tid = None
    for t in existing.get("templates", []):
        if t.get("name") == name:
            tid = t["id"]
            break
    if tid:
        mc.patch(f"/templates/{tid}", {"name": name, "html": html})
        print(f"  template refreshed: '{name}' (id {tid})")
    else:
        created = mc.post("/templates", {"name": name, "html": html})
        tid = created["id"]
        print(f"  template created: '{name}' (id {tid})")
    return str(tid)


def find_draft_campaign(mc: Mailchimp, title: str) -> str | None:
    """Reuse an existing unsent draft with the same internal title (avoids dupes on re-run)."""
    r = mc.get("/campaigns?count=50&status=save&sort_field=create_time&sort_dir=DESC"
               "&fields=campaigns.id,campaigns.settings.title,campaigns.status")
    for c in r.get("campaigns", []):
        if c.get("settings", {}).get("title") == title:
            return c["id"]
    return None


def set_campaign_content(mc: Mailchimp, campaign_id: str, template_id: str, html: str) -> None:
    """Point the campaign at the template; verify it rendered, else fall back to raw HTML."""
    mc.put(f"/campaigns/{campaign_id}/content", {"template": {"id": int(template_id), "sections": {}}})
    check = mc.get(f"/campaigns/{campaign_id}/content?fields=html")
    if len(check.get("html") or "") > 500:
        print("  content set from template ✓")
        return
    print("  template render came back empty — falling back to raw HTML")
    mc.put(f"/campaigns/{campaign_id}/content", {"html": html})
    print("  content set from raw HTML ✓")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--episode", type=int, default=None, help="Episode number (default: newest newsletter).")
    ap.add_argument("--html", default=None, help="Explicit newsletter HTML path (overrides --episode lookup).")
    ap.add_argument("--subject", default=None, help="Subject line (default: hero image alt text).")
    ap.add_argument("--test-email", default=None,
                    help="Comma-separated addresses to send a TEST to after the draft is built. "
                         "Sends only to these addresses, never the full audience.")
    ap.add_argument("--dry-run", action="store_true", help="Resolve everything and print the plan; no API calls.")
    args = ap.parse_args()

    html_path, episode = resolve_newsletter(args.episode, args.html)
    html = html_path.read_text()
    subject = args.subject or hero_alt(html)
    if not subject:
        sys.exit("ERROR: could not derive a subject from the hero alt text — pass --subject.")
    title = f"AI Podcast Episode {episode}"
    template_name = template_name_for(html_path)

    print(f"Newsletter: {html_path.name}  ({len(html):,} bytes)")
    print(f"Episode:    {episode}")
    print(f"Subject:    {subject}")
    print(f"Template:   '{template_name}' (per-episode, refreshed on re-run)")
    print(f"Campaign:   '{title}'  from {FROM_NAME} <{REPLY_TO}>")
    if args.test_email:
        print(f"Test send:  {args.test_email}")

    if args.dry_run:
        print("\n[dry-run] no API calls made.")
        return 0

    env = load_env()
    mc = Mailchimp(env["MAILCHIMP_API_KEY"])
    list_id = env["MAILCHIMP_AUDIENCE_ID"]

    # sanity: audience reachable
    aud = mc.get(f"/lists/{list_id}?fields=name,stats.member_count")
    print(f"\nAudience: {aud.get('name')} ({aud.get('stats', {}).get('member_count')} members)")

    template_id = upsert_template(mc, template_name, html)

    campaign_id = find_draft_campaign(mc, title)
    if campaign_id:
        print(f"  reusing existing draft campaign (id {campaign_id})")
    else:
        created = mc.post("/campaigns", {
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": subject,
                "title": title,
                "from_name": FROM_NAME,
                "reply_to": REPLY_TO,
            },
        })
        campaign_id = created["id"]
        print(f"  campaign draft created (id {campaign_id})")

    set_campaign_content(mc, campaign_id, template_id, html)

    info = mc.get(f"/campaigns/{campaign_id}?fields=web_id,status")
    web_id = info.get("web_id")
    print(f"\nDraft ready (status: {info.get('status')})")
    print(f"Open in Mailchimp: https://{mc.dc}.admin.mailchimp.com/campaigns/edit?id={web_id}")

    if args.test_email:
        emails = [e.strip() for e in args.test_email.split(",") if e.strip()]
        mc.post(f"/campaigns/{campaign_id}/actions/test", {"test_emails": emails, "send_type": "html"})
        print(f"Test email sent to: {', '.join(emails)}")

    print("\nNothing was sent to the audience. Review the draft and click Send in Mailchimp when ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
