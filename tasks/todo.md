# TODO — Surgical Survey Collector

## Google Sheets go-live (2026-07-10)
- Switched `config.toml` to backend = "google_sheets",
  spreadsheet_id = 1A_szQ3EBQObP6g7d7Dv6YP4PHOohd-1dAAtAVofRh1g,
  service account: survey-app@medical-research-bau.iam.gserviceaccount.com
  (key in ./service_account.json — never share/commit).
- Installed gspread + google-auth; migrated the 1 existing row ("test",
  P-0001) from data/patients.xlsx (now a frozen snapshot, no longer used).
- Verified against the LIVE sheet: connect, migrate, create/save/delete
  round-trip, AppTest smoke. Team gets direct browser access to the sheet.
- UPDATE (same day): grouped 4-row header ported to Google Sheets.
  Shared schema helpers `_schema_blocks()` / `_column_labels()` / `_FILLS`
  now drive BOTH backends. Sheets writer: unmergeCells -> resize/clear ->
  values -> batch merges + repeatCell formats + frozen rows(4)/cols(2) +
  row-3 height + column widths. Gotcha: Sheets forbids frozen columns that
  cut through a merged cell -> merges straddling the freeze line are split
  at column 2 (PATIENT banner = A:B + C:D). Sheets reads use get_all_values
  with header row 4 (falls back to row 1 for legacy flat sheets).
  Verified live: banners/sections/questions/keys rows, frozen 4x2,
  10 merges, create/save/delete round-trip, "test" row intact.

# Pre-Surgery Section 1 (Demographics) from "Survey copy.docx"

## Source
`C:\Users\user\Documents\dalaa\Survey copy.docx` — BAU research questionnaire:
"Postoperative Anxiety and Delirium in General, Regional and MAC Anesthesia"
(PI: Dr. Nariman Salem). Contains: consent form → ~23 demographic/background
questions → 0–10 pain scale (VAS).

## Analysis of the questionnaire
- All questions are categorical (pick-one or pick-many) — no free-number fields
  except the "specify" follow-ups. Age is collected in **brackets** (18-29 …
  60+), not as a number.
- Six questions have conditional "Yes, specify:" follow-ups
  (employment cause, chronic illness list, psychiatric medication, current
  medications, post-op complications, "other" nationality).
- Three questions only apply if "previous surgeries = Yes"
  (complications, told-about-delirium).
- Ends with a 0–10 pain visual-analogue scale.

## UI/UX decisions (recommended)
1. **One section, grouped visually.** Keep Demographics as the single Section 1
   (the app requires S1 to create the patient), but render subgroup headers:
   Personal → Social & Lifestyle → Medical history → Surgical & anesthesia
   context → Financial → Pain. Engine addition: optional `"group"` key on a
   field renders a subheader. (~5 lines in app.py)
2. **Radio buttons for short lists, dropdowns for long.** Yes/No and 2–3-option
   questions become horizontal radios (1 tap, all options visible — much faster
   than dropdowns on 20+ questions). Residence (9), marital (5), age (5) stay
   dropdowns. Engine addition: new `"radio"` field type (string radio,
   horizontal). Also render `bool` as horizontal radio instead of dropdown.
3. **"Specify" follow-ups always visible, optional, with help text** ("Only if
   you answered Yes"). Streamlit `st.form` cannot show/hide fields dynamically
   before submit, and always-visible optional fields match the paper form.
   No engine change needed; avoids a fragile conditional-visibility rewrite.
4. **Pain scale as a 0–10 horizontal likert** (existing `likert` type).
5. **Chronic illness / psychiatric diagnosis as multiselects** (paper says
   "select all that apply") with an "Other — specify" text field after.
6. **Consent checkbox first**: required `bool` "Informed consent signed?" so a
   record can't be completed without documented consent.
7. Keep `demo_full_name` as the working identifier (needed to find the patient
   for the post-op survey); the auto `P-0001` code is the anonymized research ID.

## Tasks
- [x] 1. Engine: add `"radio"` field type (horizontal string radio) in
      `app.py:render_field`; render `bool` as horizontal radio too.
- [x] 2. Engine: support optional `"group"` key → subheader in
      `render_section_form`.
- [x] 3. `surveys.py`: replace Demographics placeholder with the real fields
      from the docx (35 fields, keys `demo_*`, option lists from the paper).
- [x] 4. Verify: AppTest end-to-end — created a full patient (status
      `complete`) and a partial patient (status `partial`), checked stored
      values, then deleted `data/patients.xlsx` so the app starts clean.
- [x] 5. Pre-Surgery Section 2 = HADS, same instrument as post_s2
      (confirmed by user 2026-07-10). Stored in its own hads_pre_* columns
      (items hads_pre_1..14 + 4 auto-score columns) via a prefix parameter
      on the shared _hads_fields()/_hads_total()/_hads_level() factories.
      Placeholder pre2_q* removed; spreadsheet now 87 columns. Verified:
      prefixed scoring unit-checked, AppTest e2e (pre HADS A=21 Abnormal,
      post columns stay empty), Excel row 2 shows the HADS title under
      PRE-SURGERY. All survey content is now COMPLETE.
- [x] 6. Post-surgery section 2 = HADS (see below).
- [ ] 7. (Later) Remove the pre_s3 placeholder once the real pre-S2 questions
      arrive and the "2 sections per survey" structure is confirmed.

## Post-Surgery Section 1 — Short CAM Worksheet (2026-07-09)
Source: `C:\Users\user\Documents\dalaa\CAM-S_English.pdf` — despite the file
name this is the **Short CAM Worksheet** (Hospital Elder Life Program ©1999):
identifies delirium cases only; the sheet itself states it CANNOT produce a
CAM-S severity score. Flagged to the user.

Structure: Evaluator + Date, then
  I.  Acute onset & fluctuating course (a: acute change, b: fluctuation)
  II. Inattention
  III. Disorganized thinking
  IV. Altered level of consciousness (Alert/Vigilant/Lethargic/Stupor/Coma)
Rule: Inattention + ≥1 other Box-1 item (Ia/Ib) + ≥1 Box-2 item
      (III yes, or IV ≠ Alert) → delirium suggested.

### Tasks
- [x] 8. Engine: radio fields accept optional `"horizontal": false`
      (vertical layout for the 5-level consciousness rating).
- [x] 9. Engine: `"computed"` field type — no input widget; value derived
      from the section's other answers at save time; shown as a read-only
      field. Used for the auto "Delirium suggested" verdict column.
- [x] 10. Engine: optional section-level `"intro"` text rendered above the
      form (for the worksheet's orientation-testing note).
- [x] 11. `surveys.py`: replace post_s1 placeholder with the Short CAM —
      groups I–IV, exact original wording, keys `cam_*`, plus
      `cam_delirium_suggested` computed column.
- [x] 12. Verify: 6 unit cases on the CAM algorithm + AppTest end-to-end
      (positive → verdict "Yes", negative → "No", section `complete`,
      post progress 1/2). Removed only the ZZZ test rows — kept the
      user's own "test" patient (P-0001) untouched.

### Review (2026-07-09, post_s1)
- `app.py`: radio honors `"horizontal": false`; new `computed` type renders
  as a disabled text field and is recalculated from the submitted answers in
  `render_section_form` before validation/save; sections can define `"intro"`
  shown as st.info above the form.
- `surveys.py`: `_cam_delirium()` implements the worksheet rule
  (Inattention + ≥1 other Box-1 item + ≥1 Box-2 item; Box 2 = disorganized
  thinking or consciousness ≠ Alert); returns "" until all 5 answers present.
  post_s1 = 8 fields (7 required + 1 computed), wording verbatim from the PDF.
- Spreadsheet now 60 columns; `cam_delirium_suggested` ("Yes"/"No") is the
  study's outcome variable, ready for analysis.
- OPEN: confirm with PI whether Yes/No identification (Short CAM) suffices or
  the protocol needs CAM-S severity scoring (this PDF cannot score severity).

## Section 2 — HADS (2026-07-09)
Source: `C:\Users\user\Documents\dalaa\HADS-PDF.pdf` — Hospital Anxiety and
Depression Scale: 14 items (7 Anxiety + 7 Depression, deliberately
interleaved), each 0–3; subscale totals 0–21
(0–7 Normal · 8–10 Borderline · 11–21 Abnormal).

### Plan
- Items 1–14 verbatim, paper order (interleaving preserved on purpose —
  no subscale grouping visible to the patient).
- Vertical radios; answer texts WITHOUT the scorer's 0–3 digits.
- 4 computed columns on save: anxiety score + level, depression score +
  level (reverse-scored items handled by per-item score maps).
- Paper instruction ("past week … immediate is best") as the intro banner.
- No engine changes needed — reuses radio/intro/computed from earlier work.

### Tasks
- [x] 13. `surveys.py`: HADS item table (text + score map per item),
      generate the 14 radio fields + 4 computed fields.
- [x] 14. Verify: unit-test scoring (incl. reverse-scored items and
      borderline/abnormal thresholds) + AppTest end-to-end, cleaned test rows
      (kept user's P-0001 "test").
- [x] 15. Confirmed with user: HADS is post-S2 ONLY. Pre-S2 will be a
      different questionnaire (still pending).

### Full CRUD on answers & patients (user request, 2026-07-09)
C: create patient ✓ (existed) — but form kept old values -> clear after create.
R: patient list ✓ (existed).
U: gaps — required choice fields could not be un-answered; dates could not
   be cleared; stale widget state could resurrect old values after save.
D: no patient deletion existed at all.

### Tasks
- [x] 16. All choice widgets (select/radio/likert/bool) always offer a
      "(no answer)" option -> any clicked value can be cleared; consistent
      with partial-save (required-ness only drives completion status).
- [x] 17. Date fields get a "Clear this date on save" checkbox when a value
      exists (Streamlit's date picker cannot be blanked natively).
- [x] 18. After every save/create: `_reset_form_state()` drops the section's
      widget session keys so forms always re-read from storage; "created"/
      "deleted"/"saved" confirmations flash after the rerun. New-patient
      form now blanks after creation (no carry-over / no double-create).
- [x] 19. Delete patient: `storage.delete_patient()` + "🗑️ Delete a patient
      (permanent)" expander on the Patient list page — requires ticking
      "I understand this cannot be undone" before the button enables.
- [x] 20. Verified with AppTest: create + form reset, clear a required
      radio to "", clear a date (and it STAYS cleared on the next save),
      UI delete flow removes the row; HADS scoring re-checked (A=21/D=0);
      user's real "test" patient untouched throughout.

## Grouped 3-row Excel header layout (user request, 2026-07-09)
Row 1 = survey banners (PATIENT / PRE-SURGERY / POST-SURGERY, merged),
row 2 = section titles (merged per section), row 3 = field headers,
row 4+ = one patient per row.

UPDATE 2026-07-10: user asked for the full question text in the sheet
(not just keys like hads_pre_1). Layout is now a 4-row header:
row 3 = full question text (italic, wrapped, from each field's label;
meta/status columns get descriptive labels), row 4 = canonical keys
(what the app reads, header row for pandas), data from row 5.
read_df tries header row 4 -> 3 -> 1 so all older layouts still open and
auto-migrate on the next save. Verified: migration kept "test" (P-0001),
question text present for demographics/HADS/CAM/scores, create/delete
round-trip, app renders.

### Tasks
- [x] 21. `storage.py` Excel backend: write with openpyxl — merged/styled
      rows 1-2, field keys in row 3, data from row 4; freeze panes (C4);
      column widths; PATIENT gray / PRE green / POST blue banners.
      Read with header=row 3, ValueError-safe fallback to the legacy flat
      layout (auto-migrates on the next write).
- [x] 22. `surveys.py`: removed the pre_s3 placeholder (pre = 2 sections);
      `_read_normalized` drops unknown columns only when they hold no data,
      so the retired pre3_* columns vanished after migration (76 -> 72 cols).
- [x] 23. README updated (grouped Excel layout, flat Google Sheets note,
      auto-migration).
- [x] 24. Verified: legacy file read OK -> one save migrated it; openpyxl
      structure check (A1:D1 PATIENT, E1:AR1 PRE-SURGERY, AS1:BT1
      POST-SURGERY, merged section titles in row 2, keys in row 3,
      P-0001 "test" at row 4); AppTest smoke on the new layout (create,
      HADS save A=21 stored as int, delete). Backup of the pre-migration
      file kept in the session scratchpad.

## Review (2026-07-09, post_s2 = HADS)
- `surveys.py`: `_HADS_ITEMS` table holds all 14 items verbatim in paper
  order with per-item (reply -> 0–3 score) maps (several items are
  reverse-displayed, so no global mapping is possible). `_hads_total()` /
  `_hads_level()` are compute-function factories for the 4 auto columns:
  `hads_anxiety_score/-level`, `hads_depression_score/-level`
  (0–7 Normal · 8–10 Borderline abnormal · 11–21 Abnormal (case)).
  Scores return "" until every item of that subscale is answered.
- `core.py`: `to_cell` passes computed values through unchanged so scores
  land in Excel as real numbers (verified via openpyxl: int 21, not "21").
- Verified: item-table integrity (14 items, 7A+7D, each scoring {0,1,2,3}),
  min/max/borderline/abnormal thresholds, reverse-scored items
  ('Definitely' = 0 on item 7 but 3 on item 10), AppTest e2e:
  A-items maxed + D-items zeroed -> A=21 Abnormal, D=0 Normal, complete.
- Spreadsheet now 76 columns. README field-type docs updated.
- Remaining: Pre-Surgery Section 2 (pending from user) + remove pre_s3
  placeholder once pre structure is final.
- BUGFIX (user report: "scores taking too much time after saving"): the
  computed fields saved correctly but the on-screen widget kept its stale
  empty value after save+rerun (keyed widgets ignore a changed `value=`).
  Fix in `app.py:render_field`: sync `st.session_state[key]` before
  instantiating the read-only widget. Also added a post-rerun "Section
  saved ✅" toast (the old st.success was wiped by the immediate rerun).
  Verified: scores/verdict now display instantly after save (~430 ms
  round-trip). See tasks/lessons.md.
- UPDATE (user request, same day): HADS now mirrors the paper visibly —
  every reply is stored/displayed as "<score> — <text>" (e.g.
  "3 — Most of the time"), every question label ends with
  "· Column A (Anxiety)" or "· Column D (Depression)", and all four
  auto-score fields show the scoring key (0-7 Normal · 8-10 Borderline ·
  11-21 Abnormal). Re-verified: unit tests + AppTest e2e (A=21/D=0),
  reversed items still score correctly ("0 — Definitely" item 7 vs
  "3 — Definitely" item 10). Lesson recorded in tasks/lessons.md.

## Decisions made (with user, 2026-07-09)
- Pain VAS (0–10) sits at the end of Demographics (S1).
- Full name kept in the sheet; the auto `P-####` code is the anonymized
  research ID used in analysis.

## Review (2026-07-09)
- `app.py`: new `radio` type (horizontal, stored as string; `likert` stays
  numeric); `bool` now renders as horizontal Yes/No radio; **no widget is
  preselected anymore** (index=None) so unanswered ≠ first option; optional
  `"group"` key renders a divider + subheader inside the form; the
  "name required" error now looks up the DISPLAY_ID_FIELD label instead of
  assuming it is the first field (consent is first now).
- `surveys.py`: Demographics = 35 fields (23 required) in 6 groups: Consent,
  Personal information, Social & lifestyle, Medical history,
  Surgery & anesthesia, Financial, Pain. Conditional "specify" follow-ups are
  always-visible optional fields with "Only if …" help text (st.form cannot
  show/hide dynamically).
- Spreadsheet now has 55 columns; created automatically on next run.
- Verified via `streamlit.testing.v1.AppTest`: form fills, submits, creates
  P-0001 with `pre_s1_status=complete`; partial save gives `partial`.
