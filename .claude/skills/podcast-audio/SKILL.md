# Podcast Audio Generation — `/podcast-audio`

Generates the weekly AI podcast MP3 from a script JSON. Replaces the manual Jupyter notebook step at the end of the `/ai-podcast` workflow.

Calls ElevenLabs for TTS per speaker turn, then stitches MP3 segments with 15ms micro-fades to eliminate boundary clicks.

---

## Trigger

```
/podcast-audio                          # test run: first 6 segments on the latest episode folder
/podcast-audio full                     # full episode on the latest folder
/podcast-audio regen 16,23,25           # regenerate specific bad segments and re-stitch
/podcast-audio 2026-05-25 full          # explicit date + mode
/podcast-audio 2026-05-25 regen 4,5     # explicit date + regen
/podcast-audio 2026-05-25 full --episode 9   # set episode number used in the output filename
```

The skill auto-detects the most recent `2026-MM-DD/` folder in `~/Code/02-ai-podcast-newsletter/` unless a date is passed. The episode number in the output filename comes from `--episode`; if omitted it's auto-detected as (highest existing `episode-N` in `episodes/`) + 1.

---

## What the skill does

1. **Resolves the episode folder** — uses the date arg or picks the latest dated folder
2. **Loads the script JSON** — `podcast_script_YYYY-MM-DD.json` in that folder
3. **Estimates cost** — character count vs. ElevenLabs Creator (100K/mo) and Pro (500K/mo) quotas, shown before any API call
4. **Calls ElevenLabs TTS** per segment, streaming progress (`[14/42] host_b part1...`)
5. **Stitches the MP3 segments** with 15ms micro-fades at every join
6. **Writes the final MP3** to `audio_output_elevenlabs/<timestamp>_<title>_elevenlabs/The AI News Podcast - Episode <N> - <Month DD YYYY> - Voice Only.mp3` — episode `<N>` comes from `--episode` (else auto-detected as highest existing episode + 1), and the date is the human-readable form (e.g. `June 02 2026`). The ` - Voice Only` suffix marks it as the raw TTS stitch *before* the intro music is mixed in. This exact name is the contract with the rest of the pipeline: the `/autobrief-podcast` orchestrator detects Stage 2 completion by it, and `/podcast-postprocess` reads it as the raw input for the intro mix.

---

## Running the skill

Run the script via Bash, **using the bootstrapped venv interpreter** (`~/.claude/email-venv/bin/python`) so `elevenlabs`/`pydub`/`httpx` are guaranteed present. Do **not** use the system `python3` — it won't have the deps and the run will fail (this is what previously forced the manual notebook fallback).

```bash
~/.claude/email-venv/bin/python ~/Code/02-ai-podcast-newsletter/.claude/skills/podcast-audio/scripts/generate_audio.py <args>
```

Pass through whatever positional args the user typed after `/podcast-audio`. For example, `/podcast-audio full` → `~/.claude/email-venv/bin/python ~/Code/02-ai-podcast-newsletter/.claude/skills/podcast-audio/scripts/generate_audio.py full`.

If the user asks for a dry-run (cost estimate only, no API call), add `--dry-run`:

```bash
~/.claude/email-venv/bin/python ~/Code/02-ai-podcast-newsletter/.claude/skills/podcast-audio/scripts/generate_audio.py full --dry-run
```

The script streams progress to stdout. Let it run to completion — a full episode takes 2–4 minutes depending on segment count and ElevenLabs response time.

---

## First-time setup

Setup is handled by the AutoBrief bootstrap — run it once (it's idempotent):

```bash
bash ~/Code/02-ai-podcast-newsletter/.claude/skills/autobrief-podcast/scripts/bootstrap.sh
```

That creates the `~/.claude/email-venv` venv, installs `elevenlabs`/`pydub`/`httpx` (plus the rest of the pipeline's deps), checks for `ffmpeg`, and verifies the ElevenLabs API key is present.

**API key** is read from the project's `.env` (`~/Code/02-ai-podcast-newsletter/.env`, the `ELEVENLABS_API_KEY=...` line). Resolution order in the script:

1. `$ELEVENLABS_API_KEY` environment variable
2. `<project-dir>/.env` — the canonical source
3. `~/.podcast-audio.env` — legacy fallback

If the script reports a missing API key or missing dependency, re-run the bootstrap above; it pinpoints what's missing.

---

## Voice configuration

Voices are hard-coded in `scripts/generate_audio.py`:

- **Host A (lead):** Liam — `TX3LPaxmHKxFdv7VOQHJ` — `eleven_multilingual_v2`, custom voice settings (low stability for dynamic delivery)
- **Host B:** Cassidy — `56AoDkrOh6qfVPDXZ7Pt` — `eleven_turbo_v2_5`, OOB defaults

The team uses the same hosts across episodes for consistency. To change voices, edit the constants at the top of `generate_audio.py` — don't make them user-configurable unless there's a clear reason.

---

## Modes in detail

### `test` (default)
Generates the first 6 segments only. Lets the user listen to the opening of the episode and confirm the voices, pacing, and stitching sound right before spending API credits on the full run. Cost: roughly 5–10% of a Creator-tier monthly quota.

### `full`
Generates every segment in the script and stitches the final MP3. Cost: roughly 15–25% of a Creator-tier monthly quota for a typical 20–25 min episode.

### `regen N,M,O`
After listening to a full run, the user identifies bad segments by their 1-based number (visible in the run folder's MP3 filenames like `016_host_b_part1.mp3`). Pass those numbers to `regen` — the skill re-synthesizes only those segments and re-stitches the final MP3 from the existing files plus the freshly regenerated ones. Does NOT create a new run folder; it edits the most recent one.

---

## Workflow integration with /ai-podcast

`/ai-podcast` ends with the script + JSON + notebook in `~/Code/02-ai-podcast-newsletter/YYYY-MM-DD/`. From there, the user runs:

```
/podcast-audio              # test the first 6 segments
# listen — if voices sound right:
/podcast-audio full         # generate the full episode
# listen — if specific segments sound bad:
/podcast-audio regen 14,22  # fix just those
```

The Jupyter notebook in the episode folder is still produced by `/ai-podcast` as a fallback for users who prefer the interactive workflow. The skill is the automated path.

---

## Error handling

| Situation | Response |
|-----------|----------|
| No API key found | Ensure `ELEVENLABS_API_KEY=...` is in `~/Code/02-ai-podcast-newsletter/.env`; re-run `bash ~/Code/02-ai-podcast-newsletter/.claude/skills/autobrief-podcast/scripts/bootstrap.sh` to verify |
| Missing Python deps | Run the bootstrap, and invoke the script with `~/.claude/email-venv/bin/python` (not system `python3`) |
| No episode folder for given date | List available `2026-*/` folders |
| Multiple JSON files in folder | Ask user to disambiguate |
| regen with out-of-range numbers | Show valid range from the script |
| ElevenLabs API error (rate limit, quota) | Surface the error verbatim; user checks their account |
| Bad segment audio after full run | Suggest `regen N,M,O` with the segment numbers |

---

## File outputs

For each run, the script creates:

```
~/Code/02-ai-podcast-newsletter/YYYY-MM-DD/audio_output_elevenlabs/
  YYYYMMDD_HHMMSS_AI_Podcast_June_2_2026_elevenlabs/
    001_host_a_part1.mp3
    002_host_b_part1.mp3
    ...
    The AI News Podcast - Episode 9 - June 02 2026 - Voice Only.mp3   ← the stitched output (consumed by postprocess + orchestrator)
```

The numbered segment files are kept on purpose so `regen` can replace specific ones and re-stitch.

---

## Notes

- Segment numbers in `regen` are 1-based and match the segment numbers in the JSON script (the order the speakers appear). The filenames in the run folder also use this numbering.
- The 15ms fade is essential — do not remove it. Without it, every MP3 join produces an audible click at the PCM boundary.
- `PAUSE_BETWEEN_TURNS_MS = 0` is deliberate. ElevenLabs already builds natural breath/pacing into each segment ending; adding silence makes the result feel mechanical.
- `pydub` requires `ffmpeg` on the system. On macOS: `brew install ffmpeg` if not already present.
