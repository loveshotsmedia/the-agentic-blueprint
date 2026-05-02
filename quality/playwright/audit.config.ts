/**
 * PLAYWRIGHT AUDIT CONFIG
 *
 * This is the only file that changes when you use The Blueprint
 * on a different project.
 *
 * The test engine (booking.spec.ts) stays the same forever.
 * This config file tells it where to look and what to check.
 *
 * ON CAMERA TEACHING MOMENT:
 * "See this file? This is the only thing I change when I take
 *  The Blueprint and apply it to a different business.
 *  The plumbing company gets a different BASE_URL and a different
 *  test call. The engine doesn't change. Only the config does."
 */

export const config = {

  // ── Where the system lives ────────────────────────────────────────────────
  BASE_URL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
  API_URL: process.env.API_URL || "http://localhost:8000",

  // ── The test call ─────────────────────────────────────────────────────────
  // This is the fake call data the Playwright test injects into the system.
  // It simulates a real Vapi webhook without needing an actual phone call.
  TEST_CALL: {
    call_sid: "test-call-playwright-001",
    caller_phone: "+15555550100",
    transcript: `
      Agent: Thanks for calling Rich Off AI HVAC, how can I help you today?
      Caller: Hi, my name is John Smith and my AC stopped working.
      Agent: I'm sorry to hear that. What's the address for the service?
      Caller: It's 123 Main Street, Naples Florida.
      Agent: And is this a home or a commercial property?
      Caller: It's my home.
      Agent: How urgent is this for you — is it an emergency, do you need
             someone this week, or are you flexible on timing?
      Caller: I'd say this week if possible, it's pretty hot.
      Agent: Absolutely, let me pull up some pricing for you.
    `,
    expected: {
      name: "John Smith",
      address: "123 Main Street, Naples Florida",
      issue_type: "ac",
      urgency: "this_week",
      property_type: "home",
      emergency_detected: false,
    }
  },

  // ── The emergency test call ───────────────────────────────────────────────
  // Tests that emotion detection works correctly.
  // This call should trigger emergency mode.
  TEST_CALL_EMERGENCY: {
    call_sid: "test-call-playwright-emergency-001",
    caller_phone: "+15555550101",
    transcript: `
      Agent: Thanks for calling Rich Off AI HVAC, how can I help you today?
      Caller: Hi it's an emergency, my pipe burst and water is everywhere,
              I'm at 456 Oak Avenue.
      Agent: I understand, let's get someone out to you right away.
             Can I get your name?
      Caller: Sarah Johnson.
      Agent: And is this a home?
      Caller: Yes, my home.
    `,
    expected: {
      name: "Sarah Johnson",
      address: "456 Oak Avenue",
      issue_type: "plumbing",
      urgency: "emergency",
      property_type: "home",
      emergency_detected: true,
    }
  },

  // ── Dashboard pages to audit ──────────────────────────────────────────────
  PAGES: {
    calls: "/calls",
    quotes: "/quotes",
    bookings: "/bookings",
  },

  // ── Timeouts ──────────────────────────────────────────────────────────────
  // How long to wait for each operation before failing.
  // The full agent chain should complete in under 2 minutes.
  CHAIN_TIMEOUT_MS: 120_000,   // 2 minutes — from the RUNTIME.md budget
  PAGE_LOAD_TIMEOUT_MS: 10_000,
  API_TIMEOUT_MS: 5_000,

  // ── What the dashboard must show after a successful booking ───────────────
  BOOKING_ASSERTIONS: {
    // These strings must appear somewhere on the bookings page
    // after the test call completes successfully
    MUST_CONTAIN: [
      "John Smith",
      "123 Main Street",
      "ac",
    ],
    // These strings must NOT appear — they indicate broken state
    MUST_NOT_CONTAIN: [
      "undefined",
      "null",
      "[object Object]",
      "NaN",
    ],
  },

}
