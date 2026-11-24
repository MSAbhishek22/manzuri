# LinkedIn draft 03 — Manzuri (Marketing/Management lane)
State: DRAFT_READY · package INCOMPLETE (live URL + recording after
deploy) · NOT approved, NOT scheduled.

## Draft copy

If you have ever run social media for a small business, you have
lived this scene.

The posts go into a WhatsApp group as screenshots. Feedback comes
back as voice notes and circled pictures, buried under the next
day's chat. A week later, nobody can prove which version the client
approved. And one day, the wrong version goes out.

I went looking at what the proper tools charge to fix this.
Planable's own pricing page: $39 per workspace per month — and a
workspace is one client. The setting that makes approval mandatory
only exists on the $59 plan. A small agency with five clients pays
five times, for one feature.

So I built the smallest thing that kills the actual problem. It is
called Manzuri.

The agency uploads the month's posts once. The client gets one link
inside the WhatsApp chat they already use. No login, no app, no
password. They tap Approve, or Request changes — and if they ask for
changes, they have to say whether it is the image, the words, or
both. No more archaeology.

But the feature I care about most is a rule, not a screen:

If the agency edits a post after the client approved it, the
approval is voided. Automatically. The post goes back to "waiting",
and the history shows exactly what happened.

That one rule means an approved post can never quietly become a
different post. Which is the whole dispute, gone.

What it deliberately does not do: post to Instagram for you. That
is a different permissions world, and bolting it on would have made
this a worse approval tool. It ends at an export checklist of only
the approved posts, in the versions that were approved.

Next step is unglamorous and important: put it in front of three
real micro-agencies and watch whether their clients actually tap
the link. That answer decides what v2 is.

## Evidence packet
- Problem evidence: Planable pricing help page (read directly in
  research, Nov 2026); G2 Sprout Social review (verified SMB
  reviewer, Oct 2026); eClincher/VonaHub failure analyses.
- Build evidence: git 9ddff59; 7/7 store tests; live HTTP smoke —
  approve → edit → approval voided → re-approve → export purity;
  bad-token and foreign-post guards verified.
- Claims NOT made: no user counts, no time-saved %, no ROI. The
  validation-with-agencies step is stated as future, not done.
- Missing before approval: live URL, GitHub URL, screen recording.
