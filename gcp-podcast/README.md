# AutoBrief for Google — a teaching kit

This folder rebuilds Ruth's AI-news podcast pipeline in **Google's world** for people
who **don't have Claude**. It's written for **non-technical** learners who have access to
**Gemini Enterprise**, **Google AI Studio**, and the **Google / Gemini CLI**.

The big idea you're teaching:

> A "skill" is not magic. It's just **instructions + tools + an agent that follows them**.
> Swap the agent (Claude → Gemini) and a couple of tools (Outlook → Google Search,
> ElevenLabs → NotebookLM) and the same pipeline runs.

---

## 👉 Teaching a beginner? Start with [`WORKSHOP.md`](WORKSHOP.md)

**[`WORKSHOP.md`](WORKSHOP.md)** is the hand-holding, click-by-click guide that assumes the
participant has never used AI tools and cannot code. It walks them through **building each
of the 4 assistants (Gems) step by step**, testing each one, then running a full episode.
Hand them that file.

This README (below) is the **instructor's overview** — the architecture, the Google product
choices, and the optional power-user CLI track.

---

## Two ways to do everything here

Every step exists in **two forms** so you can teach the right altitude for your audience:

| Form | Where it lives | Who it's for |
|---|---|---|
| **Gem** (no code) | `gems/*.md` — paste the text into a new Gem in Gemini Enterprise | Anyone. The simplest possible "skill". |
| **CLI command** (light) | `.gemini/commands/**/*.toml` — becomes a `/podcast:…` slash command | People comfortable in a terminal who want the "type one command, it runs" feel. |

Start everyone on **Gems**. Graduate the curious to the **CLI**.

---

## The pipeline (research-first — no inbox scanning)

```
1. /podcast:research    Google Search grounding → ranked story list   (replaces Outlook scan)
2.    (you pick)        human chooses the stories                     (editorial gate)
3. /podcast:script      style rules → two-host script
4. /podcast:factcheck   verify every claim against its source
5. /podcast:audio       guides you through NotebookLM → two-host mp3
6. /podcast:newsletter  → newsletter HTML / Google Doc
7. /podcast:publish     → Google Sites
```

`/autobrief` is an orchestrator that walks through all of them in order, pausing for your
decisions — same spirit as the Claude `/autobrief-podcast`.

---

## Setup (CLI version) — 3 minutes

1. Install the Gemini CLI and sign in with the **Gemini Enterprise** account.
   > ⚠️ On the free / Google One tier the Gemini CLI is being replaced by **Antigravity CLI**.
   > Gemini Enterprise users are unaffected — confirm the tier before teaching this part.
2. Copy this kit's `.gemini/` folder into the project you'll work in (or into `~/.gemini/`
   to make the commands global):
   ```
   cp -r gcp-autobrief-kit/.gemini ~/.gemini
   ```
3. Start the CLI in that folder and run `/commands reload`, then `/help` — you should see
   the `/podcast:*` commands and `/autobrief`.
4. `GEMINI.md` (the shared rules + naming conventions) loads automatically. Check it with
   `/memory show`.

## Setup (Gem version) — even simpler

1. Open Gemini Enterprise → **Gems** → **New Gem**.
2. Name it (e.g. "Podcast Research"), paste the matching file from `gems/` into the
   instructions box, save.
3. Repeat for each `gems/*.md` file. Now each step is a named assistant you just chat with.

---

## What changed from the Claude version, and why

| Claude version | Google version | Why |
|---|---|---|
| Scan Outlook inbox (Mac AppleScript) | **Google Search grounding** | No Mac/Outlook dependency; real-time web + citations built in. Research becomes step 1. |
| Parallel Task sub-agents | One grounded Gem run per area (or ADK if they grow) | Keeps it no-code. |
| ElevenLabs notebook | **NotebookLM Audio Overview** (two-host audio, no code) | Native conversational podcast from your script. Use Cloud Text-to-Speech only if you need per-voice control. |
| git repo + website push | **Google Sites / Drive** | No git for non-technical users. |
| `.env` / `email_config.json` | Gem settings, or **Secret Manager** if coding | No local secrets to manage. |

When a team outgrows Gems + CLI, the production-grade equivalent is **ADK (Agent
Development Kit)** deployed on **Agent Engine** — that's the real twin of what Ruth built,
but it's a developer tool, so teach it last.
