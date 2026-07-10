# =============================================================================
#  core.py  ·  schema, value conversion, completion-status engine, validation
#  (No Streamlit and no spreadsheet I/O here — pure, testable logic.)
# =============================================================================
import math
import re
from datetime import date, datetime
from pathlib import Path

import surveys

# ---- TOML reader (stdlib on 3.11+, 'tomli' fallback on older) ---------------
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
def load_config(path="config.toml"):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


# -----------------------------------------------------------------------------
# Spreadsheet schema (the canonical column order, generated from surveys.py)
#
# Layout is chosen so a human can read one patient's full pre+post data on one
# row, with each section's status column sitting right before its answers:
#
#   patient_id | display_id | created_at | updated_at |
#   pre_s1_status | <demographics...> |
#   pre_s2_status | <pre §2...> | pre_s3_status | <pre §3...> |
#   post_s1_status | <post §1...> | post_s2_status | <post §2...>
# -----------------------------------------------------------------------------
META_COLS = ["patient_id", "display_id", "created_at", "updated_at"]


def status_col(section_key):
    return f"{section_key}_status"


def build_columns():
    cols = list(META_COLS)
    for section in surveys.SECTIONS:
        cols.append(status_col(section["key"]))
        cols.extend(f["key"] for f in section["fields"])
    return cols


COLUMNS = build_columns()


# -----------------------------------------------------------------------------
# Patient ID generation  ·  sequential, human-readable: P-0001, P-0002, ...
# -----------------------------------------------------------------------------
def next_patient_id(existing_ids):
    nums = []
    for pid in existing_ids:
        m = re.match(r"P-(\d+)$", str(pid).strip())
        if m:
            nums.append(int(m.group(1)))
    nxt = (max(nums) + 1) if nums else 1
    return f"P-{nxt:04d}"


# -----------------------------------------------------------------------------
# Value conversion between a Python form value and what we store in the cell.
# We keep cells human-readable (dates as ISO, booleans as Yes/No,
# multi-selects joined by "; ").
# -----------------------------------------------------------------------------
def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, (list, tuple)) and len(value) == 0:
        return True
    return str(value).strip() == ""


def to_cell(field, value):
    """Python form value  ->  value written to the spreadsheet cell."""
    if _is_blank(value):
        return ""
    t = field["type"]
    if t == "multiselect":
        return "; ".join(str(v) for v in value)
    if t == "date":
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if t in ("integer", "likert"):
        return int(value)
    if t == "number":
        return float(value)
    if t == "computed":
        return value  # already a final cell value (may be numeric, e.g. a score)
    # text, textarea, select, bool ("Yes"/"No") are stored as-is
    return str(value)


def from_cell(field, raw):
    """Spreadsheet cell value  ->  Python value used to pre-fill the form."""
    t = field["type"]
    if _is_blank(raw):
        return [] if t == "multiselect" else None
    if t == "multiselect":
        return [x.strip() for x in str(raw).split(";") if x.strip()]
    if t == "date":
        return date.fromisoformat(str(raw)[:10])
    if t in ("integer", "likert"):
        return int(float(raw))            # float() guards "3.0" coming from Excel
    if t == "number":
        return float(raw)
    return str(raw)


# -----------------------------------------------------------------------------
# Completion-status engine (powers partial-save/resume and the "2/3 done" view)
#   empty    -> no field in the section has any value
#   partial  -> some values present, but a required field is still missing
#   complete -> every required field is filled
# -----------------------------------------------------------------------------
def _has_value(record, key):
    return not _is_blank(record.get(key, ""))


def section_status(section, record):
    fields = section["fields"]
    if not any(_has_value(record, f["key"]) for f in fields):
        return "empty"
    required = [f for f in fields if f.get("required")]
    if all(_has_value(record, f["key"]) for f in required):
        return "complete"
    return "partial"


def missing_required(section, record):
    """Return labels of required fields that are still empty (for user hints)."""
    return [f["label"] for f in section["fields"]
            if f.get("required") and not _has_value(record, f["key"])]


def survey_progress(record, survey):
    """Return (#complete, #total) of sections for 'pre' or 'post'."""
    secs = surveys.sections_for(survey)
    done = sum(1 for s in secs
               if record.get(status_col(s["key"]), "") == "complete")
    return done, len(secs)


# -----------------------------------------------------------------------------
# Validation  ·  type/range checks. Required fields are NOT hard-blocked here so
# that a half-finished section can still be saved (partial save). Missing
# required fields simply keep the section in the "partial" state.
# -----------------------------------------------------------------------------
def validate(field, value):
    """Return an error string, or None if the value is acceptable."""
    if _is_blank(value):
        return None  # empty is allowed (partial save) -> affects status only
    t = field["type"]
    if t in ("integer", "number"):
        try:
            num = float(value)
        except (TypeError, ValueError):
            return f"{field['label']}: must be a number."
        if "min" in field and num < field["min"]:
            return f"{field['label']}: must be ≥ {field['min']}."
        if "max" in field and num > field["max"]:
            return f"{field['label']}: must be ≤ {field['max']}."
    return None


# -----------------------------------------------------------------------------
# Misc
# -----------------------------------------------------------------------------
def now_stamp():
    return datetime.now().isoformat(timespec="seconds")


def empty_record():
    return {c: "" for c in COLUMNS}
