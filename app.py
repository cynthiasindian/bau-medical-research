# =============================================================================
#  app.py  ·  Streamlit UI
#
#  Pages:
#    1. Patient List      - searchable table + completion status
#    2. Pre-Surgery Survey- create new patient (Demographics) OR edit existing
#    3. Post-Surgery Survey - existing patients only
#
#  Run:  streamlit run app.py
# =============================================================================
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import core
import surveys
from storage import Storage

st.set_page_config(page_title="Surgical Survey Collector", page_icon="🩺", layout="wide")


# -----------------------------------------------------------------------------
# Storage is created once and cached for the session.
# -----------------------------------------------------------------------------
@st.cache_resource
def get_storage():
    return Storage(core.load_config())


storage = get_storage()


# -----------------------------------------------------------------------------
# Widget rendering: one field -> one Streamlit input -> a Python value.
# `disabled` is used for the overwrite-protection lock on completed sections.
# -----------------------------------------------------------------------------
def render_field(field, current, disabled=False, allow_blank=True):
    t = field["type"]
    label = field["label"] + (" *" if field.get("required") else "")
    help_ = field.get("help")
    key = f"w_{field['key']}"

    # A leading "" option on every choice widget lets a value be cleared again
    # (shown as "(no answer)"). Required-ness only drives completion status,
    # so an accidental click can always be reverted to unanswered.
    # Sections defined with "no_blank": True pass allow_blank=False: nothing is
    # preselected, but once answered a choice can only be changed, not unset.
    blank = [""] if allow_blank else []
    fmt = lambda o: "(no answer)" if o == "" else str(o)

    if t == "text":
        return st.text_input(label, value=current or "", help=help_,
                             disabled=disabled, key=key)
    if t == "textarea":
        return st.text_area(label, value=current or "", help=help_,
                            disabled=disabled, key=key)
    if t == "integer":
        return st.number_input(label, value=(None if current in (None, "") else int(current)),
                               min_value=field.get("min"), max_value=field.get("max"),
                               step=1, format="%d", help=help_, disabled=disabled, key=key)
    if t == "number":
        return st.number_input(label, value=(None if current in (None, "") else float(current)),
                               min_value=field.get("min"), max_value=field.get("max"),
                               help=help_, disabled=disabled, key=key)
    if t == "date":
        val = st.date_input(label, value=(current if isinstance(current, date) else None),
                            help=help_, disabled=disabled, key=key, format="YYYY-MM-DD")
        # Streamlit's date picker cannot be blanked once set — offer a clear.
        if isinstance(current, date) and not disabled:
            if st.checkbox("Clear this date on save", key=f"clear_{key}"):
                return None
        return val
    if t == "select":
        opts = blank + list(field["options"])
        # index=None -> nothing preselected; an unanswered question must not
        # silently record the first option.
        idx = opts.index(current) if current in opts else None
        return st.selectbox(label, opts, index=idx, format_func=fmt,
                            help=help_, disabled=disabled, key=key)
    if t in ("likert", "radio"):  # likert stores an int, radio stores a string
        opts = blank + list(field["options"])
        idx = opts.index(current) if current in opts else None
        return st.radio(label, opts, index=idx, format_func=fmt,
                        horizontal=field.get("horizontal", True),
                        help=help_, disabled=disabled, key=key)
    if t == "multiselect":
        return st.multiselect(label, field["options"], default=current or [],
                              help=help_, disabled=disabled, key=key)
    if t == "bool":
        opts = blank + ["Yes", "No"]
        idx = opts.index(current) if current in opts else None
        return st.radio(label, opts, index=idx, format_func=fmt, horizontal=True,
                        help=help_, disabled=disabled, key=key)
    if t == "computed":
        # Read-only: the value is derived from the other answers on save
        # (see the field's "compute" function in surveys.py).
        # Keyed widgets keep their old on-screen state across reruns and
        # ignore a changed `value` param, so sync the session value first —
        # otherwise a freshly saved score would never appear.
        st.session_state[key] = "" if current in (None, "") else str(current)
        return st.text_input(label, help=help_, disabled=True, key=key)

    raise ValueError(f"Unknown field type: {t}")


_STATUS_BADGE = {"complete": "✅ complete", "partial": "🟡 partial", "empty": "⬜ not started"}


def _reset_form_state(section):
    """Drop a section's widget session state so its form re-reads from
    storage on the next run. Keyed widgets otherwise keep stale on-screen
    values (e.g. a cleared date would reappear on the following save)."""
    for f in section["fields"]:
        st.session_state.pop(f"w_{f['key']}", None)
        st.session_state.pop(f"clear_w_{f['key']}", None)


def render_section_form(section, record, patient_id):
    """Render one section's form with save + overwrite protection.

    `record` is the patient's current row (dict of stored cell values).
    `patient_id` may be None only for a brand-new patient on Demographics.
    """
    if section.get("intro"):
        st.info(section["intro"])
    status = core.section_status(section, record) if record else "empty"
    st.caption(f"Status: {_STATUS_BADGE[status]}")

    # --- Overwrite protection: a completed section is locked until unlocked ---
    locked = False
    if status == "complete":
        locked = not st.checkbox(
            "This section is already complete — tick to enable editing.",
            key=f"unlock_{section['key']}_{patient_id}")

    with st.form(f"form_{section['key']}_{patient_id}"):
        values = {}
        group = None
        for field in section["fields"]:
            # Optional "group" key on a field starts a new visual subgroup.
            if field.get("group") and field["group"] != group:
                group = field["group"]
                st.divider()
                st.markdown(f"##### {group}")
            # Optional "doc": long text (e.g. the informed-consent form) in a
            # collapsible panel directly above the field it belongs to.
            if field.get("doc"):
                with st.expander(field.get("doc_title", "ℹ️ Information")):
                    st.markdown(field["doc"])
            current = core.from_cell(field, record.get(field["key"], "")) if record else None
            values[field["key"]] = render_field(field, current, disabled=locked,
                                                allow_blank=not section.get("no_blank"))
        submitted = st.form_submit_button("Save section", disabled=locked, type="primary")

    if not submitted:
        return None

    # --- Computed fields: overwrite with a fresh value derived from the -------
    # answers just entered (render_field only echoed the stored value).
    for f in section["fields"]:
        if f["type"] == "computed":
            values[f["key"]] = f["compute"](values)

    # --- Validate (type/range). Empty fields are allowed -> partial save. ----
    errors = [e for f in section["fields"]
              if (e := core.validate(f, values[f["key"]]))]
    if errors:
        for e in errors:
            st.error(e)
        return None

    cells = {f["key"]: core.to_cell(f, values[f["key"]]) for f in section["fields"]}
    return cells


# -----------------------------------------------------------------------------
# PAGE 1 — Patient list
# -----------------------------------------------------------------------------
def page_patient_list():
    st.header("Patient list")
    if deleted := st.session_state.pop("_deleted_flash", None):
        st.success(f"Patient **{deleted}** was permanently deleted.")
    records = storage.list_records()
    if not records:
        st.info("No patients yet. Go to **Pre-Surgery Survey** to add one.")
        return

    query = st.text_input("Search by hospital ID").strip().lower()

    rows = []
    for r in records:
        if query and query not in str(r.get("display_id", "")).lower() \
                and query not in str(r.get("patient_id", "")).lower():
            continue
        pre_done, pre_total = core.survey_progress(r, "pre")
        post_done, post_total = core.survey_progress(r, "post")
        rows.append({
            "Hospital ID": r.get("display_id", "") or r["patient_id"],
            "Pre": f"{pre_done}/{pre_total} done",
            "Post": f"{post_done}/{post_total} done",
            "Updated": r.get("updated_at", ""),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} patient(s) shown · storage backend: **{storage.backend_name}**")

    # --- D of CRUD: permanently remove a patient (explicit confirmation) -----
    with st.expander("🗑️ Delete a patient (permanent)"):
        pid = patient_picker("Patient to delete", key="del_pick")
        if pid:
            rec = storage.get_patient(pid)
            st.warning(f"This permanently deletes the patient with Hospital ID "
                       f"**{rec.get('display_id','') or pid}** and **all** of "
                       f"their pre- and post-surgery answers. "
                       f"This cannot be undone.")
            sure = st.checkbox("I understand this cannot be undone", key="del_sure")
            if st.button("Delete patient permanently", key="del_btn",
                         type="primary", disabled=not sure):
                storage.delete_patient(pid)
                st.session_state["_deleted_flash"] = rec.get("display_id", "") or pid
                st.session_state.pop("del_sure", None)
                st.rerun()


# -----------------------------------------------------------------------------
# Helpers for the survey pages
# -----------------------------------------------------------------------------
def patient_picker(label, key):
    """Selectbox of existing patients -> returns selected patient_id or None.
    Patients are listed by hospital ID (display_id); the internal P-#### code
    is shown only as a fallback / to disambiguate duplicates."""
    records = storage.list_records()
    if not records:
        return None
    options = {}
    for r in records:
        text = str(r.get("display_id", "")).strip() or r["patient_id"]
        if text in options:  # duplicate hospital ID -> disambiguate
            text = f'{text} ({r["patient_id"]})'
        options[text] = r["patient_id"]
    choice = st.selectbox(label, ["—"] + list(options.keys()), key=key)
    return options.get(choice)


def edit_existing_sections(patient_id, survey):
    """Show tabs for every section of `survey` for an existing patient."""
    record = storage.get_patient(patient_id)
    if record is None:
        st.error("Patient not found.")
        return
    st.success(f"Editing patient — Hospital ID: **{record.get('display_id','') or patient_id}**")

    # "Saved" feedback must survive the st.rerun() that follows a save.
    if flash := st.session_state.pop("_saved_flash", None):
        saved_title, saved_at = flash
        st.success(f"✅ **Saved** — *{saved_title}* was stored successfully "
                   f"at {saved_at}. No need to press Save again.")
        st.toast("Section saved ✅")

    secs = surveys.sections_for(survey)
    tabs = st.tabs([f'{s["title"]}' for s in secs])
    for tab, section in zip(tabs, secs):
        with tab:
            # Re-read inside each tab so status reflects the latest save.
            record = storage.get_patient(patient_id)
            missing = core.missing_required(section, record)
            if missing:
                st.warning("Required still missing: " + ", ".join(missing))
            cells = render_section_form(section, record, patient_id)
            if cells is not None:
                # Visible busy state: saving to Google Sheets takes a moment,
                # and a silent wait invites double-clicking Save.
                with st.spinner("Saving — please wait…"):
                    storage.save_section(patient_id, section["key"], cells)
                _reset_form_state(section)
                st.session_state["_saved_flash"] = (
                    section["title"], datetime.now().strftime("%H:%M:%S"))
                st.rerun()


# -----------------------------------------------------------------------------
# PAGE 2 — Pre-surgery survey (new patient OR edit existing)
# -----------------------------------------------------------------------------
def page_pre_survey():
    st.header("Pre-surgery survey")

    mode = st.radio("Patient", ["➕ New patient", "Existing patient"], horizontal=True)

    if mode == "➕ New patient":
        if flash := st.session_state.pop("_created_flash", None):
            hosp_id, missing = flash
            st.success(f"Created patient — Hospital ID: **{hosp_id}**. "
                       f"Switch to 'Existing patient' to complete the remaining sections.")
            if missing:
                st.warning(f"⚠️ Demographics saved as **partial** — it only counts "
                           f"as *done* in the patient list once every required (*) "
                           f"field is answered. Still missing ({len(missing)}): "
                           + ", ".join(missing))
        st.subheader("Demographics — creates the patient record")
        demo = surveys.get_section("pre_s1")
        # Empty record so the form renders blank fields for a new patient.
        cells = render_section_form(demo, core.empty_record(), patient_id=None)
        if cells is not None:
            # A name is required to create a patient (it becomes the identifier).
            if core._is_blank(cells.get(surveys.DISPLAY_ID_FIELD, "")):
                name_label = next(f["label"] for f in demo["fields"]
                                  if f["key"] == surveys.DISPLAY_ID_FIELD)
                st.error(f"'{name_label}' is required to create a patient.")
                return
            with st.spinner("Creating patient — please wait…"):
                storage.create_patient(cells)
            # Blank the form so the next patient doesn't inherit these answers
            # (also prevents a double-click from creating a duplicate).
            _reset_form_state(demo)
            st.session_state["_created_flash"] = (
                str(cells.get(surveys.DISPLAY_ID_FIELD, "")).strip(),
                core.missing_required(demo, cells))
            st.rerun()
        return

    # Existing patient -> edit any of the pre sections
    pid = patient_picker("Select a patient", key="pre_pick")
    if pid:
        edit_existing_sections(pid, "pre")


# -----------------------------------------------------------------------------
# PAGE 3 — Post-surgery survey (existing patients only)
# -----------------------------------------------------------------------------
def page_post_survey():
    st.header("Post-surgery survey")
    st.caption("Available only for patients already created in the pre-surgery survey.")
    pid = patient_picker("Select an existing patient", key="post_pick")
    if pid:
        edit_existing_sections(pid, "post")


# -----------------------------------------------------------------------------
# Navigation
# -----------------------------------------------------------------------------
PAGES = {
    "Patient list": page_patient_list,
    "Pre-surgery survey": page_pre_survey,
    "Post-surgery survey": page_post_survey,
}

_LOGO = Path(__file__).parent / "logo.png"
if _LOGO.exists():
    st.sidebar.image(str(_LOGO), width="stretch")
st.sidebar.title("🩺 Survey Collector")
choice = st.sidebar.radio("Go to", list(PAGES.keys()))
st.sidebar.divider()
st.sidebar.caption(f"Storage: **{storage.backend_name}**")
PAGES[choice]()
