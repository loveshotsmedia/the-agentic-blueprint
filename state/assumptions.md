# state/assumptions.md
# Expiring Assumptions Log
#
# Every design choice in this system that encodes a limitation
# gets an entry here. With a review date. With a kill threshold.
#
# This is how the system gets cheaper and simpler over time
# instead of heavier and more expensive.
#
# FORMAT:
# [date] Component: [name]
#   Assumption: What we assumed the model/service cannot do
#   Review date: When to test this assumption again
#   Expiry test: How to test whether it still holds
#   Kill threshold: What result justifies removing this component
#
# RULE: Every entry past its review date gets tested.
# If it passes the expiry test — kill the component.
# If it fails — update the review date and keep it.
#
# ─────────────────────────────────────────────────────────────

[2026-04-30] Component: JSON extraction scaffolding in planner.py
  Assumption: Claude Sonnet cannot reliably extract 5 structured
              fields from a voice transcript without explicit
              JSON output instructions and markdown fence removal.
  Review date: 2026-07-30
  Expiry test: Run 100 real transcripts directly with no output
               scaffolding. Measure valid JSON parse rate.
  Kill threshold: If >= 98% parse without scaffolding — remove
                  the fence-stripping code and simplify the prompt.

[2026-04-30] Component: 3-attempt retry loop in quote_generator.py
  Assumption: Claude Haiku will occasionally generate quotes
              outside the approved price ranges on first attempt,
              requiring a retry.
  Review date: 2026-07-30
  Expiry test: Run 200 quotes. Measure first-attempt validation
               pass rate. Target: 97%+.
  Kill threshold: If first-attempt pass rate >= 99% for 30 days —
                  remove the retry loop. Single attempt only.

[2026-04-30] Component: Emergency tone eval (eval 03)
  Assumption: The quote agent will occasionally use excited tone
              on emergency calls without explicit guardrails in
              the prompt.
  Review date: 2026-10-30
  Expiry test: Run 100 emergency calls. Count tone failures
               (exclamation marks, filler phrases in spoken text).
  Kill threshold: If zero tone failures in 500 emergency calls —
                  the prompt is sufficient, remove the eval check.
                  Keep the prompt guardrail regardless.

[2026-04-30] Component: Calendar-before-Supabase ordering rule
  Assumption: Calendar API is less reliable than Supabase.
              Writing calendar first ensures the technician
              always has a record even if CRM write fails.
  Review date: 2026-10-30
  Expiry test: Monitor calendar write failure rate vs Supabase
               write failure rate over 90 days.
  Kill threshold: If Supabase failure rate exceeds calendar
                  failure rate — swap the order. Update this log.

[2026-04-30] Component: HVAC pricing ranges in SKILL.md
  Assumption: Price ranges are accurate for US market as of 2026.
  Review date: 2026-10-30
  Expiry test: Compare against 3 industry pricing surveys.
               Measure how often advisors manually override quotes.
  Kill threshold: If any category drifts more than 15% from
                  market rates — update SKILL.md ranges.
