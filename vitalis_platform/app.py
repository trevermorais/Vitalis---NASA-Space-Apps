"""Vitalis: astronaut app (Streamlit).  streamlit run app.py --server.port 8501
Talks only to the MAIN API (default http://localhost:8000)."""
import os
import pandas as pd
import requests
import calendar
from datetime import datetime
import streamlit as st

API = os.environ.get("VITALIS_API_URL", "http://localhost:8000")
CHIP = ["🟢 Steady", "🟠 Watch", "🔴 Act now"]
FACES = "😞🙁😐🙂😄"

st.set_page_config(page_title="Vitalis", page_icon="🩺", layout="centered")
ss = st.session_state
for k, v in dict(page="home", step=0, tmp={}, msg="", err="", sel=None, hab=0.5, limit=0.4,
                 eva=dict(on=False, min=0, dose=0.0, spe=False, day=0.0, conn=True)).items():
    ss.setdefault(k, v)


def api(method, path, **kw):
    try:
        r = requests.request(method, API + path, timeout=10, **kw)
        if r.ok:
            return r.json(), None
        try:
            return None, str(r.json().get("detail", r.text))
        except Exception:
            return None, r.text
    except requests.RequestException:
        return None, f"Backend unreachable at {API}. Is the main API running?"


def go(p, **kw):
    ss.page = p
    ss.update(kw)


def fmt(v, f):
    return "–" if v is None else f"{v:.{f}f}"


def tdose():
    e = ss.eva
    return round(ss.hab + e["day"] + e["dose"], 2)


def eva_level():
    q = ss.eva["dose"] / ss.limit if ss.limit else 0
    return 2 if q >= 1 else 1 if q >= .7 else 0


# ----------------------------------------------------------------- HOME
def start_checkin(d):
    ss.step, ss.err = 0, ""
    ss.tmp = {}
    ss.defaults = {i["k"]: (i["value"] if i["value"] is not None else i["b"]) for i in d["indicators"]}
    ss.page = "checkin"


def home():
    d, err = api("GET", "/dashboard")
    now = datetime.now()
    total_days = calendar.monthrange(now.year, now.month)[1]
    current_time = now.strftime("%I:%M %p")
    if err:
        st.error(err)
        st.stop()
    if d.get("empty"):
        st.info("No data yet. Open the admin portal (port 8502) and load or seed data.")
        st.stop()
    R = d["radiation"]
    ss.hab, ss.limit = R["habitat"], R["eva_limit"]
    st.caption(f"Day {d['today']} of {total_days} · {current_time}") # considering one trip being a month long, the days are measured in days of the month
    st.title(d["headline"])
    if ss.msg:
        st.success(ss.msg)
        ss.msg = ""
    if not R["dose_logged"]:
        st.warning("**Required:** log today's radiation dose. It is the first step of your check-in.")
    if ss.eva["on"] and eva_level():
        (st.error if eva_level() == 2 else st.warning)(
            "EVA dose limit reached: return to the airlock now." if eva_level() == 2 else "EVA dose is high: plan your return.")
        
    c1, c2 = st.columns([1, 2])
    c1.metric("Steady", f"{d['steady']}/{d['total']}")
    c2.progress(d["steady"] / d["total"])
    c2.caption(d["sub"])

    if d["worst"] == 2:
        st.error("Contact the flight surgeon.")
        st.button("Prepare my report", on_click=go, args=("report",))
    st.button("Update today's check-in" if d["complete"] else "Start today's check-in · 1 min", type="primary",
              use_container_width=True, on_click=start_checkin, args=(d,))

    with st.container(border=True):
        st.subheader("Radiation exposure")
        st.markdown(f"### {R['cumulative']:.1f} mSv  <small>of {R['budget']:.0f} mSv budget</small>", unsafe_allow_html=True)
        st.progress(min(1.0, R["pct"]))
        st.caption(f"{R['pct']*100:.0f}% used · you should be at {R['pace']*100:.0f}% by now · {CHIP[R['status']]}")
        st.caption(f"Today: {R['today_dose']:.2f} mSv logged ✓" if R["dose_logged"] else "Today: not logged yet")
        st.caption(f"On pace for about {R['projected']:.0f} mSv by the end of the mission.")
        st.button("Open suit link", on_click=go, args=("suit",), key="suit_btn")

    if d["plan"]:
        st.subheader("Your plan for today")
        for p in d["plan"]:
            st.checkbox(f"**{p['n']}** ({CHIP[p['status']]}): {p['text']}", key=f"done_{p['k']}")

    st.subheader("Your body today")
    cols = st.columns(2)
    for i, ind in enumerate(d["indicators"]):
        with cols[i % 2], st.container(border=True):
            st.caption(ind["n"])
            st.markdown(f"### {fmt(ind['value'], ind['f'])} {ind['u']}")
            st.write(CHIP[ind["status"]])
            st.button("Details", key=f"o_{ind['k']}", on_click=go, args=("detail",), kwargs={"sel": ind["k"]})
    st.button("Contact the flight surgeon", on_click=go, args=("report",), key="rep_btn")
    st.caption("Simulated demo data · guidance, not diagnosis · works offline-first")


# ------------------------------------------------------------- CHECK-IN
def nxt(inds, skip=False):
    c = inds[ss.step]
    ss.tmp[c["k"]] = None if skip else ss.get(f"in_{c['k']}")
    if ss.step < len(inds) - 1:
        ss.step += 1
        return
    _, err = api("POST", "/checkin", json={"values": ss.tmp})
    if err:
        ss.err = err
        return
    ss.msg, ss.page = "Check-in saved. Here's how you're doing.", "home"


def prev():
    if ss.step > 0:
        ss.step -= 1
    else:
        ss.page = "home"


def use_suit():
    ss["in_dose"] = float(tdose())


def checkin():
    inds, err = api("GET", "/indicators")
    if err:
        st.error(err)
        st.stop()
    c, n = inds[ss.step], len(inds)
    k, whole = c["k"], c["f"] == 0 and float(c["st"]).is_integer()
    st.button("← Back" if ss.step else "← Cancel", on_click=prev)
    st.progress((ss.step + 1) / n)
    st.caption(f"{ss.step + 1} of {n}")
    st.header(c["q"])
    val = ss.tmp.get(k, ss.defaults.get(k, c["b"]))
    val = c["b"] if val is None else val
    if k == "mood":
        st.radio("Mood", [1, 2, 3, 4, 5], index=int(val) - 1, format_func=lambda i: FACES[i - 1], horizontal=True, key="in_mood")
    else:
        cast = int if whole else float
        st.slider(c["n"], cast(c["mn"]), cast(c["mx"]), cast(min(max(val, c["mn"]), c["mx"])), step=cast(c["st"]), key=f"in_{k}")
    if k == "dose":
        st.button(f"Use my suit's reading ({tdose()} mSv)", on_click=use_suit)
        st.caption("Required every day.")
    st.caption(c["how"])
    if ss.err:
        st.error(ss.err)
    b1, b2 = st.columns(2)
    if c["req"]:
        b1.button("Required", disabled=True, use_container_width=True)
    else:
        b1.button("Skip", on_click=nxt, args=(inds, True), use_container_width=True)
    b2.button("Save check-in" if ss.step == n - 1 else "Next", type="primary", on_click=nxt, args=(inds,), use_container_width=True)


# --------------------------------------------------------------- DETAIL
def detail():
    d, err = api("GET", f"/indicators/{ss.sel}")
    st.button("← Back", on_click=go, args=("home",))
    if err:
        st.error(err)
        st.stop()
    st.header(d["n"])
    st.markdown(f"## {fmt(d['value'], d['f'])} {d['u']}  {CHIP[d['status']]}")
    st.caption(f"Your usual: {fmt(d['usual'], d['f'])} {d['u']}")
    st.line_chart(pd.DataFrame({"value": d["series"]}, index=d["days"]), height=180)
    st.subheader("Why it matters")
    st.write(d["why"])
    st.subheader("What to do now" if d["status"] else "Keep it steady")
    st.write(d["act"][d["status"] - 1] if d["status"] else "No action needed. Keep your routine and check in tomorrow.")
    st.subheader("How to measure")
    st.write(d["how"])
    st.subheader("Contact the flight surgeon if")
    st.write(d["call"])
    st.button("Prepare a report", on_click=go, args=("report",))


# --------------------------------------------------------------- REPORT
def report():
    d, err = api("GET", "/report")
    st.button("← Back", on_click=go, args=("home",))
    st.header("Report for the flight surgeon")
    st.caption("Check it, then send. You decide what is shared.")
    if err:
        st.error(err)
        st.stop()
    st.code(d["text"], language=None)
    if st.button("Send when link is back", type="primary"):
        st.success("Queued on this device. It sends when a link to Earth exists.")


# ----------------------------------------------------------------- SUIT
def suit_live():
    e = ss.eva
    rate = (500 if e["spe"] else 60) if e["on"] else 20
    if e["on"]:
        e["min"] += 5
        e["dose"] += rate * 5 / 60 / 1000
    lv = eva_level()
    if lv:
        (st.error if lv == 2 else st.warning)("EVA dose limit reached. Return to the airlock now." if lv == 2 else "EVA dose is high. Plan your return.")
    with st.container(border=True):
        st.write(f"**{'On EVA · ' + str(e['min'] // 60) + 'h ' + format(e['min'] % 60, '02d') + 'm' if e['on'] else 'Inside the habitat'}**")
        st.metric("Dose rate now", f"{rate} µSv/h")
        st.progress(min(1.0, e["dose"] / ss.limit))
        st.caption(f"This EVA: {e['dose']:.3f} mSv of {ss.limit} mSv limit · Today's dose so far: {tdose()} mSv")
        if e["conn"]:
            hr = round(98 + 14 * __import__("math").sin(e["min"] / 9) + (10 if e["spe"] else 0)) if e["on"] else 61
            st.caption(f"Suit heart rate: {hr} bpm")


def eva_start():
    ss.eva.update(on=True, min=0, dose=0.0)


def eva_end():
    e = ss.eva
    _, err = api("POST", "/radiation/eva", json={"dose_msv": round(e["dose"], 4)})
    if err:
        ss.msg = err
        return
    e.update(on=False, spe=False, day=e["day"] + e["dose"], dose=0.0, min=0)
    ss.msg, ss.page = "EVA ended. Your dose was added to today's log.", "home"


def suit():
    e = ss.eva
    st.button("← Back", on_click=go, args=("home",))
    st.header("Suit link")
    e["conn"] = st.toggle("Suit connected (demo)", value=e["conn"])
    st.caption("Your suit measures radiation and adds it to today's record." if e["conn"]
               else "Not connected. Enter your dose by hand in the check-in. It still counts.")
    st.fragment(run_every=1 if e["on"] else None)(suit_live)()
    if not e["on"]:
        st.button("Start EVA", type="primary", disabled=not e["conn"], on_click=eva_start, use_container_width=True)
    else:
        st.button("End EVA and log my dose", type="primary", on_click=eva_end, use_container_width=True)
        st.button("End solar particle event" if e["spe"] else "Simulate a solar particle event",
                  on_click=lambda: e.update(spe=not e["spe"]), use_container_width=True)
    st.caption("Demo: one second is five minutes. Limits and rates are placeholders until flight medicine sets them.")


{"home": home, "checkin": checkin, "detail": detail, "report": report, "suit": suit}[ss.page]()
