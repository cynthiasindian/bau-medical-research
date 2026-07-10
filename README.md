# Surgical Survey Collector

A small, reliable web app for a medical research team. Med students use it to
collect **pre-** and **post-operative** survey data from surgical patients.
Each patient is **one row** in a spreadsheet, with pre- and post-surgery data
sitting **side by side** so the file is easy for a human to read.

- **Stack:** Python + Streamlit + pandas/openpyxl
- **Database:** a spreadsheet — local Excel `.xlsx` (default) **or** a Google Sheet
- **Patient IDs:** auto-generated, sequential (`P-0001`, `P-0002`, …)

---

## 1. Setup

Requires **Python 3.9+** (3.11+ recommended).

```bash
# from the project folder
python -m venv .venv

# activate it:
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Run

```bash
streamlit run app.py
```

Your browser opens at `http://localhost:8501`. On first run with the Excel
backend, `data/patients.xlsx` is created automatically.

---

## 3. How to use it

- **Patient list** — searchable table of everyone, showing `patient_id`, name,
  and completion status (e.g. `Pre: 2/3 done`, `Post: 0/2 done`).
- **Pre-surgery survey**
  - *New patient* → fill **Demographics** (Section 1). Saving creates the
    patient and auto-assigns a `patient_id`.
  - *Existing patient* → open them and complete/edit Sections 2 & 3.
- **Post-surgery survey** — pick an existing patient and fill Sections 1 & 2.

**Partial save & resume:** save any section at any time. A section becomes
`complete` only when all its required (`*`) fields are filled; otherwise it
stays `partial` and the app shows what's still missing. Nothing is lost when you
leave and come back.

**Overwrite protection:** a section marked `complete` is locked. To change it,
tick *"enable editing"* first — this prevents accidental overwrites.

---

## 4. Switching from Excel to a Google Sheet

Edit `config.toml`:

```toml
[storage]
backend = "google_sheets"
```

Then set up service-account access:

1. In Google Cloud Console, create a **service account** and enable the
   **Google Sheets API** and **Google Drive API**.
2. Create a **JSON key** for it and save it as `service_account.json` in this
   folder (or point `service_account_file` to its path).
3. Create a Google Sheet. Copy its **ID** from the URL
   (`https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`).
4. **Share** the Sheet with the service-account email (the `client_email` in the
   JSON), giving it **Editor** access.
5. Fill in `config.toml`:

```toml
[google_sheets]
spreadsheet_id = "THE_ID_FROM_THE_URL"
worksheet_name = "patients"
service_account_file = "service_account.json"
```

The columns are the same as the Excel version, but the Google Sheet uses a
flat single header row, while the Excel file uses a grouped 4-row header:
row 1 = merged survey banners (PATIENT / PRE-SURGERY / POST-SURGERY),
row 2 = merged section titles, row 3 = the full question text, row 4 = the
field headers, and patient data starts at row 5. Files in the older layouts
are migrated automatically the next time data is saved. (Don't commit
`service_account.json` to source control.)

---

## 5. Editing the survey questions

All questions live in **one file: `surveys.py`**. Nothing else needs to change.

Each field looks like:

```python
{"key": "pre2_pain", "label": "Pain level", "type": "likert",
 "required": True, "options": [1, 2, 3, 4, 5]}
```

- `key` becomes the spreadsheet **column name** (lowercase, unique, no spaces).
- `type` is one of: `text`, `textarea`, `integer`, `number`, `date`,
  `select`, `multiselect`, `likert`, `radio`, `bool`, `computed`.
- `required: True` fields determine when a section counts as **complete**.
- `select`/`multiselect`/`likert`/`radio` need an `options` list.
- `integer`/`number` accept optional `min`/`max`.
- `radio` shows one-tap buttons (add `"horizontal": False` for a vertical
  list); `likert` is the same but with numeric options, stored as a number.
- `computed` fields have no input — their value is derived from the section's
  other answers when saving, via the field's `compute` function (used for the
  Short CAM delirium verdict and the HADS scores).
- A field may set `"group": "Heading"` to start a visual subgroup; a section
  may set `"intro": "..."` to show an instruction banner above its form.

Just replace the `PLACEHOLDER` fields in Sections 2/3 (pre) and 1/2 (post) with
your real questions, then restart the app. New columns are added to the
spreadsheet automatically the next time data is saved.

> Tip: keep `key` names stable. Renaming a `key` creates a **new** column and
> the old answers stay under the old column name.

---

## 6. Backing up the data

- **Excel:** the entire database is the single file `data/patients.xlsx`. Copy
  it somewhere safe regularly (cloud drive, USB, etc.). To restore, just put the
  file back. You can also open it directly in Excel to read/analyze data — close
  it before saving in the app to avoid file-lock conflicts.
- **Google Sheets:** use **File → Make a copy** or **File → Version history** in
  Google Sheets for backups/restores.

---

## 7. Project structure

```
med-research/
├── app.py            # Streamlit UI (pages, forms, navigation)
├── surveys.py        # *** EDIT HERE *** all survey/section questions
├── core.py           # schema, value conversion, completion-status, validation
├── storage.py        # spreadsheet read/write (Excel + Google Sheets)
├── config.toml       # choose Excel vs Google Sheets
├── requirements.txt
├── README.md
└── data/
    └── patients.xlsx # created on first run (Excel backend)
```

---

## 8. Notes & limitations

- Designed for a **small team / low concurrency**. Writes are whole-sheet
  read-modify-write under a file lock, which is safe for a handful of users but
  not for hundreds of simultaneous editors.
- Keep the Excel file **closed** in Excel while students are entering data.
- The spreadsheet *is* the database — there is no separate DB to manage.
