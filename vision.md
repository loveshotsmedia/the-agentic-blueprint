# Vision — Rich Off AI HVAC

**Last updated:** 2026-04-30
**Written by:** Cam Wilson
**Read by:** Every agent in this system before doing anything

---

## What this business is

Rich Off AI HVAC is a demo field service business built on The Agentic Blueprint framework.

It exists to prove one thing:

> A small business owner with no staff and no tech background
> can have an AI workforce that answers calls,
> generates quotes, and books jobs —
> running 24 hours a day, 7 days a week,
> without them touching anything.

---

## The problem it solves

A plumber, HVAC technician, or field service owner has one of two problems:

**Problem A — They answer every call themselves.**
They're under a sink at 2pm. Phone rings. They miss it.
That caller calls the next company and books with them instead.
The job is gone.

**Problem B — They hire someone to answer calls.**
Now they're paying $18/hour for someone to read from a script,
get the details wrong half the time,
and go home at 5pm.

**The Blueprint solves both.**
An AI agent answers every call.
Asks the right questions.
Generates a real quote on the call.
Books the job to the calendar.
Sends the customer a confirmation text.
All of it — while the owner is under that sink.

---

## What "done" looks like

A customer calls **+1 (239) 294-2140**.

By the time they hang up:
- Their name, address, issue, urgency, and property type are in Supabase
- A quote has been generated and spoken to them on the call
- A job is booked in Google Calendar
- They have received an SMS confirmation with the date, time, and address
- The owner has been notified

No human touched anything.
No data was lost.
No appointment was missed.

That is the definition of done for this system.

---

## What this system is NOT trying to do

- It is not trying to replace a full CRM
- It is not trying to handle billing or invoicing
- It is not trying to manage existing customers
- It is not trying to do marketing or outreach

It does one thing completely:
**Turn an inbound call into a booked job.**

Everything else is out of scope for this version.

---

## Why it's built the way it's built

Three things will eventually break any AI system that isn't built on a solid foundation:

**1. The system restarts and loses everything.**
A server reboots at 3am. An in-flight booking disappears.
The Blueprint fixes this by writing every piece of data to Supabase
the moment it exists — not at the end of the call.

**2. The AI does something confidently wrong.**
The agent sounds excited when a customer says their pipe burst.
Or it quotes $5,000 for a $200 job.
The Blueprint fixes this with emotion detection and a quote validator
that checks every price before it gets spoken.

**3. You want to switch tools and have to rebuild everything.**
You start with Supabase and want to move to GoHighLevel.
With a normal codebase that's a rewrite.
The Blueprint fixes this with one environment variable.
Change `CRM_DESTINATION=supabase` to `CRM_DESTINATION=ghl`.
The agents don't change. The system reroutes.

These are not theoretical problems.
They are the three things that kill real systems in production.
This system is built to survive all three.

---

## The five questions the agent always asks

Every inbound call collects exactly these five fields.
Nothing ships until all five are collected.

```
1. name          — who is calling
2. address       — where the job is
3. issue_type    — AC / heating / plumbing
4. urgency       — emergency / this week / flexible
5. property_type — home / commercial
```

If any field is missing at the end of the call — the booking does not proceed.
The agent re-asks. Every time.

---

## The voice

The agent's default voice is **bubbly and energetic.**
Warm. Helpful. Like the best receptionist you ever hired.

The agent's emergency voice is **calm and direct.**
No excitement. No filler. Just: "I understand. Let's get someone out to you."

The switch happens automatically when the caller uses any of these words:
`emergency`, `flooding`, `burst`, `no heat`, `gas leak`, `not working at all`

This is not optional. It is one of the most important evals in the system.
A customer with a burst pipe does not want to hear an excited AI.

---

## Who this is for

**The business owner** who wants this running in their business.
They don't need to understand how it works.
They need to know it works, that it won't lose bookings,
and that they can change the business name and phone number
and have it running in under an hour.

**The aspiring engineer** who wants to understand how to build
agentic systems that a senior software engineer would respect.
Every design decision in this system has a reason.
The reason is in this file, in `harness/RUNTIME.md`,
and in the contracts.

Both people are welcome here.
The Blueprint is built for both.

---

*This file is read-only for agents.*
*If you are an AI agent reading this — do not modify it.*
*Use it to understand what you are building and why.*
