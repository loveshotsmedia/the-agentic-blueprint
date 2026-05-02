# The Agentic Blueprint

**An AI workforce that answers inbound calls, generates quotes, and books jobs — built on a framework any business can deploy in under 5 minutes.**

> *"You can outsource thinking. You cannot outsource understanding."*
> — Andrej Karpathy

---

## 📞 Call the demo right now

**+1 (239) 294-2140**

This is Rich Off AI HVAC — a fully working AI agent built on The Blueprint.
Call it. Ask about AC repair. Get a quote. Book a job.

*No sales pitch. No humans. Just the system working.*

---

## What this system does

A customer calls your business number.
The AI answers, asks the right questions, generates a real quote on the call, books the job to your calendar, and sends a confirmation text — all without you touching anything.

```
Customer calls
      ↓
AI answers — bubbly, professional, detects urgency
      ↓
Asks 5 questions (name, address, issue, urgency, home vs commercial)
      ↓
Generates a quote on the call
      ↓
Offers 3 available time slots
      ↓
Customer picks one
      ↓
Job writes to Google Calendar + Supabase
      ↓
Customer gets SMS confirmation
```

That's it. That's the whole system. Every piece of it is in this repo.

---

## Deploy your own in 5 minutes

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/the-agentic-blueprint)

1. Click the button above
2. Fill in your env vars (Vapi key, Supabase URL, business name)
3. Hit deploy
4. Upload your phone number to Vapi
5. You're live

No terminal required for the basic setup.
Full customization requires the tutorial — link below.

---

## What's inside

```
the-agentic-blueprint/
├── .claude/agents/        Your AI workforce — one file per role
├── harness/               The rules your agents operate inside
├── src/                   The FastAPI backend + dashboard
├── quality/               Evals, tests, and Playwright audit
└── state/                 Everything the system produces at runtime
```

Three types of folders. That's all this is.

**Purple — you write this.** Agents only read it.
**Teal — agents use this.** Code the system runs.
**Amber — system fills this.** Never edit manually.

If you understand those three sentences, you understand the entire framework.

---

## Why it's built this way

Most people vibe code a chatbot and call it an AI system.
That works until a customer calls about a burst pipe at midnight and the AI sounds excited about it.
Or until the system reboots and loses every in-flight booking.
Or until you want to swap from Supabase to GoHighLevel and have to rebuild everything.

The Blueprint solves all three of those problems — with engineering principles that senior software engineers use on systems that handle millions of requests.

Explained clearly enough that someone who has never opened a terminal can understand why they matter.

**The five principles this repo is built on:**

1. **State lives on disk, not in memory.** If the system restarts mid-booking, it picks up exactly where it left off. Nothing is lost.

2. **The agent that builds the thing cannot be the same agent that checks the thing.** Separate roles. Separate contexts. Like a factory with a QA department that's independent from production.

3. **Adapters, not rebuilds.** One environment variable switches the entire system from Supabase to GoHighLevel. Same agents. Same logic. Different destination.

4. **Narrow first, broaden on failure.** Start with the minimum that works. Add complexity only when something breaks and you can prove why.

5. **Every agent has a contract.** Inputs, outputs, budget, what it's allowed to do, and what "done" means. No ambiguity. No agent goes rogue.

---

## The full tutorial

This repo is the companion to a 3+ hour YouTube tutorial series.

**Watch it here:** [youtube.com/@rich_off_ai_](https://youtube.com/@rich_off_ai_)

**What the series covers:**

| Episode | What you build |
|---------|---------------|
| 1 | Stack setup. Clone the repo. Understand every folder. |
| 2 | AGENTS.md + your first brief. The programming interface. |
| 3 | Vapi agent live. Answers calls. Asks the 5 questions. |
| 4 | Quote generation on the call. |
| 5 | Job booking. Google Calendar + Supabase. SMS confirmation. |
| 6 | Swap one env var. Same system. GoHighLevel. |
| 7 | The evaluator. How we know it actually worked. |
| 8 | Full system. The Blueprint story. From prison to programmer. |

No prior coding experience assumed.
By Episode 8 you have a working AI workforce deployed in production.

---

## Get the framework + community

The Blueprint is bigger than this repo.

**Join the newsletter** for the framework walkthrough, templates, and the community of builders using this in their businesses.

**→ [Subscribe at richhoffai.beehiiv.com](https://richhoffai.beehiiv.com)**

You get:
- The complete Blueprint framework doc (not on GitHub)
- AGENTS.md templates for 10 different business types
- Access to the builder community (Railway + Lovable + Supabase stack)
- Early access to new Blueprint systems as they ship

---

## Tech stack

| Layer | Tool |
|-------|------|
| Voice agent | Vapi |
| Phone numbers | Twilio |
| Backend | FastAPI on Railway |
| Database | Supabase |
| Calendar | Google Calendar |
| CRM (optional) | GoHighLevel |
| Dashboard | Lovable (React) |
| AI models | Claude Sonnet (reasoning) + Claude Haiku (fast tasks) |
| E2E testing | Playwright |

---

## Who built this

**Cam Wilson** — founder of Love Shots Media, co-founder of Dartix (AI practice management for financial advisors — received $7.5M pre-revenue acquisition offer).

Self-described vibe coder. Built production systems on this exact stack.
Teaching what actually works, not what sounds good in a tutorial.

From prison to programmer to $7.5M acquisition offer.
The Blueprint is what I wish existed when I started.

**→ [Follow @rich_off_ai_ on YouTube](https://youtube.com/@rich_off_ai_)**

---

## License

MIT — use it, fork it, build on it, sell systems built on it.
If it helps your business, star the repo and tag me when you go live.

---

*Built with The Blueprint framework — harness engineering for agentic systems.*
*Research basis: Tsinghua 2026, Stanford / Omar Khattab 2026, Anthropic agentic patterns.*
