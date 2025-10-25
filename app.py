import streamlit as st
from pathlib import Path
from loader import build_question_set

st.set_page_config(page_title="SME Cybersecurity Self-Assessment", layout="wide")

st.title("Small and Medium Enterprise Cybersecurity Self-Assessment")

with st.sidebar:
    st.header("Setup")
    annual_turnover = st.number_input("Annual turnover (euro)", min_value=0, step=1000, value=500000)
    sector = st.selectbox(
        "Sector",
        [
            "hospitality_retail",
            "professional_services",
            "manufacturing_logistics",
            "creative_digital_marketing",
            "health_wellness_education",
            "technology_startup_saas",
        ],
    )
    card_payments = st.checkbox("We accept card payments or use point of sale systems", True)
    personal_data = st.checkbox("We process personal data of individuals in the European Union", True)
    industrial_systems = st.checkbox("We use production or control systems connected to networks", False)

    if annual_turnover < 2_000_000:
        size = "micro"
    elif annual_turnover < 10_000_000:
        size = "small"
    else:
        size = "medium"

    st.info(f"Detected enterprise size: {size.capitalize()}")

overlay_flags = {
    "payment_card_industry_data_security_standard": card_payments,
    "general_data_protection_regulation": personal_data,
    "operational_technology_and_industrial_control": industrial_systems,
}

questions, debug = build_question_set(Path("."), size, sector, overlay_flags)

st.caption(f"Loaded {len(questions)} questions for {size} in {sector.replace('_',' ')}")

answers = {}
for i, q in enumerate(questions, 1):
    st.subheader(f"{i}. {q['section']}")
    st.write(q["text"])
    st.caption(q["hint"])
    choice = st.radio("Answer", ["Yes", "Partially or unsure", "No"], key=q["id"], horizontal=True)
    answers[q["id"]] = choice

st.divider()

def score(choice): return {"Yes": 2, "Partially or unsure": 1, "No": 0}[choice]
section_scores = {}
for q in questions:
    s = q["section"]
    section_scores.setdefault(s, []).append(score(answers[q["id"]]))
section_avg = {s: sum(v)/len(v) for s, v in section_scores.items()}
overall = sum(section_avg.values()) / len(section_avg)

def color(avg):
    if avg >= 1.6: return "🟩 Good"
    if avg >= 0.8: return "🟨 Needs improvement"
    return "🟥 At risk"

st.header("Summary")
st.metric("Overall Score", f"{overall:.2f}", color(overall))
for s, avg in section_avg.items():
    st.write(f"**{s}** — {color(avg)} ({avg:.2f})")

with st.expander("Debug information"):
    st.write(debug)
