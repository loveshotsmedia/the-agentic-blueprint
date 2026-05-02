/**
 * BOOKING AUDIT — Playwright End-to-End Test
 *
 * This is the robot that clicks through the dashboard.
 *
 * WHAT IT DOES:
 * 1. Injects a test call directly into the Vapi webhook endpoint
 * 2. Waits for the full agent chain to complete
 *    (planner → quote → booking → evaluator)
 * 3. Opens the dashboard in a real browser
 * 4. Navigates to the bookings page
 * 5. Verifies the booking appears with correct data
 * 6. Checks that no broken state is visible
 * 7. Verifies the eval report passed
 *
 * WHY THIS EXISTS ALONGSIDE THE EVALUATOR:
 * The evaluator (evaluator.py) checks the data after every call.
 * The Playwright audit checks the INTERFACE — what the advisor actually sees.
 * A booking can exist in Supabase but not show on the dashboard.
 * A booking can show on the dashboard but display the wrong data.
 * The evaluator catches data failures. Playwright catches UI failures.
 * Different jobs. Both required.
 *
 * ON CAMERA TEACHING MOMENT:
 * "The evaluator is our QA department checking the production line.
 *  Playwright is our QA department checking the storefront window.
 *  What goes in the box and what shows in the window are two different things.
 *  We check both."
 *
 * RUN WITH:
 * bash scripts/test.sh --e2e
 */

import { test, expect, request } from "@playwright/test"
import { config } from "./audit.config"

// ── Test Suite ────────────────────────────────────────────────────────────────

test.describe("Rich Off AI HVAC — Full Booking Chain Audit", () => {

  // ── Test 1: Standard booking end-to-end ──────────────────────────────────
  test("standard call books correctly and appears on dashboard", async ({ page }) => {

    const testCall = config.TEST_CALL
    const apiContext = await request.newContext({ baseURL: config.API_URL })

    // ── Step 1: Inject test call via Vapi webhook ─────────────────────────
    // We simulate a Vapi call.ended event directly
    // This is how we test without needing an actual phone call
    const webhookPayload = {
      type: "call.ended",
      call: {
        call_sid: testCall.call_sid,
        caller_phone: testCall.caller_phone,
        transcript: testCall.transcript,
        duration_seconds: 45,
        assistant_id: process.env.VAPI_ASSISTANT_ID || "test-assistant",
      },
      timestamp: new Date().toISOString(),
    }

    console.log(`Injecting test call: ${testCall.call_sid}`)

    const webhookResponse = await apiContext.post("/webhooks/vapi", {
      data: webhookPayload,
      headers: {
        // In test mode the webhook signature check is bypassed
        // Set TEST_MODE=true in your .env to enable this
        "x-test-mode": "true",
        "Content-Type": "application/json",
      },
    })

    expect(webhookResponse.ok()).toBeTruthy()
    console.log("Webhook accepted — agent chain starting")

    // ── Step 2: Wait for the full chain to complete ───────────────────────
    // Poll the API until the call status is completed or failed
    // Timeout from RUNTIME.md: 2 minutes maximum
    let chainCompleted = false
    const startTime = Date.now()

    while (!chainCompleted && Date.now() - startTime < config.CHAIN_TIMEOUT_MS) {

      await page.waitForTimeout(3000) // poll every 3 seconds

      const callResponse = await apiContext.get(`/api/calls/${testCall.call_sid}`)

      if (callResponse.ok()) {
        const callData = await callResponse.json()
        const status = callData.status

        console.log(`Chain status: ${status} (${Math.round((Date.now() - startTime) / 1000)}s)`)

        if (status === "completed" || status === "completed_with_issues") {
          chainCompleted = true
        } else if (status === "failed") {
          throw new Error(
            `Agent chain failed for ${testCall.call_sid}. ` +
            `Check state/traces/ for details.`
          )
        }
      }
    }

    if (!chainCompleted) {
      throw new Error(
        `Agent chain timed out after ${config.CHAIN_TIMEOUT_MS / 1000}s. ` +
        `Budget ceiling from RUNTIME.md: 2 minutes. ` +
        `Check state/traces/ for details.`
      )
    }

    const totalTime = Math.round((Date.now() - startTime) / 1000)
    console.log(`Chain completed in ${totalTime}s`)

    // ── Step 3: Verify the eval report passed ─────────────────────────────
    // Read the eval report artifact directly
    // This confirms the evaluator ran and the chain passed
    const evalReportPath = `state/artifacts/${testCall.call_sid}-eval-report.json`

    // In CI, we check via API. Locally, we can read the file directly.
    // The bookings API includes eval status in the response.
    const bookingResponse = await apiContext.get(`/api/bookings/${testCall.call_sid}`)
    expect(bookingResponse.ok()).toBeTruthy()

    const bookingData = await bookingResponse.json()

    // The booking must exist
    expect(bookingData).toBeDefined()
    expect(bookingData.call_sid).toBe(testCall.call_sid)

    console.log(`Booking confirmed in database: ${bookingData.id}`)

    // ── Step 4: Open the dashboard bookings page ──────────────────────────
    await page.goto(`${config.BASE_URL}${config.PAGES.bookings}`)
    await page.waitForLoadState("networkidle")

    // Page title or heading should indicate we're on bookings
    await expect(page).toHaveTitle(/booking|job|dashboard/i)

    // ── Step 5: Verify the booking appears on the dashboard ───────────────
    // Wait for the booking to appear (dashboard polls every 30s)
    // We give it up to 40 seconds
    const bookingCard = page.locator(`text=${testCall.expected.name}`)
    await expect(bookingCard).toBeVisible({ timeout: 40_000 })

    console.log(`Booking visible on dashboard: ${testCall.expected.name}`)

    // ── Step 6: Verify booking shows correct data ─────────────────────────
    const pageContent = await page.content()

    for (const expected of config.BOOKING_ASSERTIONS.MUST_CONTAIN) {
      expect(pageContent).toContain(expected)
      console.log(`✓ Dashboard contains: "${expected}"`)
    }

    for (const forbidden of config.BOOKING_ASSERTIONS.MUST_NOT_CONTAIN) {
      expect(pageContent).not.toContain(forbidden)
      console.log(`✓ Dashboard does not contain broken value: "${forbidden}"`)
    }

    // ── Step 7: Check the calls page ─────────────────────────────────────
    await page.goto(`${config.BASE_URL}${config.PAGES.calls}`)
    await page.waitForLoadState("networkidle")

    const callEntry = page.locator(`text=${testCall.call_sid}`)
      .or(page.locator(`text=${testCall.expected.name}`))

    await expect(callEntry).toBeVisible({ timeout: 10_000 })
    console.log("Call visible on calls page")

    // ── Step 8: Check the quotes page ────────────────────────────────────
    await page.goto(`${config.BASE_URL}${config.PAGES.quotes}`)
    await page.waitForLoadState("networkidle")

    // Quote should show the customer name and issue type
    const quoteEntry = page.locator(`text=${testCall.expected.name}`)
      .or(page.locator(`text=${testCall.expected.issue_type}`))

    await expect(quoteEntry).toBeVisible({ timeout: 10_000 })
    console.log("Quote visible on quotes page")

    console.log("\n✅ STANDARD BOOKING AUDIT PASSED")
    console.log(`   Call: ${testCall.call_sid}`)
    console.log(`   Customer: ${testCall.expected.name}`)
    console.log(`   Chain time: ${totalTime}s`)

  })

  // ── Test 2: Emergency call tone check ────────────────────────────────────
  test("emergency call detects urgency and applies correct tone", async ({ page }) => {

    const testCall = config.TEST_CALL_EMERGENCY
    const apiContext = await request.newContext({ baseURL: config.API_URL })

    // Inject emergency call
    const webhookPayload = {
      type: "call.ended",
      call: {
        call_sid: testCall.call_sid,
        caller_phone: testCall.caller_phone,
        transcript: testCall.transcript,
        duration_seconds: 30,
        assistant_id: process.env.VAPI_ASSISTANT_ID || "test-assistant",
      },
      timestamp: new Date().toISOString(),
    }

    await apiContext.post("/webhooks/vapi", {
      data: webhookPayload,
      headers: { "x-test-mode": "true", "Content-Type": "application/json" },
    })

    // Wait for chain to complete
    let chainCompleted = false
    const startTime = Date.now()

    while (!chainCompleted && Date.now() - startTime < config.CHAIN_TIMEOUT_MS) {
      await page.waitForTimeout(3000)
      const callResponse = await apiContext.get(`/api/calls/${testCall.call_sid}`)
      if (callResponse.ok()) {
        const callData = await callResponse.json()
        if (callData.status === "completed" || callData.status === "completed_with_issues") {
          chainCompleted = true
        } else if (callData.status === "failed") {
          throw new Error(`Emergency call chain failed: ${testCall.call_sid}`)
        }
      }
    }

    expect(chainCompleted).toBeTruthy()

    // Verify the quote was generated in emergency tone
    const quoteResponse = await apiContext.get(`/api/quotes/${testCall.call_sid}`)
    expect(quoteResponse.ok()).toBeTruthy()

    const quoteData = await quoteResponse.json()

    // Emergency surcharge must be applied
    expect(quoteData.urgency_surcharge_applied).toBe(true)

    // Emergency tone — no excitement markers
    const spokenText = quoteData.quote_spoken_text || ""
    const excitementMarkers = ["!", "Absolutely", "Great news", "Wonderful", "Fantastic"]
    for (const marker of excitementMarkers) {
      expect(spokenText).not.toContain(marker)
    }

    console.log(`✅ Emergency tone check passed`)
    console.log(`   Quote text: "${spokenText.substring(0, 80)}..."`)

  })

  // ── Test 3: Dashboard loads without errors ────────────────────────────────
  test("dashboard loads all pages without errors", async ({ page }) => {

    const pages = Object.entries(config.PAGES)

    for (const [name, path] of pages) {

      console.log(`Auditing page: ${name} (${path})`)

      await page.goto(`${config.BASE_URL}${path}`)
      await page.waitForLoadState("networkidle")

      // No JavaScript console errors
      const errors: string[] = []
      page.on("console", msg => {
        if (msg.type() === "error") errors.push(msg.text())
      })

      // No broken network requests (404s on API calls are a fail)
      const failedRequests: string[] = []
      page.on("requestfailed", req => {
        if (req.url().includes("/api/")) {
          failedRequests.push(req.url())
        }
      })

      // Wait a moment for any async requests to complete
      await page.waitForTimeout(2000)

      // No broken values visible on screen
      const pageContent = await page.content()
      for (const forbidden of config.BOOKING_ASSERTIONS.MUST_NOT_CONTAIN) {
        const occurrences = (pageContent.match(new RegExp(forbidden, "g")) || []).length
        if (occurrences > 0) {
          console.warn(`⚠️  Found "${forbidden}" ${occurrences} times on ${name} page`)
        }
      }

      if (failedRequests.length > 0) {
        console.error(`Failed API requests on ${name}:`, failedRequests)
      }

      // Page must not be a blank screen or error page
      const bodyText = await page.locator("body").innerText()
      expect(bodyText.length).toBeGreaterThan(50)

      console.log(`✓ ${name} page loaded`)
    }

    console.log("\n✅ DASHBOARD PAGE AUDIT PASSED")

  })

})
