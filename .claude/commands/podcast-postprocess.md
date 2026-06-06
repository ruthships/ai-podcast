# Podcast Postprocess

Applies the canonical 15s intro music to a raw TTS-generated podcast episode and writes the final, shippable audio file to `episodes/` in the newsletter repo. This is the canonical step between "ElevenLabs notebook finished generating audio" and "newsletter / website / Drive can use it."

The newsletter repo is the **single source of truth** for episode audio. Both the website repo and any newsletter Listen links should pull from here. Skip this step and the website drifts (see the May 2026 ep8 drift incident).

## How to invoke

Run from inside the **newsletter repo** (`~/Code/02-ai-podcast-newsletter`) after `/podcast-audio` has produced the raw voice-only stitch (`The AI News Podcast - Episode <N> - <Month DD YYYY> - Voice Only.mp3`) in the dated working folder:

```
/podcast-postprocess
/podcast-postprocess date=2026-06-01
/podcast-postprocess date=2026-06-01 episode=9
/podcast-postprocess source="2026-06-01/audio_output_elevenlabs/20260601_140532_AI_Podcast.../The AI News Podcast - Episode 9 - June 01 2026 - Voice Only.mp3"
/podcast-postprocess --force
```

Defaults:
- `date` — newest dated folder under `./2026-*/` (or the user-supplied `YYYY-MM-DD`)
- `source` — the only `* - Voice Only.mp3` inside `<date>/audio_output_elevenlabs/<timestamp>_*/`; error if zero or multiple
- `episode` — `(highest existing episode in episodes/) + 1`
- Idempotent: refuse to overwrite an existing `episodes/The AI News Podcast - Episode N - Month DD YYYY.mp3` unless `--force`

---

## Step 1 — Resolve inputs

Locate the four things this skill needs:

```bash
NEWSLETTER_REPO=~/Code/02-ai-podcast-newsletter
INTRO=$NEWSLETTER_REPO/assets/ai-podcast-intro.mp3

# Date — default to newest dated folder
DATE=${date:-$(ls -1d $NEWSLETTER_REPO/2026-* 2>/dev/null | sort | tail -1 | xargs basename)}

# Human-readable date used in the canonical filename, e.g. 2026-06-02 -> "June 02 2026"
PRETTY_DATE=$(date -j -f "%Y-%m-%d" "$DATE" "+%B %d %Y")

# Source — auto-discover the raw "voice only" stitch unless given
if [ -z "$source" ]; then
  SOURCE=$(ls -1 "$NEWSLETTER_REPO/$DATE/audio_output_elevenlabs/"*/*" - Voice Only.mp3" 2>/dev/null | head -1)
else
  SOURCE="$NEWSLETTER_REPO/$source"
fi

# Episode — auto-detect next sequential number (matches both legacy kebab and
# current title-case filenames in episodes/)
if [ -z "$episode" ]; then
  LAST=$(ls "$NEWSLETTER_REPO/episodes/"*.mp3 2>/dev/null \
         | grep -oiE 'episode[ -][0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1)
  EPISODE=$((LAST + 1))
else
  EPISODE="$episode"
fi

# Canonical published (with-intro) file — title-case long form the website generator expects.
DST="$NEWSLETTER_REPO/episodes/The AI News Podcast - Episode ${EPISODE} - ${PRETTY_DATE}.mp3"
```

**Sanity-check before doing anything destructive:**
- `INTRO` must exist (`assets/ai-podcast-intro.mp3`, 15s, ~236 KB)
- `SOURCE` must exist and be > 1 MB
- `DST` must not already exist (unless `--force` was passed)
- `DATE` must match `^2026-\d{2}-\d{2}$` (or the current year)

Show the user the resolved values and confirm before running ffmpeg.

---

## Step 2 — Apply the duck-under intro mix

The canonical recipe. **Do not modify the parameters without testing** — this curve was tuned iteratively in May 2026 and ear-tested on ep7/ep8.

```bash
ffmpeg -y -loglevel error \
  -i "$INTRO" \
  -i "$SOURCE" \
  -filter_complex "[1:a]adelay=11000[voice];[0:a][voice]amix=inputs=2:duration=longest:normalize=0[out]" \
  -map "[out]" -ac 1 -ar 44100 -b:a 128k \
  "$DST"
```

What this does:
- **`adelay=11000`** — voice starts 11 seconds into the mix
- **`amix=...:normalize=0`** — overlays intro music + delayed voice without auto-gain (prevents mid-mix volume change)
- The intro file already has the duck-down volume curve baked into it (see Appendix B), so the music is silent by 12.5s and voice carries cleanly
- Output: mp3, 44.1kHz, mono, 128kbps — matches the rest of the published episodes

---

## Step 3 — Verify

```bash
SRC_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SOURCE")
OUT_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DST")
DELTA=$(awk "BEGIN{printf \"%.2f\", $OUT_DUR - $SRC_DUR}")

# Verify the intro signature: RMS@0-2s should be near digital silence
# (the fade-in starts at 0 volume)
RMS=$(ffprobe -v error -f lavfi -i "amovie='$DST',astats=metadata=1:reset=1:length=2" \
      -show_entries frame_tags=lavfi.astats.Overall.RMS_level -of csv=p=0 2>/dev/null | head -1)

echo "  source: $SRC_DUR s"
echo "  output: $OUT_DUR s  (Δ = ${DELTA}s, expected +11.00s)"
echo "  RMS@0-2s: $RMS dB  (expected < -200dB if intro is properly mixed)"
```

**Halt and report to the user if:**
- `DELTA` is not within 11.00 ± 0.05 seconds — something is off with the adelay
- `RMS@0-2s` is greater than -50 dB — the intro music isn't where it should be (could be missing the intro file, wrong filter syntax, or input swap)

---

## Step 4 — Commit (and optionally push)

Stage only the new episode file. Don't `git add -A` — it would scoop up `.DS_Store`, scratch notebooks, etc.

```bash
cd $NEWSLETTER_REPO
git add "$DST"
git status -s
```

Default commit message:

```
Episode N — audio drop for [Month] [DD], [YYYY]

Generated via ElevenLabs, post-processed with the canonical duck-under
intro mix (15s music head, voice enters at 11s). Source raw TTS output
preserved locally under 2026-MM-DD/audio_output_elevenlabs/.
```

**Always confirm with the user before pushing.** Per Ruth's git workflow, push happens only after she reviews. Once approved:

```bash
git push
```

Once pushed, the audio is canonical and will be picked up by:
- `/podcast-email` — for transcription + newsletter HTML generation
- `/podcast-website` — for sync to the Deployer static site

---

## Step 5 — Hand off to next stage

Tell the user what happens next so the chain stays visible:

> Next steps:
> 1. Run `/podcast-email` (from the newsletter repo) to generate the HTML newsletter
> 2. After the newsletter is on GitHub, run `/podcast-website` (from the website repo) to update the Deployer site
> 3. (Optional) Upload the new mp3 to Google Drive and update the Listen button URL in the newsletter HTML

Future: `/autobrief-podcast` orchestrator will chain all three.

---

## Appendix A — Argument cheat sheet

| Arg | Default | Meaning |
|---|---|---|
| `date=YYYY-MM-DD` | newest dated folder | Episode date (used in filename + dated working dir lookup) |
| `episode=N` | last + 1 | Episode number |
| `source=path` | auto-discover `* - Voice Only.mp3` | Raw TTS (voice only) output path (relative to repo or absolute) |
| `--force` | refuse to overwrite | Replace existing `episodes/...episode-N-DATE.mp3` |

---

## Appendix B — Regenerating `assets/ai-podcast-intro.mp3`

The canonical intro is a **pre-faded 15s clip** derived from `assets/Hip-Hop Funky Beat.mp3`. The duck-down curve is baked in so the mix step doesn't have to apply it every run. **Only re-run this if you change the source music or want to retune the curve.**

The volume envelope (piecewise-linear, tuned by ear in May 2026):

| Time | Volume |
|---|---|
| 0 → 0.5s | fade in 0% → 100% |
| 0.5 → 9.5s | hold at 100% |
| 9.5 → 10.5s | 100% → 60% |
| 10.5 → 11.0s | 60% → 45% (voice enters here) |
| 11.0 → 11.5s | 45% → 30% |
| 11.5 → 12.0s | 30% → 8% |
| 12.0 → 12.5s | 8% → 0% |
| 12.5 → 15s | 0% (silent — voice carries) |

The ffmpeg `volume` filter expression that implements this:

```bash
ffmpeg -y -i "assets/Hip-Hop Funky Beat.mp3" -t 15 \
  -af "volume='if(lt(t,0.5),t/0.5,if(lt(t,9.5),1.0,if(lt(t,10.5),0.90-0.30*(t-9.5),if(lt(t,11.0),0.60-0.30*(t-10.5),if(lt(t,11.5),0.45-0.30*(t-11.0),if(lt(t,12.0),0.30-0.44*(t-11.5),if(lt(t,12.5),0.08-0.16*(t-12.0),0)))))))':eval=frame" \
  -ac 1 -ar 44100 -b:a 128k assets/ai-podcast-intro.mp3
```

After regeneration, commit the new `assets/ai-podcast-intro.mp3` to git so all future `/podcast-postprocess` runs use the updated curve.

---

## Appendix C — Production notes (learned the hard way)

- **`normalize=0` is required.** Without it, ffmpeg auto-gains the mix and produces an audible volume bump at the intro→voice transition. We want the intro to fade down because the intro file says so, not because the mixer compensates.
- **`-ac 1 -ar 44100 -b:a 128k` matches the rest of the published catalog.** Don't switch to stereo or higher bitrate without converting every prior episode — listeners will hear the dynamic-range jump between episodes.
- **Voice entry at exactly 11s.** The intro file is 15s and ducks to silence by 12.5s. Voice entering before 11s would clash with the loud music section. Voice entering after 12.5s would leave audible silence between intro and voice. 11s is the goldilocks zone.
- **Don't apply this to ep1.** Ep1 has its own different intro (louder peak music at 6-14s). Running this skill against ep1 would double-intro it. The skill auto-increments from the last episode so this shouldn't happen in normal flow — but if you're using `--force` or manually overriding `episode=1`, stop.
