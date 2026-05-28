# Podcast Email Newsletter Generator

Generates a complete newsletter HTML from a new podcast episode in the episodes/ folder.

## How to invoke
Run this skill from inside the ai-podcast repo directory after receiving the new episode email notification.
You can optionally pass headlines directly:

/podcast-email
/podcast-email headlines="headline 1, headline 2, headline 3"

---

## Step 1 — Pull latest from GitHub

Run `git pull` to fetch any newly uploaded episode files:

```bash
git pull
```

If the pull fails or there are conflicts, stop and let the user know before proceeding.

---

## Step 2 — Find and rename the episode file

Look in the `episodes/` folder for the most recently added audio file.

Extract the episode number and date from the filename. The team uploads files in this format:
`The AI News Podcast - Episode [N] - [Month DD YYYY].[ext]`

Rename the file to the standard convention:
`the-ai-news-podcast-episode-[N]-[YYYY-MM-DD].[ext]`

Example:
- Input: `The AI News Podcast - Episode 6 - May 08 2026.mp3`
- Output: `the-ai-news-podcast-episode-6-2026-05-08.mp3`

Present the rename to the user:
> "Found: `[original name]` → Renaming to: `[new name]`. Correct?"

Wait for confirmation before proceeding.

---

## Step 3 — Transcribe the audio

Run Whisper on the renamed file:
```bash
whisper "episodes/[renamed-file]" --output_format txt --output_dir /tmp
```

Read the transcript from the .txt output in /tmp.

If the user provided headlines directly, skip transcription and use those instead.

---

## Step 4 — Generate content

From the transcript (or provided headlines), generate:

**Summary** — 150 words or less, conversational and punchy, covering the main topic and key takeaways.

**Headlines** — between 3 and 6 depending on content. For each:
- **Title** — 5 to 8 words, clear and direct
- **Description** — 50 words or less, plain language
- **Image search term** — a short description for sourcing a relevant stock photo

---

## Step 5 — Human review checkpoint

Present the following to the user for approval:

---
**Episode:** [number] | **Date:** [date]

**Summary:**
[summary text]

**Headlines:**
1. [Title] — [Description] | Image: [search term]
2. [Title] — [Description] | Image: [search term]
...

---

Ask: "Does this look good? Any changes to the summary, headlines, or image directions before I source images and build the newsletter?"

**Do not proceed until the user explicitly approves.**

---

## Step 6 — Source and download images

The header logo image is evergreen and already hosted on Mailchimp — do NOT source or replace it. It is hardcoded in the template as:
`https://mcusercontent.com/af80ba3d9225959b5306dfe78/images/3810d858-c5c7-3510-bbba-b699a8a46280.jpg`

For the hero image and each headline, download a relevant photo from Unsplash:

```bash
curl -s --insecure -o "assets/ep[N]_[slug].jpg" \
  "https://images.unsplash.com/[photo-id]?w=600&q=80&fit=crop" \
  -A "Mozilla/5.0"
```

Name files using the convention: `ep[N]_[order]_[slug].jpg`
Example: `ep6_1_ai-funding.jpg`, `ep6_hero.jpg`

Show the user which images were downloaded and what they depict.

---

## Step 7 — Build the newsletter HTML

Read the template at `newsletters/podcast-email-template.html`.

Replace fixed placeholders:
- `{{EPISODE_NUMBER}}` → `PODCAST #[N]`
- `{{DATE}}` → formatted date (e.g. May 8, 2026)
- `{{SUMMARY}}` → the generated summary
- `{{EPISODE_URL}}` → leave as `#EPISODE_URL` for the user to fill in

For headlines, alternate between two block layouts:
- **Odd** (1st, 3rd, 5th): image LEFT, text RIGHT
- **Even** (2nd, 4th, 6th): text LEFT, image RIGHT (reverse class)

Use GitHub raw URLs for all images:
`https://raw.githubusercontent.com/ruthships/ai-podcast/main/assets/[filename]`

Save the completed newsletter as:
`newsletters/ai-podcast-episode-[N]-[YYYY-MM-DD].html`

---

## Step 8 — Push to GitHub

Stage and commit all new files:
```bash
git add assets/ep[N]_* newsletters/ai-podcast-episode-[N]-*.html episodes/[renamed-file]
git commit -m "Episode [N] — newsletter and assets [YYYY-MM-DD]"
git push
```

---

## Step 9 — Final confirmation

Tell the user:
- Newsletter file saved to `newsletters/`
- Images pushed to `assets/`
- Episode file renamed and pushed to `episodes/`
- Remind them to update `#EPISODE_URL` in the newsletter with the Google Drive link
- Raw newsletter URL on GitHub: `https://raw.githubusercontent.com/ruthships/ai-podcast/main/newsletters/[filename]`
