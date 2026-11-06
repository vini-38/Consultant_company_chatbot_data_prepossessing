import pandas as pd
import streamlit as st

st.set_page_config(page_title="HireEdge Assistant", page_icon="💼", layout="wide")


# ---------------------------------------------------------------
# 1. LOAD + PREPROCESS DATA
# ---------------------------------------------------------------
@st.cache_data
def load_data():
    cand = pd.read_csv("candidates_clean.csv")
    jobs = pd.read_csv("jobs_clean.csv")
    company = pd.read_csv("company_info.csv")

    # ---- clean candidates ----
    cand = cand.drop_duplicates()
    for col in ["expected_salary", "experience_years"]:
        cand[col] = cand[col].fillna(cand[col].median())
    for col in ["skill", "location", "status"]:
        cand[col] = cand[col].str.strip().str.title()

    # ---- clean jobs ----
    jobs = jobs.drop_duplicates()
    for col in ["client", "role", "skill_required", "location", "status"]:
        jobs[col] = jobs[col].str.strip()
    jobs["skill_required"] = jobs["skill_required"].str.title()
    jobs["location"] = jobs["location"].str.title()
    jobs["status"] = jobs["status"].str.title()

    return cand, jobs, company


cand, jobs, company = load_data()


# ---------------------------------------------------------------
# 2. CHATBOT LOGIC (rule based, no API)
# ---------------------------------------------------------------
def find_match(q, options):
    """Return the first option (e.g. a skill or city) found inside the question."""
    for opt in options:
        if str(opt).lower() in q:
            return opt
    return None


def company_bot(q):
    """Look up the answer in company_info.csv using keywords."""
    for _, row in company.iterrows():
        for kw in row["keywords"].split(","):
            if kw.strip() in q:
                return row["answer"]
    return None


def chatbot(question):
    q = question.lower()
    skill = find_match(q, cand["skill"].unique())
    city = find_match(q, cand["location"].unique())

    # ---- questions about JOBS ----
    if any(w in q for w in ["job", "opening", "vacanc", "position", "requirement"]):
        data = jobs[jobs["status"] == "Open"]
        if skill:
            data = data[data["skill_required"] == skill]
        if city:
            data = data[data["location"] == city]
        if any(w in q for w in ["list", "show", "which", "what"]):
            return data[["job_id", "client", "role", "location", "salary_budget"]]
        return f"There are {len(data)} open job(s)" + (f" for {skill}" if skill else "") + (f" in {city}" if city else "") + "."

    # ---- questions about CLIENTS ----
    if "client" in q and any(w in q for w in ["how many", "list", "which"]):
        return "Our clients: " + ", ".join(sorted(jobs["client"].unique()))

    # ---- salary questions ----
    if "salary" in q:
        data = cand
        if skill:
            data = data[data["skill"] == skill]
        if city:
            data = data[data["location"] == city]
        if data.empty:
            return "No candidates found for that filter."
        if any(w in q for w in ["highest", "max", "top"]):
            return f"Highest expected salary: Rs {data['expected_salary'].max():,.0f}"
        if any(w in q for w in ["lowest", "min"]):
            return f"Lowest expected salary: Rs {data['expected_salary'].min():,.0f}"
        return f"Average expected salary: Rs {data['expected_salary'].mean():,.0f}"

    # ---- experience questions ----
    if "experience" in q or "experienced" in q:
        data = cand[cand["skill"] == skill] if skill else cand
        return f"Average experience: {data['experience_years'].mean():.1f} years"

    # ---- status questions (placed, shortlisted, etc.) ----
    status = find_match(q, cand["status"].unique())
    if status:
        data = cand[cand["status"] == status]
        if skill:
            data = data[data["skill"] == skill]
        if city:
            data = data[data["location"] == city]
        if any(w in q for w in ["list", "show", "who"]):
            return data[["candidate_id", "name", "skill", "location", "status"]]
        return f"{len(data)} candidate(s) are {status}."

    # ---- candidate counts and lists ----
    if "candidate" in q or "people" in q or "profiles" in q:
        data = cand
        if skill:
            data = data[data["skill"] == skill]
        if city:
            data = data[data["location"] == city]
        if any(w in q for w in ["list", "show", "who"]):
            return data[["candidate_id", "name", "skill", "experience_years", "expected_salary", "location", "status"]]
        return f"There are {len(data)} candidate(s)" + (f" with {skill} skill" if skill else "") + (f" in {city}" if city else "") + "."

    # ---- summary ----
    if "summary" in q or "overview" in q:
        return (
            f"Candidates: {len(cand)} | Open jobs: {(jobs['status'] == 'Open').sum()} | "
            f"Placed: {(cand['status'] == 'Placed').sum()} | Clients: {jobs['client'].nunique()}"
        )

    # ---- general company questions ----
    answer = company_bot(q)
    if answer:
        return answer

    return (
        "Sorry, I didn't get that. Try: 'How many Python candidates?', "
        "'Open jobs in Chennai', 'Average salary for Java', 'Who is shortlisted?' or 'What services do you offer?'"
    )


# ---------------------------------------------------------------
# 3. APP LAYOUT
# ---------------------------------------------------------------
st.title("💼 HireEdge Recruitment Assistant")
tab1, tab2, tab3 = st.tabs(["🤖 Chatbot", "📊 Dashboard", "🗂 Data"])

# ---------- Chatbot tab ----------
with tab1:
    with st.sidebar:
        st.header("Try asking")
        samples = [
            "Give me a summary",
            "How many Python candidates?",
            "Open jobs in Chennai",
            "Show open jobs for Java",
            "Average salary for React",
            "Highest salary for Sales",
            "Who is shortlisted?",
            "How many candidates are placed?",
            "What services do you offer?",
            "What are your fees?",
            "How does your process work?",
            "How can I contact you?",
        ]
        for s in samples:
            st.write("•", s)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm the HireEdge assistant. Ask me about candidates, jobs or our company."}
        ]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if isinstance(m["content"], pd.DataFrame):
                st.dataframe(m["content"], use_container_width=True, hide_index=True)
            else:
                st.write(m["content"])

    user_input = st.chat_input("Ask me something...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        reply = chatbot(user_input)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

# ---------- Dashboard tab ----------
with tab2:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidates", len(cand))
    c2.metric("Open jobs", int((jobs["status"] == "Open").sum()))
    c3.metric("Placed", int((cand["status"] == "Placed").sum()))
    c4.metric("Avg expected salary", f"Rs {cand['expected_salary'].mean():,.0f}")

    left, right = st.columns(2)
    with left:
        st.subheader("Candidates by skill")
        st.bar_chart(cand["skill"].value_counts())
    with right:
        st.subheader("Candidates by status")
        st.bar_chart(cand["status"].value_counts())

    left, right = st.columns(2)
    with left:
        st.subheader("Candidates by city")
        st.bar_chart(cand["location"].value_counts())
    with right:
        st.subheader("Open jobs by client")
        st.bar_chart(jobs[jobs["status"] == "Open"]["client"].value_counts())

# ---------- Data tab ----------
with tab3:
    st.subheader("Candidates (cleaned)")
    st.dataframe(cand, use_container_width=True, hide_index=True)
    st.subheader("Jobs (cleaned)")
    st.dataframe(jobs, use_container_width=True, hide_index=True)
