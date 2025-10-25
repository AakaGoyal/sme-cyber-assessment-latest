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
    "employee_range": "1 to 9",
    "turnover_start": 0,               # start of the selected 100k band
    "size": "micro",
    "sector_label": "Retail & Hospitality",
    "sector_key": "hospitality_retail",
    "card_payments": True,
    "personal_data": True,
    "industrial_systems": False,
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
EMPLOYEE_RANGES = ["1 to 9", "10 to 49", "50 to 249", "250 or more"]

SECTOR_LABEL_TO_KEY = {
    "Retail & Hospitality": "hospitality_retail",
    "Professional / Consulting / Legal / Accounting": "professional_services",
    "Manufacturing / Logistics": "manufacturing_logistics",
    "Creative / Marketing / IT Services": "creative_digital_marketing",
    "Health / Wellness / Education": "health_wellness_education",
    "Others (default generic set)": "other_generic",  # no sector file; generic only
}
SECTOR_LABELS = list(SECTOR_LABEL_TO_KEY.keys())

def euro_fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n//1_000_000} million euro"
    return f"{n//1_000} thousand euro"

# 100k-step bands 0 → 9.9M, then two sentinels for larger buckets
TURNOVER_STARTS_100K = list(range(0, 10_000_000, 100_000))  # 0, 100k, ..., 9.9M
TURNOVER_OPTIONS = TURNOVER_STARTS_100K + [10_000_000, 50_000_000]

def turnover_label_from_start(start: int) -> str:
    if start < 10_000_000:
        return f"{euro_fmt(start)} to less than {euro_fmt(start + 100_000)}"
    if start == 10_000_000:
        return "10 to less than 50 million euro"
    return "50 million euro or more"

def size_from_turnover_start(start: int) -> str:
    if start < 2_000_000:
        return "micro"
    if start < 10_000_000:
        return "small"
    return "medium"  # 10–<50M and 50M+ treated as medium

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
    st.title("Small and Medium Enterprise Cybersecurity Self-Assessment")
    st.subheader("Welcome")
    st.write(
        "This assessment adapts to your business. Start with a quick initial assessment, "
        "then answer one question at a time. You will receive a simple summary with strengths and improvements."
    )
    st.markdown("**What you will need:** basic knowledge of your devices, networks, payments and data handling.")
    if st.button("Start initial assessment ➜", type="primary"):
        st.session_state.page = "Initial assessment"
        st.rerun()

# ==========================================================
# PAGE: Initial assessment
# ==========================================================
if st.session_state.page == "Initial assessment":
    st.title("Initial assessment")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.person_name = st.text_input(
            "Your name (person completing this assessment)",
            value=st.session_state.person_name,
            placeholder="First Last",
        )
        st.session_state.company_name = st.text_input(
            "Business name (optional)",
            value=st.session_state.company_name,
            placeholder="Example Consulting Ltd",
        )
        st.session_state.employee_range = st.selectbox(
            "Number of employees (choose a range)",
            EMPLOYEE_RANGES,
            index=EMPLOYEE_RANGES.index(st.session_state.employee_range),
            help="A range is enough for this assessment.",
        )

        st.write("Annual turnover (choose a range)")
        st.session_state.turnover_start = st.select_slider(
            "Move the handle to pick a 100 thousand euro band",
            options=TURNOVER_OPTIONS,
            value=st.session_state.turnover_start,
            format_func=turnover_label_from_start,
            label_visibility="collapsed",
        )
        st.session_state.size = size_from_turnover_start(st.session_state.turnover_start)
        st.info(f"Detected enterprise size: **{st.session_state.size.capitalize()}**")

    with col2:
        st.session_state.sector_label = st.selectbox(
            "Sector",
            SECTOR_LABELS,
            index=SECTOR_LABELS.index(st.session_state.sector_label),
            help="“Others” will load the generic set without sector-specific questions.",
        )
        st.session_state.sector_key = SECTOR_LABEL_TO_KEY[st.session_state.sector_label]

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

    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("⬅ Back to landing"):
        st.session_state.page = "Landing"
        st.rerun()
    if c2.button("Continue to questionnaire ➜", type="primary"):
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

    st.title("Questionnaire")
    st.caption(f"{total} questions loaded for {st.session_state.size} in {st.session_state.sector_label}")

    st.progress((idx) / total if total else 0.0, text=f"Question {idx + 1} of {total}")

    if total == 0:
        st.warning("No questions available for the current settings.")
    else:
        q = qs[idx]
        st.subheader(f"{idx + 1}. {q['section']}")
        st.write(q["text"])
        st.caption(q["hint"])

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

        section_avg = {s: sum(vals) / len(vals) for s, vals in section_scores.items()}
        overall = sum(section_avg.values()) / len(section_avg)

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
