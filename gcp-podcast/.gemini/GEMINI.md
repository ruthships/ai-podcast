# AI News Podcast — shared context (GEMINI.md)

This file is the equivalent of Claude's CLAUDE.md. The Gemini CLI loads it automatically
for every command in this project, so the rules below don't have to be repeated in each
command file.

## What we make

A weekly ~20-30 minute AI-news podcast for **senior executives** (C-suite, board, MDs),
plus a matching email newsletter. Two hosts. Plain, factual, no hype.

## Audience & voice

- Write for busy non-technical executives. Brief any company/concept on first mention
  (e.g. "Anthropic — the AI safety company behind Claude").
- Factual only. Report what happened, explain the tech, connect events.
  **Never** give recommendations ("executives should…", "your next step is…").
- No filler, no marketing language.

## File & naming conventions

- Episode date format in filenames: `YYYY-MM-DD`. Human-readable: `Month DD YYYY`.
- Per-episode files:
  - `podcast_stories_YYYY-MM-DD.md` — ranked story list with sources
  - `podcast_script_YYYY-MM-DD.md` — final fact-checked two-host script
  - `newsletter_episode-N-YYYY-MM-DD.html` — newsletter
- Episode number = last episode + 1 unless told otherwise.

## Story ranking tiers (used by research + synthesis)

- **Tier 1 — Must-Cover:** major model releases, significant business deals, regulatory
  moves with real impact, major AI-company news.
- **Tier 2 — Strong Interest:** new products, enterprise adoption, meaningful research,
  policy developments.
- **Tier 3 — Worth Knowing:** technical deep-dives, niche research, minor updates.

Always include at least one **primary-source** URL per story (prefer the company/agency
over aggregators) with the publication date.

## Human gates (never skip)

1. After research → the human **picks** which stories to cover.
2. After script → the human **reads and approves** before audio.
3. After newsletter draft → the human **approves** before publishing.

Automate the work, not the editorial judgment.
