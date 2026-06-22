# Build Your Own AI Podcast Assistant — Beginner Workshop

**Who this is for:** complete beginners. You do **not** need to code, install anything, or
have used AI tools before. If you can fill in a text box and click Save, you can do this.

**What you'll build:** a set of small AI assistants (Google calls them **Gems**) that
together produce a weekly AI-news podcast — from researching the news, to writing the
script, to making the audio, to sending a newsletter.

**Time:** about 60–90 minutes the first time. After that, making an episode takes ~30 min.

> **The one idea to hold onto:** an "AI agent" is just an assistant you've given a clear
> job description to. You write the job description once (we'll give you the words to
> paste), and from then on it does that job whenever you ask. That's it. No magic.

---

## What we're building (the big picture)

You'll create **4 assistants** and do **2 manual steps**. Each hands its result to the next:

```
1. Research Gem    → finds and ranks this week's AI news        (you build this)
2. Script Gem      → turns the news into a two-host script      (you build this)
3. Fact-Check Gem  → checks every claim is true                 (you build this)
4. (manual) Audio  → NotebookLM turns the script into audio     (no building)
5. Newsletter Gem  → writes the email                           (you build this)
6. (manual) Publish→ post the audio + send the email            (no building)
```

Don't worry about the whole chain yet. We'll build them one at a time and test each before
moving on.

---

## A 2-minute vocabulary (everything you'll see)

| Word | What it actually means |
|---|---|
| **Gem** | A custom AI assistant you create by writing it a job description. Reusable. |
| **Instructions** | The job description you type into the Gem. The most important part. |
| **Prompt** | Anything you type to the assistant in the chat box. |
| **Grounding / Google Search** | The assistant looking things up on the live web so it doesn't make things up. |
| **NotebookLM** | A separate free Google tool that can turn documents into a two-host audio show. |
| **Source** | A web link that proves a fact is real. |

---

## Part 0 — One-time setup (5 minutes)

You only do this once.

1. Open your web browser (Chrome is easiest).
2. Go to **gemini.google.com** and sign in with your **work Google account**
   (the one with Gemini Enterprise).
3. Look at the **left sidebar**. Find and click **Gems**.
   - If you don't see it, click the **☰ menu** (three lines) in the top-left to expand the
     sidebar, then look for **Gems**.
4. You're now in the **Gem manager**. You'll see Google's ready-made Gems, a space for
   "Your Gems", and a **+ New Gem** button in the top-right.

That's it. You're ready to build.

> 💡 **Beginner shortcut:** the screens may look slightly different from these words —
> Google updates the design often. The buttons (**New Gem**, **Name**, **Instructions**,
> **Save**) will still be there, maybe in a slightly different spot. Look for the label, not
> the exact location.

---

## Part 1 — Build Agent 1: the Research Gem

**Its job:** search the web for the last 7 days of AI news and hand you a ranked list of
stories to choose from. (This replaces the old "scan my email inbox" step — much simpler.)

### Build it

1. In the Gem manager, click **+ New Gem** (top-right).
2. In the **Name** box, type: `Podcast Research`
3. Click into the big **Instructions** box and **paste the entire block below** (copy from
   the first line to the last):

```
You help prepare a weekly AI-news briefing for senior executives (C-suite, board, managing directors).

When I give you a focus, or just say "go", search the live web for significant AI news from the LAST 7 DAYS across these areas: OpenAI; Google DeepMind and Anthropic; Meta, xAI and other AI labs; AI regulation and policy; and how businesses are adopting AI.

Combine duplicate stories (if several outlets report the same thing, merge them and keep all the links). Then rank everything into three tiers:
- Tier 1 — Must-Cover: major model releases, big business deals, regulation with real impact, major AI-company news.
- Tier 2 — Strong Interest: new products, business adoption, notable research, policy.
- Tier 3 — Worth Knowing: technical or niche updates.

Show the result in this format, numbering stories 1, 2, 3... straight through all tiers:

# AI Podcast Story List — [today's date]
## Tier 1 — Must-Cover
### 1. [story title]
- Summary: [2-3 plain factual sentences]
- Why executives care: [one sentence]
- Sources: [a link to the original source] ([date])
## Tier 2 — Strong Interest
## Tier 3 — Worth Knowing

Rules: use plain, factual language — no hype, no opinions, no advice. Every story must have at least one link to a primary source (the company or government site, not a blog summarizing it). When you finish, ask me which stories I want to cover, and mention that 4 to 6 stories make a good 20–30 minute episode.
```

4. **(Important for this Gem)** If you see a **Default tool** or **Tools** option, choose
   the one that lets it **search the web** (it may be called *Deep Research* or
   *Web search*). This is what lets it find real, current news.
5. On the **right-hand Preview panel**, test it: type `go` and press Enter. Wait ~30–60
   seconds — it's searching the web.
6. If the list looks good, click **Save** (top-right).

> ⚠️ **The #1 beginner mistake:** the Preview does **not** save your Gem. You must click
> **Save**, or your work disappears.

### Test it / what "good" looks like
You should get a numbered list of recent real AI stories, each with a link, sorted into
three tiers, ending with "which stories do you want to cover?" If it made up stories with
no links, the web-search tool isn't on — go back to step 4.

✅ **You just built your first AI agent.** The other three are the same process.

---

## Part 2 — Build Agent 2: the Script Gem

**Its job:** take the stories you picked and write a natural two-host podcast script in your
house style.

### Build it
1. Gem manager → **+ New Gem**.
2. **Name:** `Podcast Script`
3. Paste this into **Instructions**:

```
You write two-host AI-news podcast scripts for senior executives. I will paste a story list and tell you which stories to cover. Write the full script using ONLY the facts in that material — never add numbers, names, or claims from your own knowledge.

Style rules — follow them exactly:
- Factual only. No opinions, no advice. Never say "executives should..."
- HOST 1 carries the facts in 2-3 sentence blocks. HOST 2 reacts or asks short questions in 1-2 sentences. About 75% Host 1, 25% Host 2.
- Every HOST 2 turn must be at least 20 words (short lines sound robotic when read aloud). Mix questions, statements, and the occasional exclamation — not all questions.
- HOST 1 starts each reply by briefly acknowledging HOST 2 ("Right —", "Exactly —").
- Don't put a colon right before a number. Write "at a 350 billion dollar valuation", not "Valuation: 350 billion".
- Open by naming the week's overall theme, not a list of topics. Use a smooth sentence to move between stories — never "Next up" or "Moving on". End each story with a clear, confident statement.
- Briefly explain any company or term a non-expert wouldn't know, the first time it appears.
- Do not introduce the hosts by name.

Use this layout:
# AI Weekly Podcast — [date]
## INTRO
HOST 1: Welcome to the AI podcast. It's [Month Day, Year], and this week [one or two sentences on the theme].
HOST 2: [a reaction and why it matters]
HOST 1: Let's get into it.
## STORY 1: [title]
HOST 1: ...  HOST 2: ...  HOST 1: ... (end with a confident takeaway, then a bridge to the next story)
## CLOSING
HOST 1: [one sentence tying the week together]  HOST 2: [a short closing line]
HOST 1: Thanks for listening. See you next week.
Sources: [list every link used]

When you're done, remind me to run the script through the Fact-Check Gem before recording.
```

4. Click **Save**.

### Test it
Open your **Podcast Research** Gem, copy the story list it made, then come to this Gem and
type: `Cover stories 1, 2 and 4 from this list:` and paste the list underneath. You should
get a full HOST 1 / HOST 2 script.

---

## Part 3 — Build Agent 3: the Fact-Check Gem

**Its job:** read the script and confirm every fact is actually in the sources. This is what
keeps you from publishing a wrong number.

### Build it
1. Gem manager → **+ New Gem**.
2. **Name:** `Podcast Fact-Check`
3. Turn on the **web search tool** (same as the Research Gem) so it can open the sources.
4. Paste this into **Instructions**:

```
You are a careful fact-checker for a podcast script. I will paste a script and its list of source links. Open each source on the web and check the script against it.

Find every fact — especially numbers, dollar amounts, percentages, dates, company names, and quotes. Label each one:
- VERIFIED — matches a source exactly
- MODIFIED — close but the number or wording is off (show both versions)
- NOT FOUND — you can't find it in any source
- CONTRADICTED — a source says something different

Report it like this:
## Fact-Check Report
### Verified
- "[fact]" — confirmed in [link]
### Needs correction (Modified)
- Script says: "[fact]"  |  Source says: "[the real version]"  |  [link]
### Not found in the sources
- "[fact]"
### Contradicted
- Script says: "[fact]"  |  Source says: "[the real version]"  |  [link]

Then give me the corrected sentences for anything that was Modified, Not Found, or Contradicted. Never approve a fact from your own memory — only from what the sources actually say.
```

5. Click **Save**.

### Test it
Paste the script from Part 2 plus its "Sources" links. You'll get a report; fix any flagged
lines in your script document before moving on.

---

## Part 4 — Make the audio with NotebookLM (no building — 10 minutes)

There's nothing to build here. NotebookLM is a free Google tool that reads your script and
produces a **two-host audio conversation** automatically.

1. Go to **notebooklm.google.com** and sign in with the same account.
2. Click **Create new** (a "notebook" is just a workspace for one episode).
3. Click **Add source** and either upload your script file or paste the script text.
4. Find the **Studio** panel and choose **Audio Overview**.
5. Click **Customize** and paste this so it follows your style:
   ```
   Two hosts. Read the script faithfully and conversationally — Host 1 carries the facts in longer turns, Host 2 reacts and asks short questions. Keep a plain, factual tone for senior executives. Do not add jokes, opinions, or anything that isn't in the script.
   ```
6. Click **Generate** and wait a few minutes. Listen to the result.
7. If a part is wrong, regenerate with a more specific instruction. When happy, **download**
   the audio file.

> If you ever need exact, controllable voices instead, the alternative is **Google Cloud
> Text-to-Speech** — but that needs a developer's help. NotebookLM is the no-code way and is
> the right starting point.

---

## Part 5 — Build Agent 4: the Newsletter Gem

**Its job:** write the email that goes out with each episode.

### Build it
1. Gem manager → **+ New Gem**.
2. **Name:** `Podcast Newsletter`
3. Paste this into **Instructions**:

```
You write the email newsletter for a weekly AI-news podcast for senior executives. I will paste the final script and story list. Produce:
1. A 2-3 sentence summary of the episode — plain and factual, no hype, no advice.
2. Four to six headline bullet points, one per story, each ending with its source link.
3. A simple, clean email in HTML using only inline styles, a single column, about 600 pixels wide, and no JavaScript (many email programs remove those). Put the text #EPISODE_URL where the audio link will go later.

Before you give me the HTML, first show me ONLY the summary and the headlines, and wait for me to approve them. After I approve, give me the full HTML. If I say I'd rather not use HTML, give me the same content as plain text I can paste into a Google Doc or an email.
```

4. Click **Save**.

### Test it
Paste your final script and story list. Approve the summary, then collect the HTML it gives
you.

---

## Part 6 — Publish (manual — 10 minutes)

1. **Upload the audio** to your shared **Google Drive** podcast folder. Right-click it →
   **Share** → set to "Anyone with the link" → **Copy link**.
2. In the newsletter HTML, **replace `#EPISODE_URL`** with that link.
3. On your **Google Sites** podcast site, add a new page for the episode (title, the audio
   link, the summary and headlines), and **Publish** it.
4. Put the newsletter into your email tool as a **draft**. Read it once, then send it
   yourself. (Never set it to send automatically.)

🎉 **That's a full episode**, start to finish, built and run by you.

---

## Part 7 — Your weekly routine (after everything's built)

Once the four Gems exist, each week is just:

1. Open **Podcast Research** → type `go` → pick your stories.
2. Open **Podcast Script** → paste the picks → get the script.
3. Open **Podcast Fact-Check** → paste the script + sources → apply fixes.
4. **NotebookLM** → generate + download the audio.
5. Open **Podcast Newsletter** → paste the script → approve → get the email.
6. Upload audio, update the link, publish the page, send the email.

---

## If something goes wrong

| Problem | Fix |
|---|---|
| My Gem disappeared | You forgot to click **Save** after building it. Rebuild and Save. |
| Research made up fake stories with no links | The web-search tool isn't turned on for that Gem. Edit it and enable web search. |
| The script sounds robotic / hosts too short | That's expected if Host 2's lines are short — the rules fix this; don't change the rules, just regenerate. |
| Fact-check approves things without checking | Make sure the web-search tool is on, and that you pasted the **source links** along with the script. |
| The audio adds stuff not in my script | Regenerate in NotebookLM with a stricter Customize note ("read only what's in the script"). |
| The buttons look different from this guide | Google changes the design often. Look for the **label** (Name, Instructions, Save), not the exact position. |

---

## Want to go further? (optional, for the technically curious)

Everything above is **no-code** using Gems. There's also a "power user" version of this same
kit that runs in a terminal as slash commands (`/podcast:research`, `/podcast:script`, …)
using the **Gemini CLI**. Those files live in the `.gemini/` folder of this kit, and the
main `README.md` explains how to install them. You do **not** need this to run the workshop —
it's just the same assistants in a different, faster wrapper for people comfortable with a
command line.

---

### Sources used to write this guide
- [Tips for creating custom Gems — Google Gemini Help](https://support.google.com/gemini/answer/15235603?hl=en)
- [Create a Gem (Gem builder)](https://gemini.google.com/gems/create)
- [Grounding with Google Search — Gemini API](https://ai.google.dev/gemini-api/docs/google-search)
- [NotebookLM](https://notebooklm.google.com)
