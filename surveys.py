# =============================================================================
#  SURVEY DEFINITIONS  ---  *** THIS IS THE ONLY FILE YOU EDIT FOR QUESTIONS ***
# =============================================================================
#
#  How it works
#  ------------
#  * The whole app (spreadsheet columns, forms, validation, completion status)
#    is generated from the SECTIONS list below. Add / remove / reorder fields
#    here and everything else updates automatically.
#  * Pre-surgery survey  = 2 sections (Section 1 MUST be Demographics).
#  * Post-surgery survey = 2 sections.
#  * To plug in your real questions, just replace the PLACEHOLDER fields.
#
#  Each field is a dict:
#    key       : column name in the spreadsheet (lowercase, no spaces). UNIQUE.
#    label     : question text shown to the user.
#    type      : one of -> "text", "textarea", "integer", "number", "date",
#                          "select", "multiselect", "likert", "radio", "bool",
#                          "computed"
#                 ("radio" = one-tap buttons, stored as text; add
#                  "horizontal": False for a vertical list;
#                  "likert" = same look but numeric options, stored as int;
#                  "computed" = read-only, derived from the section's other
#                  answers on save via the field's "compute" function)
#    group     : optional subgroup heading rendered above the field when it
#                differs from the previous field's group.
#    doc       : optional long markdown text rendered in a collapsible
#                expander directly above the field's widget (used for the
#                informed-consent form). "doc_title" sets the expander label.
#
#  A section may also have an "intro" string, shown as an info banner above
#  its form, and "no_blank": True to drop the "(no answer)" choice from its
#  select/radio/likert/bool widgets (an answer can then no longer be unset).
#    required  : True/False. Required fields decide when a section is "complete".
#    options   : list of choices. REQUIRED for select / multiselect / likert.
#    min / max : numeric bounds (optional, for integer / number).
#    help      : small hint text under the field (optional).
#
#  Naming convention for keys (keeps the spreadsheet readable):
#    demo_*  -> Demographics (Pre §1)
#    pre2_*  -> Pre §2        pre3_* -> Pre §3
#    post1_* -> Post §1       post2_* -> Post §2
# =============================================================================

# The field whose value identifies the patient in the list / search / pickers
# (the hospital ID — the auto-generated P-#### code stays the internal key).
# It must be one of the keys in the Demographics section below.
DISPLAY_ID_FIELD = "demo_hospital_id"


# -----------------------------------------------------------------------------
# Informed Consent Form [Form H-V(A)] — text verbatim from "Consent Form.docx".
# Shown in a collapsible panel above the consent question; answering "Yes"
# to that question is the participant's signature. (The docx's empty sections
# "Alternatives to participation" / "If you are harmed" are omitted.)
# -----------------------------------------------------------------------------
_CONSENT_DOC = """
**Principal Investigator:** Nariman Salem\\
**Study Title:** Postoperative Anxiety and Delirium in General, Regional and Monitored Anesthesia Care\\
**Date:** 01/4/2026

##### PURPOSE OF RESEARCH STUDY
The purpose of the study is to understand the relation between postoperative \
anxiety and postoperative delirium in 3 different types of anesthesia in the \
Lebanese hospital settings. By participating in this research, you will be \
helping us conclude if there is an association between these variables in \
Lebanon.

We anticipate that approximately 400 participants in this study.

##### PROCEDURES
You are asked to fill out a questionnaire provided by the research team. The \
estimated time to complete it is 10 minutes. In case a question is not clear, \
you can ask the present team members to explain it to you.

##### RISKS/DISCOMFORTS
The risks associated with participation in this study are no greater than \
those encountered in daily life or during the performance of routine physical \
or psychological examinations or tests.

##### BENEFITS
There are no direct benefits to you from participating in this study.

This study can benefit the medical community, by approaching the patients' \
anxiety and delirium postoperatively, optimizing anesthesia practice and \
improving perioperative patient care.

##### VOLUNTARY PARTICIPATION AND RIGHT TO WITHDRAW
Your participation in this study is entirely voluntary. You choose whether to \
participate or not to participate, there are no penalties, and you will not \
lose any benefits to which you would otherwise be entitled.

##### CIRCUMSTANCES THAT COULD LEAD US TO END YOUR PARTICIPATION
Under certain circumstances we may decide to end your participation before \
you have completed the survey. Specifically, we may stop your participation \
if we find that you do not fit the criteria set for this study.

##### CONFIDENTIALITY
Any study records that identify you will be kept confidential. The records \
from your participation may be reviewed by people responsible for making sure \
that research is done properly, including members of the BAU Institutional \
Review Board. All of these people are required to keep your identity \
confidential. Otherwise, records that identify you will be available only to \
people working on the study, unless you give permission for other people to \
see the records.

The study records will be created, stored, and maintained to protect \
confidential information (e.g., use of code numbers rather than participants' \
names on data sheets, keeping records in a safe place).

##### COMPENSATION
You will not receive any payment or other compensation for participating in \
this study.

##### IF YOU HAVE QUESTIONS OR CONCERNS
You can ask questions to the researcher(s) working with you or call: \
Dr Nariman Salem, Beirut Arab University, Hariri Building on 01 300110 \
Ex: 2791.

If you have questions about your rights as a research participant or feel \
that you have not been treated fairly, please call the BAU Institutional \
Review Board at 00961 1 300110 ext. 2743 or 2689.

##### STATEMENT BY THE RESEARCHER / PERSON TAKING CONSENT
I have accurately read out the information sheet to the potential \
participant, and to the best of my ability made sure that the participant \
understands the information in this consent form. I confirm that the \
participant was given an opportunity to ask questions about the study, and \
all the questions asked by the participant have been answered correctly and \
to the best of my ability. I confirm that the individual has not been coerced \
into giving consent, and the consent has been given freely and voluntarily.

##### WHAT YOUR SIGNATURE MEANS
Your signature below means that you understand the information in this \
consent form.

Your signature also means that you agree to participate in the study.
"""


def _cam_delirium(values):
    """Short CAM diagnostic algorithm (verbatim rule from the worksheet):
    'If Inattention and at least one other item in Box 1 are checked and at
    least one item in Box 2 is checked a diagnosis of delirium is suggested.'
    Box 1 = acute change (Ia), fluctuation (Ib), inattention (II).
    Box 2 = disorganized thinking (III), any consciousness level other than
    Alert (IV). Returns "" until all five answers are present.
    """
    v = {k: values.get(k) for k in ("cam_1a", "cam_1b", "cam_2", "cam_3", "cam_4")}
    if any(x in (None, "") for x in v.values()):
        return ""
    box1_other = v["cam_1a"] == "Yes" or v["cam_1b"] == "Yes"
    box2 = v["cam_3"] == "Yes" or not str(v["cam_4"]).startswith("Alert")
    return "Yes" if (v["cam_2"] == "Yes" and box1_other and box2) else "No"


def _pack_years(values):
    """Pack years = cigarettes per day / 20 * years smoked.
    Returns "" until both smoker questions are answered."""
    cpd = values.get("demo_cigs_per_day")
    yrs = values.get("demo_smoking_years")
    if cpd in (None, "") or yrs in (None, ""):
        return ""
    return round(float(cpd) / 20 * float(yrs), 1)


def _pain_category(values):
    """Classify the 0-10 pain score: 0 no pain, 1-3 mild, 4-6 moderate,
    7-10 severe. Returns "" until the score is selected."""
    score = values.get("demo_pain_score")
    if score in (None, ""):
        return ""
    score = int(score)
    if score == 0:
        return "No pain (0)"
    if score <= 3:
        return "Mild pain (1-3)"
    if score <= 6:
        return "Moderate pain (4-6)"
    return "Severe pain (7-10)"


# -----------------------------------------------------------------------------
# HADS — Hospital Anxiety and Depression Scale (source: HADS-PDF.pdf).
# 14 items in the paper's order; the Anxiety/Depression interleaving is
# deliberate (patients should not see the subscales) — do not reorder.
# Each item: (key, subscale "A"/"D", question, [(reply text, score), ...])
# with replies listed in the paper's display order (several are reversed,
# which is why every item carries its own text->score map).
# -----------------------------------------------------------------------------
_HADS_ITEMS = [
    ("hads_1", "A", "I feel tense or 'wound up':",
     [("Most of the time", 3), ("A lot of the time", 2),
      ("From time to time, occasionally", 1), ("Not at all", 0)]),
    ("hads_2", "D", "I still enjoy the things I used to enjoy:",
     [("Definitely as much", 0), ("Not quite so much", 1),
      ("Only a little", 2), ("Hardly at all", 3)]),
    ("hads_3", "A", "I get a sort of frightened feeling as if something awful "
                    "is about to happen:",
     [("Very definitely and quite badly", 3), ("Yes, but not too badly", 2),
      ("A little, but it doesn't worry me", 1), ("Not at all", 0)]),
    ("hads_4", "D", "I can laugh and see the funny side of things:",
     [("As much as I always could", 0), ("Not quite so much now", 1),
      ("Definitely not so much now", 2), ("Not at all", 3)]),
    ("hads_5", "A", "Worrying thoughts go through my mind:",
     [("A great deal of the time", 3), ("A lot of the time", 2),
      ("From time to time, but not too often", 1), ("Only occasionally", 0)]),
    ("hads_6", "D", "I feel cheerful:",
     [("Not at all", 3), ("Not often", 2),
      ("Sometimes", 1), ("Most of the time", 0)]),
    ("hads_7", "A", "I can sit at ease and feel relaxed:",
     [("Definitely", 0), ("Usually", 1),
      ("Not Often", 2), ("Not at all", 3)]),
    ("hads_8", "D", "I feel as if I am slowed down:",
     [("Nearly all the time", 3), ("Very often", 2),
      ("Sometimes", 1), ("Not at all", 0)]),
    ("hads_9", "A", "I get a sort of frightened feeling like 'butterflies' "
                    "in the stomach:",
     [("Not at all", 0), ("Occasionally", 1),
      ("Quite Often", 2), ("Very Often", 3)]),
    ("hads_10", "D", "I have lost interest in my appearance:",
     [("Definitely", 3), ("I don't take as much care as I should", 2),
      ("I may not take quite as much care", 1),
      ("I take just as much care as ever", 0)]),
    ("hads_11", "A", "I feel restless as I have to be on the move:",
     [("Very much indeed", 3), ("Quite a lot", 2),
      ("Not very much", 1), ("Not at all", 0)]),
    ("hads_12", "D", "I look forward with enjoyment to things:",
     [("As much as I ever did", 0), ("Rather less than I used to", 1),
      ("Definitely less than I used to", 2), ("Hardly at all", 3)]),
    ("hads_13", "A", "I get sudden feelings of panic:",
     [("Very often indeed", 3), ("Quite often", 2),
      ("Not very often", 1), ("Not at all", 0)]),
    ("hads_14", "D", "I can enjoy a good book or radio or TV program:",
     [("Often", 0), ("Sometimes", 1),
      ("Not often", 2), ("Very seldom", 3)]),
]

_HADS_HELP = ("0-7 = Normal · 8-10 = Borderline abnormal (borderline case) · "
              "11-21 = Abnormal (case)")

_HADS_SUBSCALE = {"A": "Anxiety", "D": "Depression"}


def _hads_option(text, score):
    """Reply as displayed AND stored: score label first, like on the paper."""
    return f"{score} — {text}"


def _hads_key(base, prefix):
    """Map a base item key onto a section's column prefix:
    ('hads_3', 'hads')     -> 'hads_3'      (post-surgery, original columns)
    ('hads_3', 'hads_pre') -> 'hads_pre_3'  (pre-surgery copy)"""
    return prefix + base[len("hads"):]


def _hads_total(subscale, prefix="hads"):
    """Compute-function factory: total score of one subscale ("A" or "D").
    Returns "" until every item of that subscale is answered."""
    def compute(values):
        total = 0
        for key, sub, _label, opts in _HADS_ITEMS:
            if sub != subscale:
                continue
            score = {_hads_option(t, s): s for t, s in opts}.get(
                values.get(_hads_key(key, prefix)))
            if score is None:
                return ""
            total += score
        return total
    return compute


def _hads_level(subscale, prefix="hads"):
    """Compute-function factory: Normal/Borderline/Abnormal interpretation."""
    def compute(values):
        total = _hads_total(subscale, prefix)(values)
        if total == "":
            return ""
        if total <= 7:
            return "Normal"
        if total <= 10:
            return "Borderline abnormal (borderline case)"
        return "Abnormal (case)"
    return compute


def _hads_fields(prefix="hads", subscales=("A", "D")):
    """The HADS items (verbatim, paper order) + auto-scored fields.
    As on the paper: every reply carries its 0-3 score label, and every
    question shows the column it belongs to (A = Anxiety, D = Depression).
    The same instrument is used pre- and post-surgery; `prefix` keeps each
    administration in its own spreadsheet columns. `subscales` limits which
    columns are administered (the pre-surgery form uses only "A" — the
    depression items are not asked before surgery); items are renumbered
    over what is shown.
    """
    items = [it for it in _HADS_ITEMS if it[1] in subscales]
    fields = [
        {"key": _hads_key(key, prefix),
         "label": f"{i}. {label}  ·  Column {sub} ({_HADS_SUBSCALE[sub]})",
         "type": "radio", "horizontal": False, "required": True,
         "options": [_hads_option(text, score) for text, score in opts]}
        for i, (key, sub, label, opts) in enumerate(items, start=1)
    ]
    scores = []
    if "A" in subscales:
        scores += [
            {"key": f"{prefix}_anxiety_score",
             "label": "Total score: Anxiety (A)", "type": "computed",
             "required": False, "compute": _hads_total("A", prefix), "help": _HADS_HELP},
            {"key": f"{prefix}_anxiety_level", "label": "Anxiety (A) — interpretation",
             "type": "computed", "required": False, "compute": _hads_level("A", prefix),
             "help": _HADS_HELP},
        ]
    if "D" in subscales:
        scores += [
            {"key": f"{prefix}_depression_score",
             "label": "Total score: Depression (D)", "type": "computed",
             "required": False, "compute": _hads_total("D", prefix), "help": _HADS_HELP},
            {"key": f"{prefix}_depression_level",
             "label": "Depression (D) — interpretation", "type": "computed",
             "required": False, "compute": _hads_level("D", prefix), "help": _HADS_HELP},
        ]
    scores[0]["group"] = "Scores (auto-calculated on save)"
    return fields + scores


SECTIONS = [
    # -------------------------------------------------------------------------
    # PRE-SURGERY  ·  SECTION 1  ·  DEMOGRAPHICS  (creates a new patient)
    # Source: "Survey copy.docx" — BAU study "Postoperative Anxiety and
    # Delirium in General, Regional and MAC Anesthesia" (PI: Dr. Nariman Salem)
    # -------------------------------------------------------------------------
    {
        "key": "pre_s1",
        "survey": "pre",
        "number": 1,
        "title": "Demographics",
        "no_blank": True,   # per protocol: no "(no answer)" choice pre-surgery
        "fields": [
            # ---- Consent -----------------------------------------------------
            {"key": "demo_consent", "group": "Consent",
             "doc_title": "📄 Informed Consent Form [Form H-V(A)] — tap to "
                          "read before signing",
             "doc": _CONSENT_DOC,
             "label": "Informed consent form signed by the patient",
             "type": "bool", "required": True,
             "help": "Answering 'Yes' is the participant's signature: it "
                     "means they understand the information in the consent "
                     "form above and agree to participate in the study."},

            # ---- Personal information ----------------------------------------
            {"key": "demo_hospital_id", "group": "Personal information",
             "label": "Hospital ID", "type": "text", "required": True,
             "help": "The patient's hospital ID — shown in the patient list "
                     "and used to find the patient for the post-surgery "
                     "survey."},
            {"key": "demo_phone", "label": "Contact number", "type": "text",
             "required": False,
             "help": "Optional — for arranging the post-surgery follow-up."},
            {"key": "demo_gender", "label": "Gender", "type": "radio",
             "required": True, "options": ["Male", "Female"]},
            {"key": "demo_age_group", "label": "Age", "type": "select",
             "required": True,
             "options": ["18-29", "30-39", "40-49", "50-59", "60 or above"]},
            {"key": "demo_bmi", "label": "BMI", "type": "select",
             "required": True,
             "options": ["<18.5 (underweight)",
                         "18.5-24.9 (Normal weight)",
                         "25.0-29.9 (overweight)",
                         "30.0-34.9 (obesity class I)",
                         "35.0-39.9 (obesity class II)",
                         "40 or above (obesity class III)"]},
            {"key": "demo_nationality", "label": "Nationality", "type": "select",
             "required": True,
             "options": ["Lebanese", "Palestinian", "Syrian", "Other"]},
            {"key": "demo_nationality_other",
             "label": "Nationality — specify", "type": "text",
             "required": False, "help": "Only if nationality is 'Other'."},
            {"key": "demo_residence", "label": "Area of residence",
             "type": "select", "required": True,
             "options": ["Akkar", "Baalbek-Hermel", "Beirut", "Beqaa",
                         "Keserwan-Jbeil", "Mount Lebanon", "Nabatiyeh",
                         "North", "South"]},
            {"key": "demo_marital_status", "label": "What is your marital status?",
             "type": "select", "required": True,
             "options": ["Single", "Married", "Widowed", "Divorced", "Separated"]},

            # ---- Social & lifestyle ------------------------------------------
            {"key": "demo_smoking_status", "group": "Social & lifestyle",
             "label": "Smoking status (cigarettes, shisha…)",
             "type": "radio", "required": True,
             "options": ["Non smoker", "Former smoker",
                         "Current occasional smoker", "Current daily smoker"]},
            {"key": "demo_cigs_per_day",
             "label": "How many cigarettes do you smoke per day?",
             "type": "integer", "required": False, "min": 0, "max": 200,
             "help": "Only if a current (occasional or daily) smoker."},
            {"key": "demo_smoking_years",
             "label": "For how many years have you smoked?",
             "type": "integer", "required": False, "min": 0, "max": 100,
             "help": "Only if a current (occasional or daily) smoker."},
            {"key": "demo_pack_years",
             "label": "Pack years (auto-calculated on save)",
             "type": "computed", "required": False, "compute": _pack_years,
             "help": "Cigarettes per day ÷ 20 × years smoked."},
            {"key": "demo_alcohol_48h",
             "label": "Did you consume alcohol in the last 48 hours?",
             "type": "bool", "required": True},
            {"key": "demo_drugs_48h",
             "label": "Did you use any drugs in the last 48 hours?",
             "type": "bool", "required": True},
            {"key": "demo_education", "label": "What is your level of education?",
             "type": "radio", "required": True,
             "options": ["Not educated", "High school education",
                         "University education or higher"]},
            {"key": "demo_employment", "label": "What is your employment status?",
             "type": "radio", "required": True,
             "options": ["Employed", "Not employed", "Retired"]},
            {"key": "demo_employment_cause",
             "label": "Employment — specify the cause", "type": "text",
             "required": False, "help": "Only if 'Not employed' or 'Retired'."},
            {"key": "demo_healthcare_profession",
             "label": "Are you involved in any healthcare-related profession?",
             "type": "bool", "required": True},

            # ---- Medical history ---------------------------------------------
            {"key": "demo_chronic_illness", "group": "Medical history",
             "label": "Do you have a history of chronic illness?",
             "type": "bool", "required": True},
            {"key": "demo_chronic_conditions",
             "label": "Chronic illness — select all that apply",
             "type": "multiselect", "required": False,
             "options": ["Hypertension", "Diabetes Mellitus",
                         "Cardiovascular Disease", "CKD", "COPD",
                         "History of cancer", "Other"],
             "help": "Only if the previous answer is 'Yes'."},
            {"key": "demo_chronic_other",
             "label": "Other chronic illness — specify", "type": "text",
             "required": False},
            {"key": "demo_psych_diagnosis",
             "label": "Have you ever been diagnosed with any of the following "
                      "by a healthcare professional? (select all that apply)",
             "type": "multiselect", "required": True,
             "options": ["Depression", "Anxiety",
                         "Other psychiatric disorder", "None"]},
            {"key": "demo_psych_other",
             "label": "Other psychiatric disorder — specify", "type": "text",
             "required": False},
            {"key": "demo_psych_medications",
             "label": "If diagnosed — are you currently on medications for it?",
             "type": "radio", "required": False, "options": ["Yes", "No"],
             "help": "Skip if the answer above is 'None'."},
            {"key": "demo_current_medications",
             "label": "Are you currently taking any medications?",
             "type": "bool", "required": True},
            {"key": "demo_current_medications_list",
             "label": "Current medications — specify", "type": "text",
             "required": False, "help": "Only if 'Yes'."},
            {"key": "demo_previous_surgeries",
             "label": "Did you have any previous surgeries?",
             "type": "bool", "required": True},
            {"key": "demo_postop_complications",
             "label": "Have you experienced any postoperative complications?",
             "type": "radio", "required": False, "options": ["Yes", "No"],
             "help": "Only if you had previous surgeries."},
            {"key": "demo_postop_complications_spec",
             "label": "Postoperative complications — specify", "type": "text",
             "required": False},
            {"key": "demo_delirium_history",
             "label": "Were you told by a healthcare professional that you "
                      "experienced postoperative confusion or delirium?",
             "type": "radio", "required": False,
             "options": ["Yes", "No", "Not sure"],
             "help": "Only if you had previous surgeries."},

            # ---- Surgery & anesthesia ----------------------------------------
            {"key": "demo_preop_anxiety", "group": "Surgery & anesthesia",
             "label": "Are you experiencing feelings of anxiety or nervousness "
                      "before the surgery?",
             "type": "bool", "required": True},
            {"key": "demo_surgery_type", "label": "Type of current surgery",
             "type": "radio", "required": True, "options": ["Minor", "Major"]},
            {"key": "demo_anesthesia_types_familiar",
             "label": "Are you familiar with the types of anesthesia in general?",
             "type": "bool", "required": True},
            {"key": "demo_anesthesia_current_familiar",
             "label": "Are you familiar with the type of anesthesia for the "
                      "current surgery?",
             "type": "bool", "required": True},
            {"key": "demo_anesthesia_type",
             "label": "What is the type of anesthesia for the current surgery?",
             "type": "radio", "required": True,
             "options": ["General", "Regional (Spinal/Epidural)",
                         "Monitored (MAC)"]},

            # ---- Financial ----------------------------------------------------
            {"key": "demo_payment", "group": "Financial",
             "label": "The operation is covered financially by",
             "type": "radio", "required": True,
             "options": ["Own expenses", "Insurance companies", "Others"]},
            {"key": "demo_income", "label": "What is your average income level?",
             "type": "radio", "required": True,
             "options": ["Low", "Medium", "High"]},

            # ---- Pain ---------------------------------------------------------
            {"key": "demo_pain_score", "group": "Pain",
             "label": "Select from the options below to indicate how bad "
                      "you feel your pain is",
             "type": "likert", "required": True,
             "options": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
             "help": "0 = no pain · 1-3 = mild · 4-6 = moderate · "
                     "7-10 = severe"},
            {"key": "demo_pain_category",
             "label": "Pain category (auto-calculated on save)",
             "type": "computed", "required": False, "compute": _pain_category,
             "help": "0 = no pain · 1-3 = mild pain · 4-6 = moderate pain · "
                     "7-10 = severe pain"},
        ],
    },

    # -------------------------------------------------------------------------
    # PRE-SURGERY  ·  SECTION 2  ·  HADS (Anxiety items only)
    # Same instrument as Post-Surgery Section 2 but restricted to the seven
    # Column A items — the depression (Column D) questions are not asked
    # before surgery. Stored in its own hads_pre_* columns so pre and post
    # scores sit side by side.
    # -------------------------------------------------------------------------
    {
        "key": "pre_s2",
        "survey": "pre",
        "number": 2,
        "title": "Hospital Anxiety and Depression Scale (HADS)",
        "no_blank": True,   # per protocol: no "(no answer)" choice pre-surgery
        "intro": "Tick the reply that is closest to how you have been feeling "
                 "in the past week. Don't take too long over your replies: "
                 "your immediate is best.",
        "fields": _hads_fields("hads_pre", subscales=("A",)),
    },

    # -------------------------------------------------------------------------
    # POST-SURGERY  ·  SECTION 1  ·  SHORT CAM WORKSHEET
    # Source: CAM-S_English.pdf — Short Confusion Assessment Method worksheet,
    # ©1999 Hospital Elder Life Program, LLC. Wording kept verbatim.
    # NOTE: identifies delirium cases only; it cannot produce a CAM-S
    # severity score (stated on the worksheet itself).
    # -------------------------------------------------------------------------
    {
        "key": "post_s1",
        "survey": "post",
        "number": 1,
        "title": "Delirium Assessment (Short CAM)",
        "no_blank": True,   # per protocol: no "(no answer)" choice
        "intro": "Short Confusion Assessment Method (Short CAM) Worksheet — "
                 "testing of orientation and sustained attention is "
                 "recommended prior to scoring, such as digit spans, days of "
                 "week, or months of year backwards. "
                 "©1999 Hospital Elder Life Program, LLC.",
        "fields": [
            # ---- Assessment info ----------------------------------------------
            {"key": "cam_evaluator", "group": "Assessment info",
             "label": "Evaluator", "type": "text", "required": True},
            {"key": "cam_date", "label": "Date", "type": "date",
             "required": True},

            # ---- I. Acute onset and fluctuating course ------------------------
            {"key": "cam_1a", "group": "I. Acute onset and fluctuating course",
             "label": "a) Is there evidence of an acute change in mental "
                      "status from the patient's baseline?",
             "type": "radio", "required": True, "options": ["Yes", "No"]},
            {"key": "cam_1b",
             "label": "b) Did the (abnormal) behavior fluctuate during the "
                      "day, that is tend to come and go or increase and "
                      "decrease in severity?",
             "type": "radio", "required": True, "options": ["Yes", "No"]},

            # ---- II. Inattention ----------------------------------------------
            {"key": "cam_2", "group": "II. Inattention",
             "label": "Did the patient have difficulty focusing attention, "
                      "for example, being easily distractible or having "
                      "difficulty keeping track of what was being said?",
             "type": "radio", "required": True, "options": ["Yes", "No"]},

            # ---- III. Disorganized thinking -----------------------------------
            {"key": "cam_3", "group": "III. Disorganized thinking",
             "label": "Was the patient's thinking disorganized or incoherent, "
                      "such as rambling or irrelevant conversation, unclear "
                      "or illogical flow of ideas, or unpredictable switching "
                      "from subject to subject?",
             "type": "radio", "required": True, "options": ["Yes", "No"]},

            # ---- IV. Altered level of consciousness ---------------------------
            {"key": "cam_4", "group": "IV. Altered level of consciousness",
             "label": "Overall, how would you rate the patient's level of "
                      "consciousness?",
             "type": "radio", "required": True, "horizontal": False,
             "options": ["Alert (normal)",
                         "Vigilant (hyperalert)",
                         "Lethargic (drowsy, easily aroused)",
                         "Stupor (difficult to arouse)",
                         "Coma (unarousable)"]},

            # ---- Result (auto-calculated) -------------------------------------
            {"key": "cam_delirium_suggested", "group": "Result",
             "label": "Delirium suggested (auto-calculated on save)",
             "type": "computed", "required": False, "compute": _cam_delirium,
             "help": "Worksheet rule: Inattention and at least one other "
                     "Box 1 item, and at least one Box 2 item → delirium "
                     "is suggested."},
        ],
    },

    # -------------------------------------------------------------------------
    # POST-SURGERY  ·  SECTION 2  ·  HADS (Anxiety items only)
    # Source: HADS-PDF.pdf — Hospital Anxiety and Depression Scale.
    # Same 7 Column A items as Pre §2, administered ANEW after surgery and
    # stored in separate hads_* columns (the pre administration lives in
    # hads_pre_*), so pre and post answers/scores never mix. The depression
    # (Column D) questions are removed, matching the pre-surgery form.
    # -------------------------------------------------------------------------
    {
        "key": "post_s2",
        "survey": "post",
        "number": 2,
        "title": "Hospital Anxiety and Depression Scale (HADS)",
        "no_blank": True,   # per protocol: no "(no answer)" choice
        "intro": "Tick the reply that is closest to how you have been feeling "
                 "in the past week. Don't take too long over your replies: "
                 "your immediate is best.",
        "fields": _hads_fields(subscales=("A",)),
    },
]


# ----------------------------- small helpers --------------------------------
def sections_for(survey):
    """Return the ordered sections for 'pre' or 'post'."""
    return [s for s in SECTIONS if s["survey"] == survey]


def get_section(section_key):
    for s in SECTIONS:
        if s["key"] == section_key:
            return s
    raise KeyError(f"Unknown section: {section_key}")


def all_fields():
    for s in SECTIONS:
        for f in s["fields"]:
            yield s, f
