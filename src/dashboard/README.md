# Dashboard — Rich Off AI HVAC

The dashboard is a simple frontend that shows incoming calls,
generated quotes, and booked jobs in real time.

Built in Lovable. Published directly from Lovable.
No Vercel needed — the paid Lovable plan handles custom domains
and environment variables natively.
The backend API it reads from is defined in `src/api/routes/`.

---

## What the dashboard shows

Three pages. Nothing more.

### Calls page (`/calls`)
- Table of all inbound calls
- Columns: date/time, caller phone, customer name, issue type, status
- Status badge: in_progress | processing | completed | failed
- Click a row to see the full transcript
- Auto-refreshes every 30 seconds

### Quotes page (`/quotes`)
- Table of all generated quotes
- Columns: date/time, customer name, service category, quote range, tone
- Quote range displayed as: $150 – $300
- Tone badge: standard (green) | emergency (red)

### Bookings page (`/bookings`)
- Table of all booked jobs
- Columns: job date, customer name, address, issue type, quote range, SMS status
- SMS badge: delivered (green) | failed (red)
- Calendar destination badge: Google | GHL
- Upcoming jobs shown first

---

## API endpoints the dashboard calls

All read-only. No write operations from the dashboard.

```
GET /api/calls              — calls page
GET /api/calls/{call_sid}   — call detail + transcript
GET /api/quotes             — quotes page
GET /api/quotes/{call_sid}  — quote for a specific call
GET /api/bookings           — bookings page
GET /api/bookings/{call_sid}— booking for a specific call
GET /health                 — server status (shown in header)
```

Base URL comes from the `VITE_API_URL` environment variable in Lovable.

---

## Build this in Lovable

**Prompt to paste into Lovable:**

```
Build a simple operations dashboard for Rich Off AI HVAC.

Three pages: Calls, Quotes, Bookings.

API base URL: use the VITE_API_URL environment variable.

Calls page:
- Fetch GET /api/calls on load and every 30 seconds
- Show a table with columns: Date/Time, Phone, Customer Name,
  Issue Type, Status
- Status is a badge: in_progress (yellow), processing (blue),
  completed (green), failed (red), completed_with_issues (orange)
- Clicking a row shows a slide-out panel with the full transcript

Quotes page:
- Fetch GET /api/quotes on load
- Show a table with columns: Date/Time, Customer, Service Category,
  Quote Range, Tone
- Quote range format: $150 – $300
- Tone is a badge: standard (green), emergency (red)

Bookings page:
- Fetch GET /api/bookings?upcoming_only=false on load
- Show a table with columns: Job Date, Customer, Address,
  Issue Type, Quote, SMS
- SMS is a badge: delivered (green), failed (red)
- Sort by job_date ascending (next upcoming first)

Header:
- Business name: Rich Off AI HVAC
- Show server status from GET /health
  (green dot if ok, red dot if unreachable)
- Navigation: Calls | Quotes | Bookings

Design:
- Dark background (#0f0f0f)
- Clean, minimal, data-dense
- No charts or graphs needed — just clean tables
- Mobile responsive

Error states:
- If API is unreachable: show "Server offline" banner
- If a table is empty: show "No records yet" message
- Never show undefined, null, or [object Object] to the user
```

---

## After building in Lovable

**Step 1 — Set the environment variable**

In Lovable:
- Go to Project Settings → Environment Variables
- Add: `VITE_API_URL` = your Railway backend URL
- Example: `https://web-production-xxxx.up.railway.app`

**Step 2 — Connect your custom domain**

In Lovable:
- Go to Project Settings → Custom Domain
- Add your domain (e.g. `dashboard.richoffaihvac.com`)
- Follow Lovable's DNS instructions — usually a CNAME record

**Step 3 — Publish**

Hit Publish in Lovable.
Your dashboard is live at your custom domain.

**Step 4 — Add the URL to your .env**

```
DASHBOARD_URL=https://dashboard.richoffaihvac.com
```

---

## Connecting to the Blueprint repo

If you want Lovable to auto-deploy when you push code changes:

In Lovable:
- Go to Project Settings → GitHub
- Connect the `the-agentic-blueprint` repo
- Lovable redeploys automatically on every push to main

---

## Testing the dashboard

Once published, run the Playwright audit:

```bash
PLAYWRIGHT_BASE_URL=https://your-custom-domain.com \
bash scripts/test.sh --e2e
```

This boots the robot, injects a test call, and confirms
the booking appears on the dashboard correctly.

If the Playwright audit passes — the dashboard is wired correctly.

---

## On camera teaching moment

When you show this step on YouTube, point at the environment
variable setting and say:

*"This is why we use an environment variable instead of
hardcoding the Railway URL in the code. If your Railway URL
changes — you update one variable in Lovable settings and
republish. You never touch the code. That's the separation
between configuration and code."*
