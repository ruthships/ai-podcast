---
name: autobrief-podcast
description: "Orchestrates the full AI news podcast pipeline end-to-end: emails → script → audio → intro mix → newsletter → website. Walks through 5 stages with file-presence state detection, skipping anything already done. Pauses at editorial gates and pre-push confirmations. Trigger on /autobrief-podcast."
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Skill
  - Task
compatibility: "claude-code>=1.0"
---

# AutoBrief Podcast Orchestrator — `/autobrief-podcast`

Runs Ruth's full AI news podcast pipeline end-to-end. Chains five skills, detects which stages are already done by file presence, and resumes from the right point. Pauses for editorial decisions and pre-push confirmations.

## How to invoke

```
/autobrief-podcast                          # produce this week's episode end-to-end
/autobrief-podcast date=2026-06-02          # explicit episode date
/autobrief-podcast date=2026-06-02 episode=9
/autobrief-podcast from=postprocess         # explicit entry point — skip to stage N
/autobrief-podcast dry-run                  # show the plan, don't execute
```

The orchestrator works from anywhere — it `cd`s into the right repo for each stage.

---

## The pipeline

```
Stage 1: /podcast-script    → podcast_script_DATE.md + podcast_stories_DATE.md + DATE/podcast_script_DATE.json
Stage 2: /podcast-audio     → DATE/audio_output_elevenlabs/<run>/The AI News Podcast - Episode N - Month DD YYYY - Voice Only.mp3
Stage 3: /podcast-postprocess → episodes/The AI News Podcast - Episode N - Month DD YYYY.mp3 (with intro)
Stage 4: /podcast-email     → newsletters/ai-podcast-episode-N-DATE.html
Stage 5: /podcast-website   → updates Deployer dev branch
```

---

## State detection (file presence)

For a given `DATE` and `EPISODE`, the orchestrator checks these files:

| Stage | "Done if this file exists" |
|---|---|
| 1. script | `02-ai-podcast-newsletter/podcast_script_DATE.md` |
| 2. audio | `02-ai-podcast-newsletter/DATE/audio_output_elevenlabs/*/The AI News Podcast - Episode EPISODE - * - Voice Only.mp3` |
| 3. postprocess | `02-ai-podcast-newsletter/episodes/The AI News Podcast - Episode EPISODE - *.mp3` |
| 4. email | `02-ai-podcast-newsletter/newsletters/ai-podcast-episode-EPISODE-DATE.html` |
| 5. website | (no local file; rely on user confirmation or git log of website repo) |

A stage's output existing means we **skip** it. The user can override with `--force` to re-run a stage, or `from=stage` to start at a specific stage.

---

## Step 0 — Bootstrap environment (run first, every time)

Before resolving inputs or touching any stage, make sure the environment is ready. This is the one-time setup that previously had to be done by hand mid-run (creating the venv, `pip install`-ing packages). The bootstrap script is **idempotent** — fast and safe to run on every invocation.

```bash
bash ~/Code/00-autobrief-podcast/scripts/bootstrap.sh
```

It checks (and auto-fixes what's safe):

| Check | Auto-fixed? |
|---|---|
| `python3` on PATH | no — fatal if missing |
| venv at `~/.claude/email-venv` | **yes** — created if missing |
| packages: `anthropic elevenlabs httpx pydub python-dotenv requests` | **yes** — missing ones installed |
| `ffmpeg` + `ffprobe` (postprocess + image resize) | no — prints `brew install ffmpeg` |
| `~/.claude/email_config.json` (account + podcast_dir) | no — fatal if missing |
| `<podcast_dir>/.env` has `ELEVENLABS_API_KEY` + `ANTHROPIC_API_KEY` | no — fatal if missing |

**If bootstrap exits non-zero, stop and show the user the failing `✗` items** — these need manual attention (a missing API key or `ffmpeg`) and the pipeline will fail downstream without them. Only continue to Step 0.1 once bootstrap reports `environment ready.`

The canonical Python interpreter for every stage that runs Python (email fetch, TTS) is `~/.claude/email-venv/bin/python` — use it rather than the system `python3`.

---

## Step 0.1 — Resolve inputs

```bash
NEWSLETTER=~/Code/02-ai-podcast-newsletter
WEBSITE=~/Code/03-ai-podcast-website

# Date — default to today
DATE=${date:-$(date +%Y-%m-%d)}
# Human-readable date for the canonical filenames, e.g. 2026-06-02 -> "June 02 2026"
PRETTY_DATE=$(date -j -f "%Y-%m-%d" "$DATE" "+%B %d %Y")

# Episode — default to (last existing episode + 1). Matches both the legacy kebab
# names and the current title-case names in episodes/.
if [ -z "$episode" ]; then
  LAST=$(ls "$NEWSLETTER/episodes/"*.mp3 2>/dev/null \
         | grep -oiE 'episode[ -][0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1)
  EPISODE=$((LAST + 1))
else
  EPISODE="$episode"
fi
```

**Validate the date — two checks:**

1. **Format:** `DATE` must match `^[0-9]{4}-[0-9]{2}-[0-9]{2}$`. Stop if not.
2. **Sanity vs. reality** (catches the backwards/typo dates the format check can't — e.g. `2026-02-02` when the last episode was `2026-06-02`):

```bash
LAST_EP_DATE=$(ls "$NEWSLETTER/newsletters/"ai-podcast-episode-*-*.html 2>/dev/null \
  | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort | tail -1)
TODAY=$(date +%Y-%m-%d)

# (a) New episode should be dated AFTER the most recent one
if [ -n "$LAST_EP_DATE" ] && [[ ! "$DATE" > "$LAST_EP_DATE" ]]; then
  echo "⚠️  DATE ($DATE) is not after the most recent episode ($LAST_EP_DATE)."
fi
# (b) Guard against a far-future typo
if [[ "$DATE" > "$TODAY" ]]; then
  DELTA=$(( ($(date -j -f "%Y-%m-%d" "$DATE" "+%s") - $(date -j -f "%Y-%m-%d" "$TODAY" "+%s")) / 86400 ))
  [ "$DELTA" -gt 30 ] && echo "⚠️  DATE ($DATE) is $DELTA days in the future — possible typo."
fi
```

If either warning fires, **stop and confirm the intended date with the user** before running any stage. Only an explicit confirmation (or a corrected `date=`) proceeds. This is the gate that would have caught the `date=2026-02-02` mistake.

---

## Step 1 — Detect state and show the plan

Run all five file-presence checks and build a state report:

```
Pipeline state for episode ${EPISODE} on ${DATE}:

  [X] Stage 1: script         — ✓ podcast_script_${DATE}.md exists
  [X] Stage 2: audio          — ✓ voice-only mp3 exists in ${DATE}/audio_output_elevenlabs/
  [ ] Stage 3: postprocess    — episodes/The AI News Podcast - Episode ${EPISODE} - ${PRETTY_DATE}.mp3 missing
  [ ] Stage 4: email          — newsletter HTML missing
  [ ] Stage 5: website        — pending (no local detection)

Plan: skip stages 1-2; run stages 3-5.
```

**Show this report to the user and ask:**

> *"Plan looks good? Or do you want to override (re-run a stage, start from a different point, change date/episode)?"*

Wait for confirmation before proceeding. If the user says "looks good," continue. If they want a different entry point, accept and reset which stages run.

---

## Step 2 — Run Stage 1: `/podcast-script` (if needed)

If `podcast_script_${DATE}.md` does not exist (or `--force-script`):

1. Tell the user: *"Stage 1: generating script. Running /podcast-script — this pulls newsletters from Outlook (script), builds the email digest here in Cursor (no expiring API key), runs web research, synthesizes a story list, and waits for you to pick topics."*
2. Invoke `/podcast-script` (use the Skill tool or follow that skill's steps directly).
3. **Human gate:** Stage 1 contains its own story-pick checkpoint. Don't try to automate that.
4. After it returns, verify outputs exist:
   - `${NEWSLETTER}/podcast_script_${DATE}.md`
   - `${NEWSLETTER}/podcast_stories_${DATE}.md`
   - `${NEWSLETTER}/${DATE}/podcast_script_${DATE}.json`
5. Halt with a clear error if any output is missing.

Otherwise: log `"Stage 1 already done — skipping."`

---

## Step 3 — Run Stage 2: `/podcast-audio` (if needed)

If `${DATE}/audio_output_elevenlabs/*/The AI News Podcast - Episode ${EPISODE} - * - Voice Only.mp3` does not exist (or `--force-audio`):

1. Tell the user: *"Stage 2: generating audio. Running /podcast-audio in test mode first (first 6 segments) — listen and approve before the full run."*
2. Invoke the headless audio script (the `/podcast-audio` skill) — **always with the bootstrapped venv interpreter**, never the system `python3` and never the notebook:

   ```bash
   ~/.claude/email-venv/bin/python ~/.claude/skills/podcast-audio/scripts/generate_audio.py ${DATE} --episode ${EPISODE}
   ```

   (no mode arg = 6-segment test). Always pass `--episode ${EPISODE}` so the output filename matches the number postprocess/website will use. The script reads the ElevenLabs key from `${NEWSLETTER}/.env`.
3. **Human gate:** ask the user to listen to the test output and approve before running full.
   - On approval, run the full episode:

     ```bash
     ~/.claude/email-venv/bin/python ~/.claude/skills/podcast-audio/scripts/generate_audio.py ${DATE} full --episode ${EPISODE}
     ```
   - On rejection: ask what's wrong, optionally regenerate specific segments:

     ```bash
     ~/.claude/email-venv/bin/python ~/.claude/skills/podcast-audio/scripts/generate_audio.py ${DATE} regen N,M,O --episode ${EPISODE}
     ```
4. Verify `${NEWSLETTER}/${DATE}/audio_output_elevenlabs/*/The AI News Podcast - Episode ${EPISODE} - * - Voice Only.mp3` exists post-run (the script writes exactly this name).
5. Halt on failure.

Otherwise: log `"Stage 2 already done — skipping."`

---

## Step 4 — Run Stage 3: `/podcast-postprocess` (if needed)

If `${NEWSLETTER}/episodes/The AI News Podcast - Episode ${EPISODE} - ${PRETTY_DATE}.mp3` does not exist (or `--force-postprocess`):

1. Tell the user: *"Stage 3: applying the canonical intro mix to the raw audio."*
2. `cd "$NEWSLETTER"` and invoke `/podcast-postprocess date=${DATE} episode=${EPISODE}`.
3. The skill applies the duck-under intro mix to the raw voice-only mp3, writes the canonical `episodes/The AI News Podcast - Episode ${EPISODE} - ${PRETTY_DATE}.mp3`.
4. **Human gate:** confirm the new file before the skill commits and pushes.
5. Verify output file exists and is ~11s longer than the raw source.
6. Push to `ruthships/ai-podcast` after Ruth confirms.

Otherwise: log `"Stage 3 already done — skipping."`

---

## Step 5 — Run Stage 4: `/podcast-email` (if needed)

If `${NEWSLETTER}/newsletters/ai-podcast-episode-${EPISODE}-${DATE}.html` does not exist (or `--force-email`):

1. Tell the user: *"Stage 4: building newsletter HTML from script and stories markdown."*
2. `cd "$NEWSLETTER"` and invoke `/podcast-email date=${DATE} episode=${EPISODE}`.
3. The skill reads `podcast_script_${DATE}.md` + `podcast_stories_${DATE}.md` and generates summary, headlines, and source URLs (no Whisper).
4. **Human gate:** the skill presents the summary + headlines for approval before sourcing images and building the HTML.
5. After approval, the skill sources images, builds HTML, commits, and pushes (with confirmation).
6. As its final step the skill creates the Mailchimp **template + campaign draft** (`scripts/mailchimp_draft.py`, status `save` — never auto-sent). This runs after the GitHub push so the campaign preview's `raw.githubusercontent.com` images resolve.

Otherwise: log `"Stage 4 already done — skipping."`

---

## Step 6 — Run Stage 5: `/podcast-website`

(Always run — no local file detection. The user can pass `--skip-website` to bypass.)

1. Tell the user: *"Stage 5: updating the Deployer site."*
2. `cd "$WEBSITE"` and invoke `/podcast-website episode=${EPISODE}`.
3. The skill pulls both repos, syncs the new audio + newsletter HTML into the website repo, regenerates episode pages via `generate_episodes.py`, and commits.
4. **Human gate:** confirm before pushing to McK-Private/ai-podcast-website `dev` branch (shared remote).

---

## Step 7 — Final report

```
✓ AutoBrief Episode ${EPISODE} (${DATE}) shipped:

  Newsletter HTML:  https://raw.githubusercontent.com/ruthships/ai-podcast/main/newsletters/ai-podcast-episode-${EPISODE}-${DATE}.html
  Audio (canonical): episodes/The AI News Podcast - Episode ${EPISODE} - ${PRETTY_DATE}.mp3 on main
  Website:          https://ai-podcast-website.dev.deployer.mckinsey.com/episode-${EPISODE}.html

Manual follow-ups:
  - Upload mp3 to Google Drive, replace #EPISODE_URL in newsletter HTML, re-push (then re-run the Mailchimp draft step)
  - Review the Mailchimp campaign draft and click Send when ready (it's left unsent)
  - (Optional) merge dev → stg → prod on website when ready
```

---

## Args reference

| Arg | Default | Meaning |
|---|---|---|
| `date=YYYY-MM-DD` | today | Episode date — used in filenames and dated working dir |
| `episode=N` | last + 1 | Episode number |
| `from=stage` | (auto from file-presence) | Force entry at `script`, `audio`, `postprocess`, `email`, or `website` |
| `dry-run` | false | Show the plan + state report, don't execute any stage |
| `--force-script` | false | Re-run stage 1 even if output exists |
| `--force-audio` | false | Re-run stage 2 |
| `--force-postprocess` | false | Re-run stage 3 |
| `--force-email` | false | Re-run stage 4 |
| `--skip-website` | false | Don't run stage 5 (when iterating on script/audio/newsletter only) |

---

## Design notes (for future-me)

**File-presence over manifest** — the current state tracking is just "does this output file exist?" Cheap, no extra state to maintain, sufficient for a 5-stage linear pipeline. If we ever want richer state (editorial decisions remembered across sessions, resume-from-failed-segment, multi-user collaboration), upgrade to a per-episode `manifest.json` in an `episodes-in-progress/ep${EPISODE}/` folder.

**Human gates over full automation** — every stage with editorial judgment (story-pick, audio quality, newsletter review) pauses for the user. The orchestrator is dynamic in the workflow sense (skip what's done, branch on decisions) but not in the "no human in the loop" sense. That's intentional — the editorial output is too important to fully automate.

**Why this orchestrator doesn't own its sub-skills** — each sub-skill (`/podcast-script`, `/podcast-audio`, `/podcast-postprocess`, `/podcast-email`, `/podcast-website`) is standalone and invokable on its own. This orchestrator chains them. If you need to debug a single stage, run that skill directly — don't rely on the orchestrator for state.

**Why episode N auto-detects from last + 1** — file-presence detection assumes one canonical naming scheme. If you skip a number (e.g. ep10 already exists from a prior week) the auto-increment breaks. Pass `episode=N` explicitly if you ever need to back-fill.

**Stage 5 has no local detection** — the website repo's dev branch could have been updated by anyone (you, Cursor, a teammate). Don't try to infer from git state — just always offer to run it (with confirmation) and skip if the user says it's done.
