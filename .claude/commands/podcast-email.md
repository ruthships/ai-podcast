# Podcast Email Newsletter Generator

Generates a complete HTML newsletter for a podcast episode by reading directly from the structured script and stories markdown files. No transcription step — the script already contains the final chosen story titles, host narrative, and the stories file already has the source URLs.

## How to invoke

Run this skill from inside the **newsletter repo** (`~/Code/02-ai-podcast-newsletter`) once `/podcast-postprocess` has produced the canonical episode audio:

```
/podcast-email
/podcast-email date=2026-06-02
/podcast-email date=2026-06-02 episode=9
```

Defaults:
- `date` — newest `podcast_script_YYYY-MM-DD.md` at repo root (or the user-supplied date)
- `episode` — extracted from the audio filename in `episodes/the-ai-news-podcast-episode-N-DATE.mp3`

---

## Step 1 — Pull latest from GitHub

```bash
git pull
```

If the pull fails or there are conflicts, stop and let the user know.

---

## Step 2 — Verify the canonical episode audio exists

`/podcast-postprocess` is the prerequisite — it produces the final audio file in `episodes/` with the canonical slug name and the intro music already mixed in.

```bash
EPISODE=${episode:-$(ls episodes/the-ai-news-podcast-episode-*.mp3 \
  | sed -E 's/.*episode-([0-9]+)-.*/\1/' | sort -n | tail -1)}
DATE=${date:-$(ls -t podcast_script_*.md | head -1 | sed -E 's/podcast_script_(.+)\.md/\1/')}
AUDIO="episodes/the-ai-news-podcast-episode-${EPISODE}-${DATE}.mp3"

test -f "$AUDIO" || { echo "Audio not found: $AUDIO — run /podcast-postprocess first"; exit 1; }
```

**Do not run `whisper` on the audio.** All content for the newsletter comes from the script — the audio is just for the Listen button URL once you upload it to Drive.

---

## Step 3 — Read the script and stories files

The two structured inputs:

```bash
SCRIPT="podcast_script_${DATE}.md"
STORIES="podcast_stories_${DATE}.md"
```

The script (`podcast_script_*.md`) has the **final narrative** with the chosen stories in episode order. Structure:

```
# AI Weekly Podcast — YYYY-MM-DD
_Topics: title1; title2; title3; ..._
_Runtime estimate: ~N minutes_

## INTRO
**HOST 1:** [framing of the week's overall theme]
**HOST 2:** [reaction]
**HOST 1:** Let's get into it.

## STORY 1: [Title used as headline]
**HOST 1:** [opening sentences — use as the headline description]
**HOST 2:** [...]
**HOST 1:** [...]

[repeat for STORY 2..N]

## CLOSING
**HOST 1:** [one-line synthesis]
**HOST 2:** [closer]

_Sources:_
- Bloomberg: https://...
- ...
```

The stories file (`podcast_stories_*.md`) has the **full candidate list** with rich per-story source URLs as markdown links — use this to match each chosen story to its primary source URL.

---

## Step 4 — Extract newsletter content from the script

For each piece of the newsletter:

### Episode metadata
- **Episode number**: from `$EPISODE` (resolved in Step 2)
- **Date**: from the `# AI Weekly Podcast — YYYY-MM-DD` line; format for display as `Month DD, YYYY` (e.g. `June 2, 2026`)

### Overall summary (≤150 words, conversational, punchy)

Synthesize from the script's `## INTRO` and `## CLOSING` sections. The intro frames the week's theme; the closing has the synthesis. Combine into ~120 words.

**Don't** copy host dialogue verbatim — paraphrase into editorial newsletter voice. Drop the SSML `<break>` tags and host markers.

### Headlines (one per `## STORY N` section)

Each `## STORY N: <Title>` becomes one headline. Extract:

- **Title** — the text after `## STORY N: ` (already 5-8 words, written for the script). Use as-is unless it's awkward in newsletter context.
- **Description** — paraphrase the **first HOST 1 paragraph** of that story (the opening factual statement). Target 30-50 words. Strip `<break>` tags and any host attribution.
- **Source URL** — match this story's title or topic to a story in `podcast_stories_*.md` and use its primary (first) source URL. The stories file has them as `[Outlet](URL)` markdown links per story.
- **Image search term** — a short 3-6 word descriptor for sourcing a stock photo (e.g. "data center server racks", "humanoid robot in factory", "stock market trading floor"). Avoid logos, faces, brand names.

Aim for 3-6 headlines — match the script's story count (usually 5-6).

---

## Step 5 — Human review checkpoint

Present to the user:

```
---
Episode: [N] | Date: [Month DD, YYYY]

Summary:
[summary text]

Headlines:
1. [Title] — [Description]
   Source: [URL]
   Image: [search term]
2. ...
---
```

Ask: *"Does this look good? Any changes to the summary, headlines, sources, or image directions before I source images and build the newsletter?"*

**Do not proceed until the user explicitly approves.**

---

## Step 6 — Source and download images

The header logo image is evergreen and already hosted on Mailchimp — **do NOT replace it**. It's hardcoded in the template as:
`https://mcusercontent.com/af80ba3d9225959b5306dfe78/images/3810d858-c5c7-3510-bbba-b699a8a46280.jpg`

For the **hero image** and each **headline image**, use the Openverse fetcher (free, key-less, CC-licensed — replaces the old Unsplash flow which needed an API key we don't have). It downloads and crops to the 600x400 newsletter convention.

First **list** candidates so you (and the user) can pick a good one:

```bash
python3 scripts/fetch_image.py --query "stock market trading floor" --list
```

Then download the chosen candidate (use `--index N` to pick a non-default one):

```bash
python3 scripts/fetch_image.py --query "stock market trading floor" \
  --out "assets/ep${EPISODE}_1_anthropic-ipo.jpg" --index 0
```

Naming convention:
- Hero: `assets/ep${EPISODE}_hero.jpg`
- Headlines: `assets/ep${EPISODE}_[order]_[slug].jpg` (e.g. `ep9_1_anthropic-ipo.jpg`)

Cross-check the hero against past `ep*_hero.jpg` files — don't repeat the same thematic stock photo (e.g. don't pick another robot-themed hero if a recent episode already used one). Show the user which images were downloaded and what they depict.

> **Push-first rule (important):** all images are referenced via `raw.githubusercontent.com/.../main/assets/...`. Nothing renders — not the newsletter preview, not the website, not the Mailchimp campaign — until the image is committed and pushed to `main`. So `git add` + push the new `assets/ep${EPISODE}_*` files (Step 8) **before** expecting any preview to show them. This is the #1 cause of "all the photos are broken."

---

## Step 7 — Build the newsletter HTML

Read the template at `newsletters/podcast-email-template.html`.

Replace fixed placeholders:
- `{{EPISODE_NUMBER}}` → `PODCAST #[N]`
- `{{DATE}}` → formatted date (e.g. `June 2, 2026`)
- `{{SUMMARY}}` → the generated summary
- `{{EPISODE_URL}}` → leave as `#EPISODE_URL` for the user to fill in after Drive upload

**Write the editorial theme as an explicit marker** near the top of the HTML (just after the opening `<body>` or `<html>` tag) so the website generator uses it as the episode page heading — decoupled from the hero image's `alt` text:

```html
<!-- EPISODE_THEME: AI's valuations race ahead of the payoff -->
```

This is the approved editorial theme (the same line you use for the hero `alt` and the Mailchimp subject). Keeping it as a dedicated marker means the hero image's `alt` can be a literal accessibility description without it leaking into the website's episode title (this is what caused the ep9 "financial district skyline" heading). `/podcast-website`'s `generate_episodes.py` reads this marker first, falling back to the hero `alt` only for older newsletters that predate it.

For headlines, alternate between two block layouts:
- **Odd** (1st, 3rd, 5th): image LEFT, text RIGHT
- **Even** (2nd, 4th, 6th): text LEFT, image RIGHT (reverse class)

Use GitHub raw URLs for all images:
```
https://raw.githubusercontent.com/ruthships/ai-podcast/main/assets/[filename]
```

(The GitHub repo name remains `ai-podcast` — the local folder was renamed to `02-ai-podcast-newsletter` but the remote is unchanged.)

Save the completed newsletter as:
`newsletters/ai-podcast-episode-[N]-[YYYY-MM-DD].html`

---

## Step 8 — Push to GitHub

**Pre-push gate: check the Listen link.** The newsletter ships with a `#EPISODE_URL` placeholder until the mp3 is on Google Drive. Detect it so it never goes out unnoticed:

```bash
NL="newsletters/ai-podcast-episode-${EPISODE}-${DATE}.html"
if grep -q "#EPISODE_URL" "$NL"; then
  echo "⚠️  $NL still has the #EPISODE_URL placeholder — the Listen button won't work."
fi
```

If the placeholder is present, tell the user explicitly and ask whether to:
- **(a)** upload the mp3 to Google Drive now, replace `#EPISODE_URL` with the share link, then push (preferred — ships a working Listen button), or
- **(b)** push with the placeholder on purpose (e.g. audio not ready yet) and fix it on a later re-push.

Don't push past the placeholder silently.

Stage only what this skill produced — don't `git add -A`:

```bash
git add "assets/ep${EPISODE}_"* \
        "newsletters/ai-podcast-episode-${EPISODE}-${DATE}.html"
git commit -m "Episode ${EPISODE} — newsletter and assets ${DATE}"
```

**Confirm with the user before pushing.** Once approved:

```bash
git push
```

---

## Step 9 — Push the draft to Mailchimp

Create the reusable per-episode **template** and a send-ready **campaign draft** from the finished HTML. This runs only **after** Step 8's push, because the newsletter references images via `raw.githubusercontent.com` URLs — if those aren't on `main` yet, the Mailchimp preview shows broken images (same push-first rule as the website).

> Ideally replace `#EPISODE_URL` (the Listen button) with the real Drive link before this step so the draft's Listen button works. If it's not ready, you can still create the draft and fix the link in Mailchimp's editor before sending.

```bash
# Draft only (safe — nothing is sent to the 5-member audience):
python3 scripts/mailchimp_draft.py --episode ${EPISODE}

# Draft + a test email to yourself, to see it land:
python3 scripts/mailchimp_draft.py --episode ${EPISODE} --test-email ruth_tupe@mckinsey.com
```

What it does (stdlib only, reads `MAILCHIMP_API_KEY` + `MAILCHIMP_AUDIENCE_ID` from `.env`):
- Creates/refreshes a template named by date (e.g. `June 02 2026`) — matches Ruth's existing template set
- Creates a campaign draft `AI Podcast Episode ${EPISODE}` (subject = hero image alt text; from "Ruth Tupe" / reply-to `ruth_tupe@mckinsey.com`) referencing that template
- Leaves it at status `save` and prints the Mailchimp edit URL

**It never sends to the audience.** The only outbound path is `--test-email` (to addresses you name). Ruth reviews the draft and clicks **Send** in the UI. Re-running the same episode refreshes the template and reuses the draft (no duplicates).

---

## Step 10 — Final confirmation + handoff

Tell the user:
- Newsletter HTML saved to `newsletters/ai-podcast-episode-${EPISODE}-${DATE}.html`
- Images committed to `assets/`
- Raw newsletter URL (once pushed):
  `https://raw.githubusercontent.com/ruthships/ai-podcast/main/newsletters/ai-podcast-episode-${EPISODE}-${DATE}.html`
- Mailchimp campaign draft created (status `save`) — review and Send in the UI
- **Manual step**: upload the canonical mp3 to Google Drive, get the share link, replace `#EPISODE_URL` in the newsletter HTML, re-push (and re-run Step 9 to refresh the draft)
- **Next pipeline step**: run `/podcast-website` (from the website repo) to update the Deployer site

---

## Appendix — What changed from the Whisper era

The old skill ran `whisper` on the audio and tried to extract headlines from the transcript. That had problems:

- Whisper transcripts lose all structure — there was no clean way to split "the host's intro" from "story 1" without re-segmenting
- Source URLs were never available (no way to look them up from a transcript)
- Story titles got re-paraphrased into something different from what the host actually said
- The transcription step alone took 2-3 minutes per episode

Reading the script directly gives us:
- **Pre-segmented stories** (`## STORY N:` headers — already labeled)
- **Pre-written headline titles** (the ## headers themselves are written for the script's structure and read well as newsletter headlines)
- **Sources as proper markdown links** (in the stories file)
- **Zero transcription cost** — pure text parsing

If you ever need the transcript for some other purpose (search, accessibility, etc.), generate it separately — but don't make the newsletter depend on it.
