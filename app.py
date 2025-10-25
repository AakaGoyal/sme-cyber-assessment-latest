import streamlit as st
from pathlib import Path
from loader import build_question_set

st.set_page_config(page_title="SME Cybersecurity Self-Assessment", layout="wide")

# =========================
# Session defaults
# =========================
defaults = {
    "page": "Landing",                 # Landing → Initial assessment → Questionnaire → Results
    "person_name": "",
    "company_name": "",
    "employee_range": "1–5",
    "turnover_start": 0,               # start of the selected 100k band (via dropdown)
    "size": "micro",
    "sector_label": "Retail & Hospitality",
    "sector_key": "hospitality_retail",
    "card_payments": True,
    "personal_data": True,
    "industrial_systems": False,

    # Initial assessment extras (Business profile + Digital footprint)
    "bp_it_manager": "Self-managed",
    "bp_asset_inventory": "Partially",
    "bp_byod": "Sometimes",
    "bp_sensitive_data": "Yes",
    "dp_has_website": "Yes",
    "dp_https": "Yes",
    "dp_business_email": "Yes",
    "dp_social_media": "Yes",
    "dp_public_review": "Sometimes",

    # Snapshot-related inputs
    "years_in_business": "<1 year",
    "work_mode": "Local & in-person",

    "questions": [],
    "answers": {},                     # {question_id: "Yes" | "Partially or unsure" | "No"}
    "q_index": 0,                      # current question index
    "debug": False,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# =========================
# Options & helpers
# =========================
EMPLOYEE_RANGES = ["1–5", "6–10", "10–25", "26–50", "51–100", "More than 100"]

SECTOR_LABEL_TO_KEY = {
    "Retail & Hospitality": "hospitality_retail",
    "Professional / Consulting / Legal / Accounting": "professional_services",
    "Manufacturing / Logistics": "manufacturing_logistics",
    "Creative / Marketing / IT Services": "creative_digital_marketing",
    "Health / Wellness / Education": "health_wellness_education",
    "Others (default generic set)": "other_generic",  # no sector file; generic only
}
SECTOR_LABELS = list(SECTOR_LABEL_TO_KEY.keys())

YEARS_OPTIONS = ["<1 year", "1–3 years", "4–10 years", "10+ years"]
WORK_MODE_OPTIONS = ["Local & in-person", "Online/remote", "A mix of both"]

def euro_short(n: int) -> str:
    # 100_000 -> "€100k", 5_000_000 -> "€5.0M"
    if n >= 1_000_000:
        return f"€{n/1_000_000:.1f}M"
    return f"€{n//1000}k"

def euro_fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n//1_000_000} million euro"
    return f"{n//1_000} thousand euro"

# 100k-step bands 0 → 9.9M, then two sentinels for larger buckets
TURNOVER_STARTS_100K = list(range(0, 10_000_000, 100_000))  # 0, 100k, ..., 9.9M
TURNOVER_SENTINELS = [10_000_000, 50_000_000]                # 10–<50M, 50M+
TURNOVER_STARTS_ALL = TURNOVER_STARTS_100K + TURNOVER_SENTINELS

def turnover_label_from_start(start: int) -> str:
    if start < 100_000:
        return "<€100k"
    if start < 10_000_000:
        return euro_short(start)
    if start == 10_000_000:
        return "€10.0M–<€50.0M"
    return "€50.0M+"

def start_from_turnover_label(label: str) -> int:
    if label == "<€100k":
        return 0
    if label == "€10.0M–<€50.0M":
        return 10_000_000
    if label == "€50.0M+":
        return 50_000_000
    raw = label.replace("€", "")
    if raw.endswith("k"):
        return int(float(raw[:-1])) * 1000
    if raw.endswith("M"):
        return int(float(raw[:-1]) * 1_000_000)
    return 0

def build_turnover_dropdown_options():
    # Starts at 100k, then 200k, ..., 9.9M; plus <€100k and the two big buckets
    opts = ["<€100k"]
    for v in range(100_000, 10_000_000, 100_000):
        opts.append(euro_short(v))
    opts.extend(["€10.0M–<€50.0M", "€50.0M+"])
    return opts

TURNOVER_DROPDOWN = build_turnover_dropdown_options()

def size_from_turnover_start(start: int) -> str:
    if start < 2_000_000:
        return "micro"
    if start < 10_000_000:
        return "small"
    return "medium"  # 10–<50M and 50M+ treated as medium

def derive_digital_dependency() -> str:
    """
    Simple heuristic based on inputs commonly linked to online reliance.
    Score (0–5):
      +1 card_payments, +1 personal_data, +2 industrial_systems,
      +1 if turnover >= €1M, +1 if employees >= 51.
    """
    score = 0
    score += 1 if st.session_state.card_payments else 0
    score += 1 if st.session_state.personal_data else 0
    score += 2 if st.session_state.industrial_systems else 0
    score += 1 if st.session_state.turnover_start >= 1_000_000 else 0
    # employees rough check
    emp = st.session_state.employee_range
    if emp in ["51–100", "More than 100"]:
        score += 1
    if score <= 1:
        return "Low"
    if score <= 3:
        return "Medium"
    return "High"

def build_questions_now():
    overlay_flags = {
        "payment_card_industry_data_security_standard": st.session_state.card_payments,
        "general_data_protection_regulation": st.session_state.personal_data,
        "operational_technology_and_industrial_control": st.session_state.industrial_systems,
    }
    qs, debug_log = build_question_set(
        base_dir=Path("."),
        size=st.session_state.size,
        sector=st.session_state.sector_key,  # "other_generic" → no sector add-ins
        overlay_flags=overlay_flags,
    )
    st.session_state.questions = qs
    st.session_state.q_index = 0
    if st.session_state.debug:
        st.toast(f"Loaded {len(qs)} questions for {st.session_state.size} / {st.session_state.sector_key}")
        for line in debug_log:
            st.write(line)

def score_choice(choice: str) -> int:
    return {"Yes": 2, "Partially or unsure": 1, "No": 0}[choice]

def status_from_avg(avg: float) -> str:
    if avg >= 1.6:
        return "🟩 Good"
    if avg >= 0.8:
        return "🟨 Needs improvement"
    return "🟥 At risk"

# --------- Shared UI bits
def render_snapshot():
    with st.container():
        st.subheader("Snapshot")
        st.markdown(
            f"**Business:** {st.session_state.company_name or '—'}  \n"
            f"**Industry:** {st.session_state.sector_label or '—'}  \n"
            f"**People:** {st.session_state.employee_range or '—'}  • "
            f"**Years:** {st.session_state.years_in_business or '—'}  • "
            f"**Turnover:** {turnover_label_from_start(st.session_state.turnover_start)}  \n"
            f"**Work mode:** {st.session_state.work_mode or '—'}"
        )
        st.markdown("---")
        dep = derive_digital_dependency()
        st.markdown(f"**Digital dependency (derived):** {dep}")
        st.caption("Derived from online sales, data handling, and daily tools.")
        st.button("🔁 Restart", key="restart_btn", on_click=_restart)

def _restart():
    # reset volatile fields; keep current page
    keep_page = st.session_state.page
    st.session_state.clear()
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    st.session_state.page = keep_page

# =========================
# Sidebar navigation
# =========================
with st.sidebar:
    st.header("Navigation")
    nav = st.radio(
        "Go to",
        ["Landing", "Initial assessment", "Questionnaire", "Results"],
        index=["Landing", "Initial assessment", "Questionnaire", "Results"].index(st.session_state.page),
    )
    if nav != st.session_state.page:
        st.session_state.page = nav
        st.rerun()
    st.markdown("---")
    st.checkbox("Show debug info", key="debug")

# ==========================================================
# PAGE: Landing
# ==========================================================
if st.session_state.page == "Landing":
    st.title("SME Self-Assessment Wizard")
    st.subheader("First, tell us a bit about the business (≈2 minutes)")

    c1, c2 = st.columns(2)
    with c1:
        st.session_state.person_name = st.text_input(
            "Your name",
            value=st.session_state.person_name,
            placeholder="First Last",
        )
        # REQUIRED business name (no “optional”)
        st.session_state.company_name = st.text_input(
            "Business name",
            value=st.session_state.company_name,
            placeholder="Example Consulting Ltd",
        )
        st.session_state.sector_label = st.text_input(
            "Industry / core service (e.g., retail, consulting)",
            value=st.session_state.sector_label,
            placeholder="Retail & Hospitality",
        )
        st.session_state.sector_key = SECTOR_LABEL_TO_KEY.get(
            st.session_state.sector_label, "other_generic"
        )

    with c2:
        st.session_state.years_in_business = st.selectbox(
            "How long in business?",
            YEARS_OPTIONS,
            index=YEARS_OPTIONS.index(st.session_state.years_in_business),
        )
        # employees — updated ranges
        try:
            emp_index = EMPLOYEE_RANGES.index(st.session_state.employee_range)
        except ValueError:
            emp_index = 0
        st.session_state.employee_range = st.selectbox(
            "How many people (incl. contractors)?",
            EMPLOYEE_RANGES,
            index=emp_index,
        )
        current_label = turnover_label_from_start(st.session_state.turnover_start)
        try:
            t_index = build_turnover_dropdown_options().index(current_label)
        except ValueError:
            t_index = 0
        chosen_label = st.selectbox(
            "Approx. annual turnover",
            build_turnover_dropdown_options(),
            index=t_index,
        )
        st.session_state.turnover_start = start_from_turnover_label(chosen_label)

    st.session_state.work_mode = st.radio(
        "Would you describe your business as mostly…",
        WORK_MODE_OPTIONS,
        horizontal=True,
        index=WORK_MODE_OPTIONS.index(st.session_state.work_mode),
    )

    st.markdown(
        "_We’ll tailor the next questions based on this._"
    )
    disabled = (st.session_state.company_name.strip() == "")
    if st.button("Start Initial Assessment", type="primary", disabled=disabled):
        st.session_state.page = "Initial assessment"
        st.rerun()

# ==========================================================
# PAGE: Initial assessment
# ==========================================================
if st.session_state.page == "Initial assessment":
    st.title("Initial assessment")

    # snapshot + form columns
    snap_col, col1, col2 = st.columns([1, 2, 2], vertical_alignment="top")
    with snap_col:
        render_snapshot()

    with col1:
        st.session_state.person_name = st.text_input(
            "Your name (person completing this assessment)",
            value=st.session_state.person_name,
            placeholder="First Last",
        )
        # REQUIRED
        st.session_state.company_name = st.text_input(
            "Business name",
            value=st.session_state.company_name,
            placeholder="Example Consulting Ltd",
        )
        try:
            emp_index = EMPLOYEE_RANGES.index(st.session_state.employee_range)
        except ValueError:
            emp_index = 0
        st.session_state.employee_range = st.selectbox(
            "Number of employees (choose a range)",
            EMPLOYEE_RANGES,
            index=emp_index,
            help="A range is enough for this assessment.",
        )
        st.session_state.years_in_business = st.selectbox(
            "How long in business?",
            YEARS_OPTIONS,
            index=YEARS_OPTIONS.index(st.session_state.years_in_business),
        )
        # turnover — dropdown in €100k steps
        current_label = turnover_label_from_start(st.session_state.turnover_start)
        try:
            t_index = build_turnover_dropdown_options().index(current_label)
        except ValueError:
            t_index = 0
        chosen_label = st.selectbox(
            "Approx. annual turnover (choose a value)",
            build_turnover_dropdown_options(),
            index=t_index,
            help="Dropdown in €100k steps (no slider).",
        )
        st.session_state.turnover_start = start_from_turnover_label(chosen_label)
        st.session_state.size = size_from_turnover_start(st.session_state.turnover_start)
        st.info(f"Detected enterprise size: **{st.session_state.size.capitalize()}**")

    with col2:
        st.session_state.sector_label = st.selectbox(
            "Sector",
            SECTOR_LABELS,
            index=SECTOR_LABELS.index(st.session_state.sector_label) if st.session_state.sector_label in SECTOR_LABELS else 0,
            help="“Others” will load the generic set without sector-specific questions.",
        )
        st.session_state.sector_key = SECTOR_LABEL_TO_KEY.get(st.session_state.sector_label, "other_generic")

        st.session_state.card_payments = st.checkbox(
            "We accept card payments or use point of sale systems",
            value=st.session_state.card_payments,
        )
        st.session_state.personal_data = st.checkbox(
            "We process personal data of individuals in the European Union",
            value=st.session_state.personal_data,
        )
        st.session_state.industrial_systems = st.checkbox(
            "We use production or control systems connected to networks",
            value=st.session_state.industrial_systems,
        )
        st.session_state.work_mode = st.radio(
            "Work mode",
            WORK_MODE_OPTIONS,
            horizontal=True,
            index=WORK_MODE_OPTIONS.index(st.session_state.work_mode),
        )

    # ---- Business profile & Digital footprint (from the reference sheet)
    st.markdown("---")
    bp, df = st.columns(2)

    with bp:
        st.subheader("Section 1 — Business profile")
        st.caption("Purpose: understand organizational size, structure, and IT management context.")
        st.session_state.bp_it_manager = st.selectbox(
            "Who manages your IT systems?",
            ["Self-managed", "Outsourced IT", "Shared responsibility", "Not sure"],
            index=["Self-managed", "Outsourced IT", "Shared responsibility", "Not sure"].index(st.session_state.bp_it_manager),
        )
        st.session_state.bp_asset_inventory = st.radio(
            "Do you have an inventory of company devices (laptops, phones, servers)?",
            ["Yes", "Partially", "No", "Not sure"],
            horizontal=True,
            index=["Yes", "Partially", "No", "Not sure"].index(st.session_state.bp_asset_inventory),
        )
        st.session_state.bp_byod = st.radio(
            "Do employees use personal devices (BYOD) for work?",
            ["Yes", "Sometimes", "No", "Not sure"],
            horizontal=True,
            index=["Yes", "Sometimes", "No", "Not sure"].index(st.session_state.bp_byod),
        )
        st.session_state.bp_sensitive_data = st.radio(
            "Do you handle sensitive customer or financial data?",
            ["Yes", "No", "Not sure"],
            horizontal=True,
            index=["Yes", "No", "Not sure"].index(st.session_state.bp_sensitive_data),
        )

    with df:
        st.subheader("Section 2 — Digital footprint")
        st.caption("Purpose: identify online exposure and brand presence.")
        st.session_state.dp_has_website = st.radio(
            "Does your business have a public website?",
            ["Yes", "No"],
            horizontal=True,
            index=["Yes", "No"].index(st.session_state.dp_has_website),
        )
        st.session_state.dp_https = st.radio(
            "Is your website protected with HTTPS (padlock symbol)?",
            ["Yes", "No", "Not sure"],
            horizontal=True,
            index=["Yes", "No", "Not sure"].index(st.session_state.dp_https),
        )
        st.session_state.dp_business_email = st.radio(
            "Do you use business email addresses (e.g., info@yourcompany.com)?",
            ["Yes", "No", "Partially"],
            horizontal=True,
            index=["Yes", "No", "Partially"].index(st.session_state.dp_business_email),
        )
        st.session_state.dp_social_media = st.radio(
            "Is your business present on social media platforms?",
            ["Yes", "No"],
            horizontal=True,
            index=["Yes", "No"].index(st.session_state.dp_social_media),
        )
        st.session_state.dp_public_review = st.radio(
            "Do you regularly review what company or employee info is publicly visible online?",
            ["Yes", "Sometimes", "No"],
            horizontal=True,
            index=["Yes", "Sometimes", "No"].index(st.session_state.dp_public_review),
        )

    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("⬅ Back to landing"):
        st.session_state.page = "Landing"
        st.rerun()
    if c2.button("Continue to questionnaire ➜", type="primary", disabled=(st.session_state.company_name.strip() == "")):
        build_questions_now()
        st.session_state.page = "Questionnaire"
        st.rerun()

# ==========================================================
# PAGE: Questionnaire — single question at a time
# ==========================================================
if st.session_state.page == "Questionnaire":
    if not st.session_state.questions:
        build_questions_now()

    qs = st.session_state.questions
    total = len(qs)
    idx = min(st.session_state.q_index, max(0, total - 1))

    # Snapshot left + question right
    snap_col, main = st.columns([1, 3], vertical_alignment="top")
    with snap_col:
        render_snapshot()

    with main:
        st.title("Questionnaire")
        st.caption(f"{total} questions loaded for {st.session_state.size} in {st.session_state.sector_label}")
        st.progress((idx) / total if total else 0.0, text=f"Question {idx + 1} of {total}")

        if total == 0:
            st.warning("No questions available for the current settings.")
        else:
            q = qs[idx]
            st.subheader(f"{idx + 1}. {q['section']}")
            st.write(q["text"])
            with st.expander("Why this matters", expanded=False):
                st.write(q["hint"])

            default_choice = st.session_state.answers.get(q["id"], "Partially or unsure")
            choice = st.radio(
                "Answer",
                ["Yes", "Partially or unsure", "No"],
                horizontal=True,
                index={"Yes": 0, "Partially or unsure": 1, "No": 2}[default_choice],
                key=f"radio_{q['id']}",
            )
            st.session_state.answers[q["id"]] = choice

            st.markdown("---")
            b1, b2, b3 = st.columns([1, 1, 2])
            if b1.button("⬅ Previous", disabled=(idx == 0)):
                st.session_state.q_index = max(0, idx - 1)
                st.rerun()
            if b2.button("Next ➜", disabled=(idx >= total - 1)):
                st.session_state.q_index = min(total - 1, idx + 1)
                st.rerun()
            if b3.button("Finish and see results ✅", type="primary"):
                st.session_state.page = "Results"
                st.rerun()

            with st.expander("Jump to a question"):
                jump = st.slider("Question number", 1, max(1, total), idx + 1)
                if jump - 1 != idx:
                    st.session_state.q_index = jump - 1
                    st.rerun()

# ==========================================================
# PAGE: Results
# ==========================================================
if st.session_state.page == "Results":
    if not st.session_state.questions:
        build_questions_now()
    qs = st.session_state.questions

    st.title("Results")

    # Profile header
    person = st.session_state.person_name.strip() or "Anonymous"
    company = st.session_state.company_name.strip() or "Unnamed business"
    turnover_label = turnover_label_from_start(st.session_state.turnover_start)
    st.caption(f"Assessed by **{person}** for **{company}**")
    st.markdown(
        f"**Profile:** {st.session_state.employee_range} employees · "
        f"Turnover: {turnover_label} · "
        f"Sector: {st.session_state.sector_label} · "
        f"Detected size: {st.session_state.size.capitalize()}"
    )
    st.markdown("---")

    if not qs:
        st.warning("No answers yet. Go to the questionnaire page to answer the questions.")
    else:
        # Section scores
        section_scores = {}
        for q in qs:
            ans = st.session_state.answers.get(q["id"], "Partially or unsure")
            section_scores.setdefault(q["section"], []).append(score_choice(ans))

        section_avg = {s: sum(vals) / len(vals) for s, vals in section_scores.items() if vals}
        overall = sum(section_avg.values()) / len(section_avg) if section_avg else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Overall score (0 to 2)", f"{overall:.2f}")
        c2.metric("Overall status", status_from_avg(overall))
        c3.metric("Questions answered", f"{len([a for a in st.session_state.answers.values() if a])} / {len(qs)}")

        st.markdown("### Section scores")
        for s, avg in sorted(section_avg.items()):
            st.write(f"**{s}** — {status_from_avg(avg)} ({avg:.2f})")

        # Quick wins
        st.markdown("---")
        st.subheader("Suggested quick wins")
        quick_wins = []
        for q in qs:
            ans = st.session_state.answers.get(q["id"], "Partially or unsure")
            if ans != "Yes":
                w = q.get("weights", {"importance": 2, "effort": 2, "impact": 2})
                if w.get("effort", 2) <= 2 and w.get("impact", 2) >= 2:
                    quick_wins.append((q, ans))
        if not quick_wins:
            st.write("Great work. No obvious quick wins based on your answers.")
        else:
            for q, ans in quick_wins[:8]:
                st.write(f"- **{q['section']}**: {q['text']} — _Current answer: {ans}_")

        st.markdown("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Back to questionnaire"):
            st.session_state.page = "Questionnaire"
            st.rerun()
        if c2.button("Start over"):
            st.session_state.answers = {}
            st.session_state.q_index = 0
            st.session_state.page = "Questionnaire"
            st.rerun()
