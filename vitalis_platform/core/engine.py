"""Pure health logic (no DB, no web). Baselines, traffic lights, radiation budget."""
import math
from statistics import median

DEFAULTS = {"budget": 60.0, "mission_len": 100.0, "per_eva_limit": 0.4, "habitat_daily": 0.5, "today": 15.0}


def _i(k, n, q, u, st, mn, mx, b, tol, f, d, how, why, act, call, lo=None, hi=None, req=False):
    return dict(k=k, n=n, q=q, u=u, st=st, mn=mn, mx=mx, b=b, tol=tol, f=f, dir=d, how=how, why=why, act=act, call=call, lo=lo, hi=hi, req=req)


# Dose first: the mandatory daily radiation log is the first check-in step.
IND = [
    _i("dose", "Radiation dose", "What was your radiation dose today?", "mSv", .05, 0, 3, .55, .25, 2, "high",
       "Read your dosimeter, or use the reading from your suit.", "Exposure builds up and is tracked against your mission budget.",
       ["Spend more time in the shielded area and check again tomorrow.", "Move to the shielded area now and report the reading."],
       "Your reading is near the daily limit or spikes suddenly.", hi=2, req=True),
    _i("sleep", "Sleep", "How many hours did you sleep?", "h", .5, 0, 12, 7.2, 1, 1, "low",
       "Count the time you were actually asleep.", "Poor sleep slows recovery and lowers mood and focus.",
       ["Keep a fixed sleep window, dim the lights an hour before, and limit screens.", "Skip heavy tasks today and ask a crewmate to cover them."],
       "You have had several nights of almost no sleep.", lo=4),
    _i("hr", "Heart rate", "What is your resting heart rate?", "bpm", 1, 40, 130, 58, 5, 0, "high",
       "Sit quietly for 5 minutes, then read your wearable or count your pulse for 30 seconds and double it.",
       "A rising resting rate is an early sign of stress, illness or lost fitness.",
       ["Do your aerobic session, drink water and rest well. Measure again tomorrow.", "Rest now and measure again in 10 minutes."],
       "You have chest pain, faint, or a racing heart that won't settle.", lo=40, hi=100),
    _i("bp", "Blood pressure", "What is your blood pressure (top number)?", "mmHg", 2, 80, 190, 118, 8, 0, "both",
       "Sit for 5 minutes with the cuff on your upper arm at heart level.", "Fluid shifts in low gravity can change blood pressure.",
       ["Drink water, go easy on salt, and re-measure at the same time tomorrow.", "Sit calmly and re-measure in 10 minutes."],
       "You have a headache with blurred vision, chest pain or dizziness.", lo=90, hi=150),
    _i("glu", "Blood sugar", "What is your blood sugar?", "mg/dL", 2, 40, 260, 92, 14, 0, "both",
       "Wash your hands, use the glucometer, and note when you last ate.", "Meal timing and stress in a closed habitat can push blood sugar off track.",
       ["Eat a regular balanced meal, drink water, and re-check in a few hours.", "Treat as you were trained and re-check in 15 minutes."],
       "You feel confused, shaky, or extremely thirsty.", lo=60, hi=180),
    _i("temp", "Temperature", "What is your body temperature?", "°C", .1, 35, 40.5, 36.6, .5, 1, "both",
       "Use the thermometer in the same spot at the same time each day.", "A raised temperature can signal infection or an immune change.",
       ["Rest, drink water and re-check this evening.", "Rest, keep distance from crewmates, and re-check in 30 minutes."],
       "You have a fever with chills, a cough or a spreading rash.", lo=35.5, hi=38),
    _i("mood", "Mood", "How are you feeling today?", "/5", 1, 1, 5, 4, 1, 0, "low",
       "Pick the face that best matches today.", "Isolation shows up in mood before it shows up anywhere else.",
       ["Plan a call home or a shared meal, and take a short break.", "Talk to someone now. You don't have to handle this alone."],
       "You feel hopeless or unsafe, even briefly.", lo=1),
    _i("ex", "Exercise", "How many minutes did you exercise?", "min", 5, 0, 180, 90, 30, 0, "low",
       "Add up resistance and aerobic work.", "Exercise is your main defence against muscle and bone loss in low gravity.",
       ["Restart your full prescribed session today, but never more than prescribed.", "Stop if you have pain or an injury and tell the flight surgeon."],
       "You have pain, injury or dizziness during exercise."),
]
BY = {c["k"]: c for c in IND}
HEAD = ["You're doing well", "A few things to watch", "Please contact the flight surgeon"]
SUB = ["Everything is in your usual range.", "Some readings are drifting from your own baseline. Here's your plan.", "One or more readings need attention now."]
NAMES = ["Steady", "Watch", "Act now"]


def status(c, a):
    """0 steady, 1 watch, 2 act now. Hard limits first, then drift from your own median."""
    if not a or a[-1] is None:
        return 0
    v = a[-1]
    if (c["lo"] is not None and v <= c["lo"]) or (c["hi"] is not None and v >= c["hi"]):
        return 2

    def z(i):
        if a[i] is None:
            return 0
        p = [x for x in a[max(0, i - 7):i] if x is not None]
        if len(p) < 3:
            return 0
        d = a[i] - median(p)
        return (-d if c["dir"] == "low" else d if c["dir"] == "high" else abs(d)) / c["tol"]

    L = len(a) - 1
    x, y = z(L), (z(L - 1) if L else 0)
    return 2 if x >= 2.5 else 1 if (x >= 1.8 or (x >= 1 and y >= 1)) else 0


def usual(a):
    p = [x for x in a[-8:-1] if x is not None]
    return median(p) if p else None


def radiation(es, S):
    L = es[-1]
    cum = sum((e.get("dose") or 0) for e in es)
    p, pace = cum / S["budget"], L["day"] / S["mission_len"]
    r = p / pace if pace else 0
    ok = L["day"] == int(S["today"]) and L.get("dose") is not None
    return dict(cumulative=round(cum, 2), budget=S["budget"], pct=p, pace=pace, projected=cum / L["day"] * S["mission_len"],
                status=2 if p >= .9 or r >= 1.3 else 1 if r >= 1.1 else 0, dose_logged=ok,
                today_dose=L["dose"] if ok else None, habitat=S["habitat_daily"], eva_limit=S["per_eva_limit"])


def dashboard(es, S):
    if not es:
        return {"empty": True}
    R, L, inds, sts = radiation(es, S), es[-1], [], []
    for c in IND:
        a = [e.get(c["k"]) for e in es]
        s = status(c, a)
        sts.append(s)
        inds.append(dict(k=c["k"], n=c["n"], u=c["u"], f=c["f"], value=a[-1], status=s, usual=usual(a), b=c["b"], series=a[-14:]))
    worst = max(sts + [R["status"], 0 if R["dose_logged"] else 1])
    plan = [dict(k=i["k"], n=i["n"], status=i["status"], text=BY[i["k"]]["act"][i["status"] - 1])
            for i in sorted(inds, key=lambda x: -x["status"]) if i["status"]][:4]
    return dict(empty=False, today=int(S["today"]), headline=HEAD[worst], sub=SUB[worst], worst=worst, steady=sts.count(0), total=len(IND),
                complete=bool(L["day"] == int(S["today"]) and L.get("complete")), radiation=R, indicators=inds, plan=plan)


def detail(es, k):
    c = BY[k]
    a = [e.get(k) for e in es]
    return dict(k=k, n=c["n"], u=c["u"], f=c["f"], value=a[-1] if a else None, status=status(c, a), usual=usual(a), days=[e["day"] for e in es][-14:],
                series=a[-14:], how=c["how"], why=c["why"], act=c["act"], call=c["call"])


def report(es, S):
    if not es:
        return "No data."
    L, lines = es[-1], []
    for c in IND:
        a = [e.get(c["k"]) for e in es]
        v, u = a[-1], usual(a)
        lines.append(f"{['●','▲','■'][status(c, a)]} {c['n']}: {'–' if v is None else round(v, c['f'])} {c['u']} ({NAMES[status(c, a)]}, usual {'–' if u is None else round(u, c['f'])})")
    return f"Vitalis report · Day {L['day']} · SIMULATED DATA\n" + "\n".join(lines) + "\nGuidance only, not a diagnosis."


def seed_rows():
    out = []
    for d in range(1, 15):
        w, m = max(0, d - 10), d >= 12
        out.append(dict(day=d, sleep=round(7.2 + .4 * math.sin(d * 1.3) - .5 * w, 1), hr=round(58 + 1.5 * math.sin(d * 2.1) + 2 * w),
                        bp=round(118 + 3 * math.sin(d * 1.7)), glu=round(92 + 4 * math.sin(d * 2.4)), temp=round(36.6 + .12 * math.sin(d * 1.9), 1),
                        mood=3 if m else 4, ex=round((90 + 10 * math.sin(d * 1.1) - (50 if m else 0)) / 5) * 5,
                        dose=round(.55 + .05 * math.sin(d * 1.5), 2), complete=True, source="seed"))
    return out
