# Manzuri — Reference Research + 3D Spec (24 Nov 2026)

## References (from the P7.1 evidence ledger, verified there)
1. **Planable** (help.planable.io, read directly in research) —
   $39/$59 per workspace per month; "Required approval" only from
   Pro. One workspace per client. Takeaway: per-client pricing is
   the pain; Manzuri's unit is the client link, free to create.
2. **G2 Sprout Social reviews** (verified small-business reviewer,
   Oct 2026) — no in-platform client approval at all; teams build
   the calendar elsewhere and schedule by hand. Takeaway: even the
   expensive suites leave this hole; the wedge is real.
3. **eClincher + VonaHub approval-workflow analyses** — approvals
   over chat fail for four named reasons: split feedback, version
   confusion, no record, missed dates. Takeaway: the product spec
   is those four failures, inverted — one place, version-locked,
   timestamped, date-ordered.
4. **WhatsApp itself** (the client's real environment) — the link
   arrives inside an existing chat; no install, no password, no new
   habit. Takeaway: the client page must feel like opening a photo
   in WhatsApp, not like logging into software.
5. **Google Docs "suggestion" state language** (product pattern) —
   people already understand pending / accepted / changes-requested
   as three states with a history. Takeaway: Manzuri uses exactly
   those three states, with the history visible to the agency.

## 3D experience: "The Month Wall" (agency console only)
The client's month as a shallow arc of standing tiles, one per post,
built in Three.js. State is posture, readable across the room:
- **Waiting** — tile stands upright, paper white.
- **Approved** — tile lies back flat and turns green: locked, done.
- **Changes requested** — tile tilts forward, edge in signal red.
Clicking a tile scrolls the console to that post. The wall is the
agency's morning answer to "where does this client stand?" — a
management view, which is why it lives on the desktop console and
never on the client's phone. Fallback: the same three counts as
plain numbers above a 2D grid; the list below the wall always
carries the full state in text.

## Performance / access rules
- One small canvas, ≤ 31 tiles, render on state change only.
- Client page: zero JavaScript frameworks, zero 3D, works on a
  ₹7,000 Android phone on 4G. Buttons ≥ 48px. Works with the token
  link alone — no cookies, no accounts.
