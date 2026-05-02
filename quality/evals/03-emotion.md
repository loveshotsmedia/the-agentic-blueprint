# Eval 03 — Emotion Detection

**Stage:** Quote Agent (tone of quote_spoken_text)
**Severity if failed:** HIGH — does not block booking but must be logged and reviewed
**Checked by:** evaluator.py (automated after every call)

---

## What "done" means for emotion detection

The voice agent shifted to the correct tone based on what the caller said.
Bubbly and energetic for standard calls.
Calm and direct for emergencies.

---

## The two modes

### Standard mode (default)
Used when: no emergency keywords detected in the transcript.

Signs it's working:
- Warm, friendly language
- Conversational pace
- "I'd love to help you get that scheduled"

### Emergency mode
Used when: any trigger word appears in the caller's transcript.

**Trigger words:**
`emergency`, `flooding`, `burst`, `no heat`, `no cooling`,
`gas leak`, `not working at all`, `pipe broke`, `water everywhere`,
`sparking`, `smoke`, `dangerous`

Signs it's working:
- No exclamation marks
- No filler phrases like "Absolutely!" "Great news!" "Wonderful!"
- Direct and calm: "I understand. Let's get someone out to you."
- Slower conversational pacing in the spoken text

---

## The checklist

**When emergency keywords detected in transcript:**
- [ ] `emergency_detected` is `true` in the plan file
- [ ] `quote_spoken_text` contains no exclamation marks
- [ ] `quote_spoken_text` contains none of: "Absolutely", "Great news", "Wonderful", "Fantastic", "Amazing"
- [ ] `quote_spoken_text` tone is direct, not enthusiastic
- [ ] `tone` field in quote file is `"emergency"`

**When no emergency keywords detected:**
- [ ] `quote_spoken_text` tone is warm and helpful
- [ ] `tone` field in quote file is `"standard"`

---

## Why this matters

This is the Karpathy problem made real.

Andrej Karpathy — the person who coined the term "vibe coding" —
described how AI models can simultaneously refactor 100,000 lines of code
and tell you to walk to the car wash.

The same model that generates a technically perfect quote
will sound excited when a customer's pipe just burst.
Not because it's broken — because tone-matching is outside the
standard training circuit.

This eval catches it.
The pricing skill and quote prompt prevent it.
The evaluator confirms it didn't happen.

---

## What to do when this eval fails

The booking proceeds — a tone failure does not block a completed booking.
But the call is flagged on the dashboard with a HIGH badge.
Review the `quote_spoken_text` for that call.
If the tone was genuinely wrong — update the quote agent prompt
and log the change to `state/decisions/`.

Patterns of failure here indicate the prompt needs updating.
One failure is a data point. Three failures is a pattern.
