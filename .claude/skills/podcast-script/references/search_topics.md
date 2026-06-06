# AI Podcast — Parallel Research Agent Instructions

These are standing search instructions for the 5 parallel web search agents launched during Phase 2 of the `/podcast-script` workflow. Each agent searches for breaking AI news from the **last 7 days** that newsletters may have missed or underreported.

---

## Agent 1: OpenAI Breaking News

**Search focus:** OpenAI — models, products, policy, personnel, partnerships, legal

**Search queries to run (pick the most relevant 2-3):**
- `OpenAI news last 7 days`
- `OpenAI model release announcement [current week]`
- `OpenAI partnership deal [current week]`
- `OpenAI regulation policy [current week]`
- `OpenAI Sam Altman [current week]`

**What to look for:**
- New model releases or capability announcements (GPT-5, o-series, etc.)
- Product launches (ChatGPT features, API updates, enterprise deals)
- Funding rounds, valuation news, M&A
- Leadership changes or departures
- Government/regulatory interactions
- Legal actions or controversies with business impact

**Output format:**
List each story as:
```
### [Story Title]
- **What happened**: [factual 1-2 sentence summary]
- **Why it matters**: [exec relevance]
- **Source**: [URL]
- **Date**: [date published]
```

---

## Agent 2: Google DeepMind & Anthropic Breaking News

**Search focus:** Google AI / DeepMind / Gemini + Anthropic / Claude — models, products, enterprise

**Search queries to run:**
- `Google DeepMind Gemini news last 7 days`
- `Anthropic Claude news last 7 days`
- `Google AI enterprise announcement [current week]`
- `DeepMind research breakthrough [current week]`
- `Anthropic funding partnership [current week]`

**What to look for:**
- Gemini model updates (1.5, 2.0, etc.) or new product launches
- Google Cloud AI integrations
- Anthropic Claude API updates, enterprise partnerships
- AlphaFold or other DeepMind research with real-world impact
- Google/Anthropic regulatory positions

**Output format:** Same as Agent 1.

---

## Agent 3: AI Regulation & Policy News

**Search focus:** Government, regulatory, legislative, and policy developments affecting AI

**Search queries to run:**
- `AI regulation news last 7 days`
- `AI executive order policy [current week]`
- `EU AI Act implementation [current week]`
- `AI legislation Congress Senate [current week]`
- `AI copyright lawsuit ruling [current week]`
- `AI safety governance [current week]`

**What to look for:**
- New laws, executive orders, or proposed legislation
- EU AI Act enforcement updates or compliance deadlines
- Copyright/IP rulings involving AI training data
- Government AI procurement or use policies
- International AI governance developments (UK, China, UN)
- Industry self-regulation or voluntary commitments

**Output format:** Same as Agent 1.

---

## Agent 4: Meta, xAI (Grok), and Other Model Labs

**Search focus:** Meta AI / Llama + xAI / Grok + Mistral / Cohere / other labs

**Search queries to run:**
- `Meta AI Llama news last 7 days`
- `xAI Grok announcement [current week]`
- `Elon Musk AI [current week]`
- `Mistral AI news [current week]`
- `open source AI model release [current week]`
- `AI startup funding [current week]`

**What to look for:**
- Llama model updates or open-source releases with business implications
- Grok/xAI product launches or major capability changes
- Mistral, Cohere, AI21, or other model lab news
- Open-source vs. closed-source AI dynamics with enterprise relevance
- Notable AI startup funding ($50M+)

**Output format:** Same as Agent 1.

---

## Agent 5: Enterprise AI & Economic Impact

**Search focus:** AI adoption in business, workforce, economic effects, enterprise deals

**Search queries to run:**
- `enterprise AI adoption news last 7 days`
- `AI jobs workforce impact [current week]`
- `AI productivity business [current week]`
- `Microsoft Copilot enterprise [current week]`
- `AI economic impact report [current week]`
- `AI chip semiconductor Nvidia [current week]`

**What to look for:**
- Major enterprise AI deployments or contracts
- AI-driven layoffs, hiring shifts, or workforce studies
- Microsoft Copilot / Azure AI enterprise news
- Nvidia, AMD, or chip supply chain news with AI relevance
- Economic research or analyst reports on AI's business impact
- Industry-specific AI adoption (finance, healthcare, legal, consulting)

**Output format:** Same as Agent 1.

---

## Agent Output Assembly

After all 5 agents complete, compile results into a unified section:

```markdown
## Breaking News (Web Research — Last 7 Days)

### Agent 1: OpenAI
[stories]

### Agent 2: Google/DeepMind/Anthropic
[stories]

### Agent 3: Regulation & Policy
[stories]

### Agent 4: Meta/xAI/Other Labs
[stories]

### Agent 5: Enterprise & Economic
[stories]
```

Then proceed to Phase 3 (Synthesis) to merge with newsletter stories.
