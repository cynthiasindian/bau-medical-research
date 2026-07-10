# Lessons

## 2026-07-09 — Keyed Streamlit widgets ignore a changed `value` on rerun
The computed score fields (HADS totals, CAM verdict) saved correctly but kept
showing their old empty value on screen after "Save section" — the user
reported it as "scores taking too much time". A widget created with a fixed
`key` keeps its session state across reruns and silently ignores a changed
`value=` parameter.

**Rule:** for read-only/derived widgets whose display must track data, write
`st.session_state[key] = new_value` immediately before instantiating the
widget (and don't pass `value=`). Also: when a user reports "slow", measure
first — this was a stale-display bug, not latency (save round-trip is
~450 ms). And any feedback shown right before `st.rerun()` is invisible;
flash it after the rerun via a session-state flag (e.g. st.toast).

## 2026-07-09 — Mirror the paper instrument exactly; don't "improve" it away
When digitizing a validated paper questionnaire (HADS), I hid the 0–3 score
labels and the A/D subscale columns from the answers, reasoning that scoring
metadata is "for the scorer, not the patient". The user corrected this: they
wanted the form to look like the paper — score label on every reply, the
subscale column (A = Anxiety / D = Depression) on every question, and the
scoring key visible.

**Rule:** the data collectors here are med students administering the
instrument, not patients self-completing it — scoring transparency helps
them cross-check against the paper. Default to reproducing the source
document's visible structure 1:1 (labels, numbering, columns, scoring keys).
Only depart from the paper when the user asks for it, and present such
departures as an explicit option during the plan check-in, never as a silent
default.
