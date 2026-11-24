# Manzuri

**Client approvals without the WhatsApp archaeology.**

A micro social-media agency uploads a client's posts once. The
client gets one link — sent inside the WhatsApp chat they already
use — and taps **Approve** or **Request changes**. No login, no app,
no password. Every decision is timestamped and locked to the
version the client saw.

## The rule the product exists for
**Editing a post voids its approval.** Change the caption or the
creative after a client approved it, and the post returns to
"waiting" — visibly, with the void written into its history. The
export checklist therefore contains only posts approved at the
version they will actually go out as. The wrong-version dispute —
the daily disease of approval-over-chat — has nowhere to live.

## Why (evidence, Nov 2026)
- Planable's own help page: **$39/workspace/month** (Pro $59), and
  "Required approval" exists only from Pro. One workspace = one
  client, so a five-client micro-agency pays for one feature five
  times over.
- A verified small-business G2 review of Sprout Social ($79/seat):
  no way to seek client approval inside the platform at all.
- Approval-over-chat fails for four named reasons (split feedback,
  version confusion, no record, missed dates) — Manzuri is those
  four, inverted.

## Run it
```
python3 server.py 8797     # agency console at /, client links at /c/<token>
```
Stdlib only. SQLite at `data/manzuri.db`, uploads at
`data/uploads/` (png/jpg/webp/gif, ≤ 3 MB). One Store connection is
shared across server threads behind a re-entrant lock — the live
smoke caught the thread-bound default; see store.py's comment.

## Surfaces
- **Agency console** (desktop): clients, posts, the client link +
  "Send on WhatsApp" (wa.me deep link), the 3D **Month Wall**
  (posture = state: flat green approved, upright waiting, red-tilted
  changes), approved-only export.
- **Client page** (phone-first, no 3D, no JS framework): posts in
  order, thumb-sized Approve / Request changes; a change request
  must say *image, caption, or both* — feedback the agency can act
  on without a follow-up call.

## Honest limits
- No auto-posting to social platforms (deliberate — a separate,
  heavier permissions gate). Manzuri ends at approval + checklist.
- The link is the credential: long, unguessable, one per client.
  Whoever holds it approves as that client.
- Single-process demo scale. Multi-agency auth is a v2 question.

## Tests
```
python3 -m unittest discover -s tests   # 7 tests: the void rule, no-op edits,
                                        # change-kind requirement, export purity,
                                        # token behaviour, counts
```
Plus a live HTTP smoke (24 Nov 2026): create → add → approve →
edit (voided, v2) → re-approve → export shows only the approved v2;
bad token and foreign-post decisions rejected in plain words.
