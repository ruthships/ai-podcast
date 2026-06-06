import subprocess
import sys
import os
import argparse
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
MAX_EMAILS = 200  # scan enough to cover a full week of inbox
CLAUDE_DIR = Path.home() / ".claude"

# AI news sources to keep (case-insensitive matching)
# Subject keyword filter — leave empty unless you want to catch newsletters by subject pattern.
AI_SUBJECT_KEYWORDS = []

# Sender email filter — newsletter senders to capture.
AI_SENDER_EMAILS = [
    "clawdlcg@gmail.com",       # HN AI Digest (LC's daily HN-ranked AI stories, ~6 editions/week)
    # "your-newsletter@example.com",  # add additional senders here
]
# ───────────────────────────────────────────────────────────────────────────────


def make_applescript(hours: int, account: str) -> str:
    return f"""
tell application "Microsoft Outlook"
    with timeout of 300 seconds
        set theInbox to mail folder "Inbox" of exchange account "{account}"
        set cutoffDate to (current date) - ({hours} * hours)
        set recentMsgs to (messages of theInbox whose time received >= cutoffDate)
        set msgCount to count of recentMsgs
        if msgCount is 0 then return "NO_EMAILS"

        set output to "COUNT:" & msgCount & return
        set i to 0
        repeat with aMsg in recentMsgs
            if i >= {MAX_EMAILS} then exit repeat
            set i to i + 1

            set msgTime to time received of aMsg as string

            try
                set msgSubj to subject of aMsg
            on error
                set msgSubj to "(no subject)"
            end try

            set senderStr to "Unknown <unknown>"
            try
                set theSender to sender of aMsg
                set senderStr to (name of theSender) & " <" & (address of theSender) & ">"
            end try

            set bodyStr to ""
            try
                set bodyStr to plain text content of aMsg
                -- Truncate very long bodies to avoid AppleScript limits
                if (count of bodyStr) > 8000 then
                    set bodyStr to (text 1 thru 8000 of bodyStr) & "... [truncated]"
                end if
            end try

            set output to output & "---MSG " & i & "---" & return
            set output to output & "TIME: " & msgTime & return
            set output to output & "FROM: " & senderStr & return
            set output to output & "SUBJECT: " & msgSubj & return
            set output to output & "BODY:" & return & bodyStr & return & return
        end repeat

        return output
    end timeout
end tell
"""


def fetch_raw_emails(hours: int, account: str) -> tuple[int, str]:
    script = make_applescript(hours, account)
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("AppleScript error:", result.stderr)
        sys.exit(1)

    raw = result.stdout.strip()
    if raw == "NO_EMAILS":
        return 0, ""

    lines = raw.split("\n", 1)
    count_line = lines[0]
    body = lines[1] if len(lines) > 1 else ""
    count = int(count_line.replace("COUNT:", "").strip()) if count_line.startswith("COUNT:") else 0
    return count, body


def filter_ai_emails(raw_body: str) -> list[dict]:
    """Parse raw email output and filter to AI news sources only."""
    emails = []
    blocks = raw_body.split("---MSG ")
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        parsed = {"raw": block}
        body_lines = []
        in_body = False

        for line in lines:
            if line.startswith("TIME: "):
                parsed["time"] = line[6:]
            elif line.startswith("FROM: "):
                parsed["from"] = line[6:]
            elif line.startswith("SUBJECT: "):
                parsed["subject"] = line[9:]
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)

        parsed["body"] = "\n".join(body_lines)

        # Filter: keep if sender matches or subject matches
        sender = parsed.get("from", "").lower()
        subject = parsed.get("subject", "").lower()

        sender_match = any(s in sender for s in AI_SENDER_EMAILS)
        subject_match = any(k in subject for k in AI_SUBJECT_KEYWORDS)

        if sender_match or subject_match:
            emails.append(parsed)

    return emails


AI_NEWS_PROMPT = """You are a research assistant helping prepare an AI podcast for senior executives.

Below are AI newsletter emails from the past 7 days. Your job is to:

1. **Filter out** all promotional content, sponsored posts, job listings, and advertisements
2. **Extract** each distinct AI story/development as a structured entry
3. **Tier** each story by relevance to senior business executives:
   - **Tier 1 — Must-Cover**: Major model releases, breakthrough capabilities, significant business deals/partnerships, regulatory moves with real business impact, major AI company news (funding, acquisitions, leadership changes)
   - **Tier 2 — Strong Interest**: New product launches, enterprise AI adoption stories, meaningful research papers with business implications, policy developments
   - **Tier 3 — Worth Knowing**: Technical deep-dives, niche research, community trends, minor updates

Output format — produce a markdown document with this structure:

# AI News Digest — {date}
_Source: newsletters and email scrapers_

## Tier 1 — Must-Cover
### [Story Title]
- **What happened**: [1-2 sentence factual summary]
- **Why it matters for execs**: [1 sentence business/strategic relevance]
- **Source email**: [newsletter name, e.g. TLDR AI, GitHub scraper]
- **Keywords**: [3-5 tags for search]

## Tier 2 — Strong Interest
[same format]

## Tier 3 — Worth Knowing
[same format]

---

Be factual, direct, and ruthlessly filter out anything promotional. If an email is mostly ads, extract only the actual news items buried in it.
"""


def format_raw_emails_file(emails: list[dict], total_count: int, today_str: str) -> str:
    """Format filtered newsletters for agent-side digest building."""
    header = f"# Raw AI Newsletter Emails — {today_str}\n"
    header += f"_Scanned {total_count} inbox emails → {len(emails)} AI newsletters matched_\n"
    if not emails:
        return header + "\n_No AI newsletter emails found in the specified time window._\n"

    body = ""
    for i, email in enumerate(emails, 1):
        body += f"\n\n=== EMAIL {i} ===\n"
        body += f"FROM: {email.get('from', 'Unknown')}\n"
        body += f"SUBJECT: {email.get('subject', 'No subject')}\n"
        body += f"TIME: {email.get('time', 'Unknown')}\n"
        body += f"BODY:\n{email.get('body', '')}\n"
    return header + body


def save_raw_emails(emails: list[dict], total_count: int) -> Path:
    today_str = date.today().isoformat()
    content = format_raw_emails_file(emails, total_count, today_str)
    CLAUDE_DIR.mkdir(exist_ok=True)
    out_path = CLAUDE_DIR / f"raw_emails_{today_str}.md"
    out_path.write_text(content)
    return out_path


def build_ai_digest(emails: list[dict]) -> str:
    if not emails:
        return "# AI News Digest\n\n_No AI newsletter emails found in the specified time window._\n"

    client = Anthropic(
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    today_str = date.today().isoformat()
    prompt = AI_NEWS_PROMPT.replace("{date}", today_str)

    # Format emails for Claude
    emails_text = ""
    for i, email in enumerate(emails, 1):
        emails_text += f"\n\n=== EMAIL {i} ===\n"
        emails_text += f"FROM: {email.get('from', 'Unknown')}\n"
        emails_text += f"SUBJECT: {email.get('subject', 'No subject')}\n"
        emails_text += f"TIME: {email.get('time', 'Unknown')}\n"
        emails_text += f"BODY:\n{email.get('body', '')}\n"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt + "\n\n---\nEMAILS:\n" + emails_text}],
    )
    return response.content[0].text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch AI news emails from Outlook")
    parser.add_argument(
        "--hours", type=int, default=168,
        help="Fetch emails from last N hours (default: 168 = 7 days)"
    )
    parser.add_argument(
        "--account", type=str, required=True,
        help="Outlook exchange account email (e.g. name@company.com)"
    )
    parser.add_argument(
        "--fetch-only", action="store_true",
        help="Save filtered newsletter text only; do not call Anthropic API",
    )
    args = parser.parse_args()

    print(f"Scanning inbox for AI news emails from the last {args.hours} hours...")
    total_count, raw_body = fetch_raw_emails(args.hours, args.account)

    if total_count == 0:
        print(f"No emails in the last {args.hours} hours.")
        sys.exit(0)

    print(f"Scanned {total_count} emails. Filtering for AI newsletters...")
    ai_emails = filter_ai_emails(raw_body)

    if not ai_emails:
        print("No AI newsletter emails found matching subject or sender filters.")
        print(f"Subject keywords: {AI_SUBJECT_KEYWORDS}")
        print(f"Sender emails: {AI_SENDER_EMAILS}")
        today_str = date.today().isoformat()
        if args.fetch_only:
            out_path = save_raw_emails([], total_count)
            print(f"Saved empty raw file to: {out_path}")
            print("Agent should build an empty digest from this file.")
        else:
            empty = f"# AI News Digest — {today_str}\n\n_No AI newsletter emails found._\n"
            out_path = CLAUDE_DIR / f"ai_news_digest_{today_str}.md"
            out_path.write_text(empty)
            print(f"Saved empty digest to: {out_path}")
        sys.exit(0)

    if args.fetch_only:
        out_path = save_raw_emails(ai_emails, total_count)
        print(f"Found {len(ai_emails)} AI newsletter email(s).")
        print(f"Saved raw newsletters to: {out_path}")
        print("Next: agent builds digest (see podcast-script Phase 1b).")
        sys.exit(0)

    print(f"Found {len(ai_emails)} AI newsletter email(s). Extracting stories with Claude...")
    digest_md = build_ai_digest(ai_emails)

    today_str = date.today().isoformat()
    header = f"# AI News Digest — {today_str}\n"
    header += f"_Scanned {total_count} inbox emails → {len(ai_emails)} AI newsletters matched_\n\n"

    full_content = header + digest_md

    CLAUDE_DIR.mkdir(exist_ok=True)
    out_path = CLAUDE_DIR / f"ai_news_digest_{today_str}.md"
    out_path.write_text(full_content)

    print("=" * 60)
    print(f"AI NEWS DIGEST ({today_str})")
    print("=" * 60)
    print(digest_md)
    print()
    print(f"Saved to: {out_path}")
