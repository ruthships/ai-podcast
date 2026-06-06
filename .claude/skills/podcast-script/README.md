# podcast-script — Claude Code Skill

A Claude Code skill that automates weekly AI news podcast prep: newsletter ingestion → parallel web research → story ranking → two-host script generation. Output feeds the rest of the AI news podcast pipeline (`/podcast-audio`, `/podcast-postprocess`, `/podcast-email`, `/podcast-website`).

## What it does

Trigger with `/podcast-script`. Runs 4 phases automatically:

1. **Email Collection** — fetches AI newsletters from Outlook (script, `--fetch-only`), then the agent builds a tiered digest in Cursor (no Anthropic API key for this step)
2. **Web Research** — launches 5 parallel agents searching for breaking AI news by vertical (OpenAI, Google/Anthropic, regulation, Meta/xAI, enterprise)
3. **Synthesis** — merges and deduplicates all sources, ranks into Tier 1/2/3 by exec relevance
4. **Script Generation** — you pick stories, Claude generates a two-host podcast script with fact-checking, plus TTS-ready JSON for ElevenLabs

Output: a polished two-host MP3 (via ElevenLabs) + a full NotebookLM-ready story list.

## Prerequisites

- **Claude Code** (claude-code >= 1.0)
- **Microsoft Outlook** on macOS (for email collection via AppleScript)
- **ElevenLabs account** (downstream `/podcast-audio` — optional for script-only runs)
- **Anthropic API key** — only if you run `fetch_ai_emails.py` without `--fetch-only` (legacy); normal `/podcast-script` flow does not need it
- The `/email` skill installed and configured (`/email setup` run once)

## Setup

### 1. Install the skill

Copy this folder to your Claude skills directory (or symlink your `01-ai-podcast-script` repo):
```bash
cp -r ~/Code/01-ai-podcast-script ~/.claude/skills/podcast-script
```

### 2. Configure your Outlook account

Run the email skill setup if you haven't already:
```
/email setup
```

This creates `~/.claude/email_config.json` with your Outlook account.

Optionally add a `podcast_dir` key to set where output files are saved (default: `~/Code/ai-podcast-newsletter`):
```json
{
  "account": "you@company.com",
  "podcast_dir": "~/Code/ai-podcast-newsletter"
}
```

### 3. Add newsletter sources

Edit `scripts/fetch_ai_emails.py` and add your newsletter sender addresses to `AI_SENDER_EMAILS`:

```python
AI_SENDER_EMAILS = [
    "clawdlcg@gmail.com",          # HN AI Digest (default)
    "your-newsletter@example.com",  # add yours here
]
```

Subject-keyword fallback is also available via `AI_SUBJECT_KEYWORDS` if you want to catch newsletters whose senders vary (left empty by default — sender filter only).

### 4. Set up ElevenLabs (optional — for audio generation)

- Get your API key from [elevenlabs.io](https://elevenlabs.io) and set `ELEVENLABS_API_KEY` in your environment
- Pick two voice IDs from the [ElevenLabs voice library](https://elevenlabs.io/voice-library)
- Update `VOICE_HOST_A` and `VOICE_HOST_B` in the notebook config (Phase 5 in SKILL.md)

## Usage

```
/podcast-script
```

Claude runs Phases 1–3 automatically, presents a ranked story list, asks which stories to cover, then generates the script and stories markdown files. Audio generation is now a separate downstream skill (`/podcast-audio`).

## File structure

```
podcast-script/
  SKILL.md                          # main orchestration instructions
  scripts/
    fetch_ai_emails.py              # Outlook fetcher (AppleScript; --fetch-only by default in skill)
  references/
    ai_news_digest_prompt.md        # agent instructions to build tiered digest from raw emails
    search_topics.md                # search instructions for the 5 parallel web agents
```

## Output files

All saved to your `podcast_dir` (default: `~/Code/ai-podcast-newsletter/`):

| File | Description |
|------|-------------|
| `podcast_stories_YYYY-MM-DD.md` | Full ranked story list with sources |
| `podcast_script_YYYY-MM-DD.md` | Two-host podcast script (fact-checked) |
| `YYYY-MM-DD/podcast_script_vN.json` | TTS-ready JSON for ElevenLabs |
| `YYYY-MM-DD/podcast_generator_elevenlabs.ipynb` | Jupyter notebook for audio generation |
| `YYYY-MM-DD/audio_output_elevenlabs/*/final_podcast.mp3` | Final episode MP3 |

## Cached files (`~/.claude/`)

| File | Created by |
|------|------------|
| `raw_emails_YYYY-MM-DD.md` | `fetch_ai_emails.py --fetch-only` |
| `ai_news_digest_YYYY-MM-DD.md` | Cursor agent (Phase 1c) |

Re-running the same day skips fetch/digest if the digest file already exists.

## Dependencies

`fetch_ai_emails.py` with `--fetch-only` needs only Python 3 and Outlook access.

Legacy full mode (no `--fetch-only`) also needs `anthropic` and `python-dotenv` plus `ANTHROPIC_API_KEY` in `.env`.

Install into the email skill's venv:
```bash
~/.claude/email-venv/bin/pip install anthropic python-dotenv
```

## License

MIT
