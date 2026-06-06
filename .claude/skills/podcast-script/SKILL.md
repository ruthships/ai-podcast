---
name: podcast-script
description: "Weekly AI podcast prep. Pulls AI news from Outlook (fetch-only script), builds tiered email digest in-session, runs parallel web research agents, synthesizes into a ranked story list, then generates a NotebookLM prompt and podcast script after you pick topics. Trigger on /podcast-script."
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebSearch
  - Task
compatibility: "claude-code>=1.0"
---

# Podcast Script Prep — `/podcast-script`

Automates weekly podcast prep in 4 phases: email collection → web research → synthesis → script generation.

---

## Step 0: Config Check

```bash
cat ~/.claude/email_config.json 2>/dev/null || echo "NOT_FOUND"
```

- **NOT_FOUND** → tell user to run `/email setup` first to configure their Outlook account, then retry.
- **Exists** → extract `account` value. Use it in all script calls.

Also set:
```bash
VENV=~/.claude/email-venv
TODAY=$(date +%Y-%m-%d)
PROJECT_DIR=~/Code/02-ai-podcast-newsletter   # override via email_config.json "podcast_dir"
# Skills are vendored inside the newsletter repo; fall back to legacy locations.
if [ -f "$PROJECT_DIR/.claude/skills/podcast-script/scripts/fetch_ai_emails.py" ]; then
  SCRIPTS="$PROJECT_DIR/.claude/skills/podcast-script/scripts"
  REFS="$PROJECT_DIR/.claude/skills/podcast-script/references"
elif [ -f ~/Code/01-ai-podcast-script/scripts/fetch_ai_emails.py ]; then
  SCRIPTS=~/Code/01-ai-podcast-script/scripts
  REFS=~/Code/01-ai-podcast-script/references
elif [ -f ~/.claude/skills/podcast-script/scripts/fetch_ai_emails.py ]; then
  SCRIPTS=~/.claude/skills/podcast-script/scripts
  REFS=~/.claude/skills/podcast-script/references
fi
```

If `email_config.json` has a `podcast_dir` key, use that value instead of the default.

---

## Phase 1 — Email Collection

**Goal:** Pull AI newsletter emails from the last 7 days and build a tiered story digest.

### 1a — Check for cached digest

```bash
cat ~/.claude/ai_news_digest_$(date +%Y-%m-%d).md 2>/dev/null || echo "NOT_FOUND"
```

- **Found** → say "Using today's cached AI news digest." and skip to Phase 2.
- **NOT_FOUND** → continue below.

### 1b — Fetch raw newsletters from Outlook (no API key)

Run only if today's digest is missing:

```bash
ACCOUNT=$(python3 -c "import json; d=json.load(open('$HOME/.claude/email_config.json')); print(d['account'])")
$VENV/bin/python "$SCRIPTS/fetch_ai_emails.py" --hours 168 --account "$ACCOUNT" --fetch-only
```

The script:
- Scans the last 168h (7 days) of inbox via AppleScript (Outlook must be running)
- Keeps emails matching `AI_SENDER_EMAILS` / `AI_SUBJECT_KEYWORDS` in `fetch_ai_emails.py`
- Saves filtered text to `~/.claude/raw_emails_YYYY-MM-DD.md` (does **not** call Anthropic)

If the raw file already exists for today and digest is still missing, skip the script and use the existing raw file.

### 1c — Build digest in this session (Cursor / Claude Code)

1. Read `~/.claude/raw_emails_$(date +%Y-%m-%d).md`
2. Read digest instructions: `$REFS/ai_news_digest_prompt.md`
3. Follow those instructions and **write** `~/.claude/ai_news_digest_YYYY-MM-DD.md` (use the Write tool)
4. Confirm with:
```bash
cat ~/.claude/ai_news_digest_$(date +%Y-%m-%d).md
```

Say: "✓ Phase 1 complete — digest ready from newsletters. Launching web research agents..."

---

## Phase 2 — Parallel Web Research Agents

**Goal:** Search for breaking AI news the newsletters may have missed.

Read the agent instructions from:
```bash
cat "$REFS/search_topics.md"
```

Then launch **5 web search agents in parallel** using the Task tool (subagent_type: `general-purpose`). Each agent:
- Searches for AI news from the last 7 days in its assigned vertical
- Returns a structured list of stories with URLs and dates
- See `references/search_topics.md` for exact search queries and output format per agent

**Launch all 5 Task agents simultaneously** (single message, 5 tool calls):

- **Agent 1**: OpenAI breaking news (models, products, policy, personnel)
- **Agent 2**: Google DeepMind + Anthropic breaking news
- **Agent 3**: AI regulation & policy news
- **Agent 4**: Meta / xAI / other model labs
- **Agent 5**: Enterprise AI & economic impact

Wait for all 5 to return before proceeding.

Compile all agent results into a section:
```markdown
## Breaking News (Web Research)
[Agent 1 results]
[Agent 2 results]
...
```

Say: "✓ Phase 2 complete — web research done. Synthesizing everything..."

---

## Phase 3 — Synthesis & Ranking

**Goal:** Merge newsletter stories + web research, deduplicate, and re-rank.

Use the following synthesis prompt internally (do NOT show it to the user):

```
You are preparing a weekly AI podcast briefing for senior executives (C-suite, board members, managing directors).

You have two inputs:
1. AI news digest from newsletters (last 7 days)
2. Breaking news from web research agents (last 7 days)

Your tasks:
1. MERGE all stories into one unified list
2. DEDUPLICATE: if the same story appears in multiple sources, combine into one entry and list all sources
3. RANK by executive relevance using this tier system:
   - Tier 1 — Must-Cover: Major model releases, significant business deals, regulatory moves with real impact, major AI company news
   - Tier 2 — Strong Interest: New products, enterprise adoption, meaningful research, policy developments
   - Tier 3 — Worth Knowing: Technical deep-dives, niche research, minor updates
4. For each story, include at least one reliable source URL (prefer primary sources over aggregators)
5. Write in plain, direct language — no hype, no filler

Output format:
---
# AI Podcast Story List — [DATE]
_[N] stories | Newsletter sources: [list] | Web research: 5 agents_

## Tier 1 — Must-Cover
### [N]. [Story Title]
- **Summary**: [2-3 factual sentences]
- **Exec angle**: [why this matters strategically/competitively]
- **Sources**: [URL1], [URL2]

## Tier 2 — Strong Interest
[same format]

## Tier 3 — Worth Knowing
[same format]
---
```

Run the synthesis. Save the result:
```bash
# Save to ~/.claude/
cat > ~/.claude/ai_podcast_stories_$(date +%Y-%m-%d).md << 'HEREDOC'
[synthesized content]
HEREDOC

# Also save to project folder
mkdir -p $PROJECT_DIR
cp ~/.claude/ai_podcast_stories_$(date +%Y-%m-%d).md \
   $PROJECT_DIR/podcast_stories_$(date +%Y-%m-%d).md
```

Say: "✓ Phase 3 complete — stories synthesized and saved."

---

## Phase 4 — Human in the Loop

**Goal:** User picks topics → generate NotebookLM prompt + podcast script.

### Step 4a: Present the ranked list

Display the full synthesized story list clearly. Number each story sequentially across all tiers (1, 2, 3... not 1.1, 1.2).

Then ask:

> **Which stories do you want to cover this week?**
> Reply with story numbers (e.g. `1, 3, 5, 7`) or ranges (e.g. `1-4, 6`).
> You can also say "all Tier 1" or "skip #N".
>
> Typically 4-6 stories make a good 20-30 minute episode.

### Step 4b: After topics are selected

Generate three outputs. Save all to the project folder:

#### Output 1: Podcast script

A full two-host script for the selected stories. Follow all style rules below exactly.

**STYLE RULES (follow precisely):**
- **Source-bound**: Every claim, figure, statistic, and named entity must come directly from the source material. Do not extrapolate, infer, or fill gaps with general knowledge. If something is not in the sources, it does not go in the script.
- **Factual only**: Report what happened. Explain tech concepts. Connect events. Do NOT give recommendations, opinions, or tell listeners what to do. Never write "executives should...", "your next step is...", "you should consider..."
- **Turn structure**: Host 1 speaks in 2-3 sentence blocks carrying facts and explanations. Host 2 speaks in 1-2 sentence turns only. Ratio ~75% Host 1 / 25% Host 2.
- **Host 2 minimum length**: Every Host 2 turn must be at least 20 words — TTS cannot render intonation from short fragments. Expand if needed.
- **Host 2 variety**: Mix ~50% questions, ~40% statements, ~10% exclamations. Never all questions. Use `!` for the two most striking data points.
- **Host 1 acknowledgment**: Host 1 must briefly acknowledge Host 2 at the start of each response — "Right —", "Exactly —", "That's right.", "That's the structure." Never ignore what Host 2 just said.
- **Natural fillers**: Add conversational fillers to Host 2 — "I mean,", "Wait —", "So, " at the start of questions. Makes TTS sound spontaneous, not read.
- **No colons before numbers**: Never write "Valuation: $350 billion" — TTS pauses unnaturally on colons. Write "at a $350 billion valuation" instead.
- **No mid-sentence question marks**: "Wait, both of them? At the same time?" causes TTS to pause hard mid-sentence. Use em-dash instead: "Wait — both of them, at the same time?"
- **Em-dash + possessive apostrophe**: `— Name's` (e.g. `— AlphaFold's`) triggers a stutter/artifact on `eleven_turbo_v2_5`. Break into two sentences with `<break time="200ms"/>` instead: `"...worth sitting with. <break time="200ms"/> AlphaFold's..."`
- **SSML breaks**: Use `<break time="300ms"/>` before the most dramatic reveal in each story. Use `<break time="250ms"/>` for moderate pauses. Embed directly in Host 1's text. These are processed by ElevenLabs.
- **Intro framing**: Open with the week's overall theme, not a list of topics. Don't lead with sensitive content (e.g. mass casualty) — frame around the broader implication (e.g. "AI liability").
- **Reactions**: Host 2 uses only: `"Right."` `"Yeah."` `"Exactly."` `"I mean"` `"Oh wow."` (once only — the single most surprising data point). Never "Sure", "Absolutely", "Great point", "Interesting."
- **Transitions**: Use a thematic bridge connecting end of one story to start of next. Never "Next up" or "Moving on." No `---` section breaks in the script.
- **Conclusions**: Declarative, not hedged. "The era of X is narrowing." not "This may signal..."
- **No host introductions by name.**
- **Accessibility**: Briefly introduce any company or concept a non-technical listener wouldn't know on first mention (e.g. "Anthropic — the AI safety company behind Claude").

```markdown
# AI Weekly Podcast — [DATE]
_Topics: [list of selected story titles]_
_Runtime estimate: ~[N] minutes_

---

## INTRO

**HOST 1:** Welcome to the AI podcast. <break time="300ms"/> It's [MONTH DAY, YEAR], and this week [1-2 sentences framing the week's overall theme — not a list of topics.]

**HOST 2:** [Short affirming reaction + one line on stakes.]

**HOST 1:** Let's get into it.

---

## STORY 1: [Title]

**HOST 1:** [Introduce what happened — 2-3 factual sentences]

**HOST 2:** [Short mid-explanation question or reaction]

**HOST 1:** [Continue explanation — analogy if technical, implications stated as facts not recommendations]

**HOST 2:** [Analogy echo or brief clarifying question]

**HOST 1:** [Conclude story — declarative statement of what this means]

[Thematic bridge to next story]

[Continue for each selected story with same pattern — vary who drives, ensure Host 2 never dominates]

---

## CLOSING

**HOST 1:** [1-sentence thematic synthesis across the episode — no story recap]

**HOST 2:** [One short aphorism or observation that closes the episode]

**HOST 1:** Thanks for listening. See you next week.

---
_Sources: [list all URLs used in this episode]_
```

Save as: `$PROJECT_DIR/podcast_script_YYYY-MM-DD.md`

### Step 4d: Fact-check the script

After saving the script, launch a fact-checking agent to verify every claim against the sources.

Use the Task tool (subagent_type: `general-purpose`) with this prompt:

```
You are a rigorous fact-checker for a podcast script. Your job is to verify every factual claim in the script against the provided source URLs.

SCRIPT:
[paste full script content]

SOURCES:
[paste all source URLs used in the episode]

Instructions:
1. Extract every factual claim from the script — especially all figures, statistics, dollar amounts, percentages, dates, named entities, and quoted statements.
2. For each claim, fetch the corresponding source URL and verify whether the claim is:
   - VERIFIED: exactly matches the source
   - MODIFIED: directionally correct but the specific figure or wording differs from the source — show both versions
   - NOT FOUND: cannot be verified in any of the provided sources
   - CONTRADICTED: the source says something different
3. Output a fact-check report in this format:

---
## Fact-Check Report

### ✅ Verified
- "[exact claim from script]" — confirmed in [URL]

### ⚠️ Modified (needs correction)
- Script says: "[claim]"
- Source says: "[actual figure/wording]"
- Source: [URL]

### ❓ Not Found in Sources
- "[claim]" — could not be verified in any provided source

### ❌ Contradicted
- Script says: "[claim]"
- Source says: "[contradicting info]"
- Source: [URL]
---

Be thorough. Flag anything you cannot confirm. Do not approve claims based on general knowledge — only what the sources explicitly state.
```

Wait for the agent to return. Then:
- If there are **Modified**, **Not Found**, or **Contradicted** items: correct the script before saving the final version, and note what was changed.
- If everything is **Verified**: confirm and proceed.

Say: "✓ Fact-check complete — [N] claims verified, [N] corrections made." and list any corrections applied.

### Step 4c: Set up ElevenLabs folder and confirm completion

After saving the script, immediately run Phase 5 setup (Steps 5a–5c) to create the episode folder, convert the script to JSON, copy the notebook, and update its config. Do this without waiting for the user to ask.

Then say:

---
**All podcast prep files saved to `$PROJECT_DIR/`:**
- `podcast_stories_YYYY-MM-DD.md` — full story list with sources
- `podcast_script_YYYY-MM-DD.md` — final fact-checked two-host script
- `YYYY-MM-DD/podcast_script_YYYY-MM-DD.json` — TTS-ready JSON
- `YYYY-MM-DD/podcast_generator_elevenlabs.ipynb` — notebook ready to run

**To generate audio:**
1. Open `YYYY-MM-DD/podcast_generator_elevenlabs.ipynb` in Jupyter
2. Run all cells top to bottom — test run uses first 6 segments
3. If test sounds good, set `MAX_SEGMENTS = None` in `cell-config` and re-run for full episode
4. Final MP3 → `YYYY-MM-DD/audio_output_elevenlabs/<timestamp>/final_podcast.mp3`
---

---

## Phase 5 — TTS Audio Generation (ElevenLabs)

**Goal:** Convert the final script to a polished two-host MP3 using ElevenLabs.

This phase uses a Jupyter notebook (`podcast_generator_elevenlabs.ipynb`) in the episode folder.

### Step 5a: Set up the notebook

Copy the template notebook from the skill's scripts folder:
```bash
cp ~/.claude/skills/podcast-script/scripts/podcast_generator_elevenlabs.ipynb \
   $PROJECT_DIR/YYYY-MM-DD/podcast_generator_elevenlabs.ipynb
```

If the template doesn't exist yet, check `$PROJECT_DIR` for a notebook from a previous episode and copy that instead.

### Step 5b: Convert script to JSON

The notebook consumes a JSON file, not the markdown script. Convert the `.md` script to a structured JSON:

```json
{
  "episode_title": "AI Podcast: [DATE]",
  "segments": [
    {"speaker": "host_a", "text": "..."},
    {"speaker": "host_b", "text": "..."}
  ]
}
```

Rules for JSON conversion:
- Strip `**HOST 1:**` / `**HOST 2:**` prefixes → `"speaker": "host_a"` / `"host_b"`
- Strip `---` section breaks entirely — do not create empty segments
- Strip `## INTRO`, `## STORY N:`, `## CLOSING` headers — do not include as segments
- Keep SSML `<break time="300ms"/>` tags inside the text — ElevenLabs processes them
- One JSON object per speaker turn — do not merge adjacent Host 1 turns

Save as: `$PROJECT_DIR/YYYY-MM-DD/podcast_script_vN.json`

### Step 5c: Configure the notebook

Update `cell-config` in the notebook with these settings (replace voice IDs with your own from ElevenLabs):

```python
SCRIPT_JSON_PATH = "/path/to/your/PROJECT_DIR/YYYY-MM-DD/podcast_script_vN.json"

# Set your own ElevenLabs voice IDs — find them at elevenlabs.io/voice-library
VOICE_HOST_A = "YOUR_HOST_A_VOICE_ID"   # e.g. deep, authoritative voice
VOICE_HOST_B = "YOUR_HOST_B_VOICE_ID"   # e.g. natural, podcast-style voice

# Per-speaker models — turbo handles female intonation better
MODEL_HOST_A = "eleven_multilingual_v2"
MODEL_HOST_B = "eleven_turbo_v2_5"

OUTPUT_FORMAT = "mp3_44100_128"

# Host A custom settings — low stability = more dynamic/expressive
VOICE_SETTINGS_HOST_A = {
    "stability": 0.15,
    "similarity_boost": 0.75,
    "style": 0.65,
    "use_speaker_boost": True
}
VOICE_SETTINGS_HOST_B = None  # OOB defaults work best for most voices

PAUSE_BETWEEN_TURNS_MS = 0    # 0 = let ElevenLabs natural pacing handle turns; added silence feels mechanical

MAX_SEGMENTS = 6    # Test with first 6 segments before running full episode
                    # Set to None for full episode

OUTPUT_DIR = Path("/path/to/your/PROJECT_DIR/YYYY-MM-DD/audio_output_elevenlabs")
```

### Step 5d: Run and stitch

1. Run all cells top to bottom in order
2. Listen to `final_podcast.mp3` in the run folder
3. If segments sound good but final MP3 is broken, use the **RE-STITCH ONLY** cell at the bottom — it rebuilds the final file from existing segments without re-calling the API

**If only specific segments are bad:** delete just those segment `.mp3` files from the run folder, re-run only `cell-run` (it will re-generate missing ones), then re-stitch.

### Technical notes (learned from production)

**Zero-crossing artifacts (clicks/beeps at joins):**
Fixed with 15ms micro-fades at every segment boundary. The `merge_mp3_files()` function applies `fade_out(15)` to the end of each segment and `fade_in(15)` to the start of the next. Do not remove these.

**AudioSegment.empty() bug:**
Never initialize the combined audio with `AudioSegment.empty()` — it creates a 22050Hz mono file that corrupts the stitch when combined with 44100Hz stereo segments. Always start from `segments[0]`.

**Silence matching:**
When creating silence gaps between turns, match `frame_rate`, `channels`, and `sample_width` to the first real segment — not hardcoded values.

**previous_text / next_text context:**
Each TTS call passes the adjacent segments as `previous_text` and `next_text`. This gives ElevenLabs prosodic context, improving intonation at sentence boundaries.

**Per-speaker models:**
Host B (female) uses `eleven_turbo_v2_5` rather than `eleven_multilingual_v2`. The multilingual model flattens female intonation; turbo handles it better. Never set both hosts to the same model.

**Pause tuning:**
0ms — let ElevenLabs handle turn transitions naturally. Any added silence sounds mechanical because ElevenLabs already builds trailing breath/pacing into each segment ending. Only add explicit pause if the stitch sounds clipped (try 50ms maximum).

**SSML breaks in script:**
`<break time="300ms"/>` — dramatic reveal (one per story, the biggest fact)
`<break time="250ms"/>` — moderate pause (for a shift in topic within a turn)
These go inside Host 1's text, not as separate segments.

---

## Error Handling

| Situation | Action |
|-----------|--------|
| No AI emails found | Proceed with just web research (Phase 2+); note in summary |
| Web search agent fails | Retry once; if still fails, proceed without that agent's results and note gaps |
| Script fails (venv/pip issue) | Check that `~/.claude/email-venv` exists; if not, run `/email setup` |
| Project folder doesn't exist | Create it: `mkdir -p $PROJECT_DIR` |
| User wants to add a story not on the list | Accept it, ask for URL, add to script |
| User wants to re-run with different date range | Re-run `fetch_ai_emails.py` with `--hours N` |
| Final podcast MP3 is corrupted/cuts off early | Run RE-STITCH ONLY cell — do not regenerate TTS |
| Individual segment sounds bad | Delete that `.mp3`, re-run `cell-run`, then re-stitch |
| Host B sounds flat/robotic | Do not change settings — use OOB defaults; fix in script (longer turns, vary punctuation) |
| Clicking/beeping between segments | Check that `merge_mp3_files()` uses 15ms fades — do not remove them |

---

## Quick Reference

```bash
# Check venv
~/.claude/email-venv/bin/python --version

# Re-run email fetch (force refresh)
~/.claude/email-venv/bin/python ~/Code/02-ai-podcast-newsletter/.claude/skills/podcast-script/scripts/fetch_ai_emails.py \
  --hours 168 --account YOUR_ACCOUNT

# View today's story list
cat ~/.claude/ai_podcast_stories_$(date +%Y-%m-%d).md

# View project outputs
ls $PROJECT_DIR/
```
