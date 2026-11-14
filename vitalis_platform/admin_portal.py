"""Vitalis: admin portal / data loader (Streamlit).  streamlit run admin_portal.py --server.port 8502
Talks only to the ADMIN API (default http://localhost:8001)."""
import os
import pandas as pd
import requests
import streamlit as st

API = os.environ.get("VITALIS_ADMIN_API_URL", "http://localhost:8001")
COLS = ["day", "dose", "sleep", "hr", "bp", "glu", "temp", "mood", "ex"]

st.set_page_config(page_title="Vitalis Admin", page_icon="🛠️", layout="wide")


def api(method, path, **kw):
    try:
        r = requests.request(method, API + path, timeout=15, **kw)
        if r.ok:
            return r.json(), None
        try:
            return None, str(r.json().get("detail", r.text))
        except Exception:
            return None, r.text
    except requests.RequestException:
        return None, f"Admin API unreachable at {API}"


def post_rows(rows, source="csv"):
    res, err = api("POST", "/admin/entries/bulk", json={"rows": rows, "source": source})
    if err:
        st.error(err)
        return
    st.success(f"Loaded {res['loaded']} day(s).")
    for e in res["errors"]:
        st.warning(e)


def loader():
    st.header("Data loader (CSV)")
    st.caption("One row per mission day. Required column: `day`. Other columns are optional and only update what you provide.")
    sample = pd.DataFrame([dict(day=15, dose=.55, sleep=7.0, hr=58, bp=118, glu=92, temp=36.6, mood=4, ex=90)])
    st.download_button("Download CSV template", sample.to_csv(index=False), "vitalis_template.csv", "text/csv")
    f = st.file_uploader("Upload CSV", type="csv")
    if f:
        df = pd.read_csv(f)
        if "day" not in df.columns:
            st.error("Missing required column: day")
            return
        st.dataframe(df, use_container_width=True)
        if st.button("Load into database", type="primary"):
            clean = df[[c for c in df.columns if c in COLS]].astype(object).where(pd.notna(df), None)
            rows = clean.to_dict("records")
            for r in rows:
                r["day"] = int(r["day"])
            post_rows(rows)
    st.divider()
    if st.button("Load demo data (replaces everything)"):
        res, err = api("POST", "/admin/seed")
        st.error(err) if err else st.success(f"Seeded {res['loaded']} demo days.")


def manual():
    st.header("Manual entry")
    with st.form("manual"):
        c = st.columns(3)
        row = {"day": c[0].number_input("Day", 1, 1000, 15), "dose": c[1].number_input("Radiation dose (mSv)", 0.0, 5.0, .55, .05),
               "sleep": c[2].number_input("Sleep (h)", 0.0, 14.0, 7.0, .5), "hr": c[0].number_input("Heart rate", 30, 200, 58),
               "bp": c[1].number_input("Blood pressure", 60, 220, 118), "glu": c[2].number_input("Blood sugar", 30, 400, 92),
               "temp": c[0].number_input("Temperature", 34.0, 42.0, 36.6, .1), "mood": c[1].number_input("Mood (1-5)", 1, 5, 4),
               "ex": c[2].number_input("Exercise (min)", 0, 300, 90)}
        if st.form_submit_button("Save entry", type="primary"):
            post_rows([row], "manual")


def limits():
    st.header("Budget & limits")
    cur, err = api("GET", "/admin/settings")
    if err:
        st.error(err)
        return
    with st.form("limits"):
        v = {"budget": st.number_input("Mission radiation budget (mSv)", 1.0, 1000.0, float(cur["budget"])),
             "mission_len": st.number_input("Mission length (days)", 1.0, 2000.0, float(cur["mission_len"])),
             "per_eva_limit": st.number_input("Per-EVA dose limit (mSv)", .01, 10.0, float(cur["per_eva_limit"])),
             "habitat_daily": st.number_input("Habitat daily dose (mSv)", 0.0, 5.0, float(cur["habitat_daily"])),
             "today": st.number_input("Current mission day", 1.0, 2000.0, float(cur["today"]))}
        if st.form_submit_button("Save", type="primary"):
            _, e = api("PUT", "/admin/settings", json=v)
            st.error(e) if e else st.success("Saved. The astronaut app uses these values immediately.")
    st.caption("Placeholders until flight medicine confirms real limits.")


def entries():
    st.header("Entries")
    s, err = api("GET", "/admin/stats")
    if err:
        st.error(err)
        return
    c = st.columns(3)
    c[0].metric("Days stored", s["entries"])
    c[1].metric("Cumulative dose", f"{s['cumulative_dose']} mSv")
    c[2].metric("Day range", f"{s['first_day']} to {s['last_day']}" if s["entries"] else "–")
    rows, _ = api("GET", "/admin/entries")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    if st.checkbox("I understand this deletes all entries") and st.button("Delete all entries"):
        api("DELETE", "/admin/entries")
        st.rerun()


st.sidebar.title("🛠️ Vitalis Admin")
st.sidebar.caption(f"API: {API}")
ok = api("GET", "/health")[1] is None
if ok:
    st.sidebar.success("🟢 Backend online")
else:
    st.sidebar.error("🔴 Backend unreachable")
page = st.sidebar.radio("Section", ["Data loader (CSV)", "Manual entry", "Budget & limits", "Entries"])
{"Data loader (CSV)": loader, "Manual entry": manual, "Budget & limits": limits, "Entries": entries}[page]()
