"""DB access shared by both APIs."""
from sqlmodel import Session, delete, select
from core import engine as eng
from core.models import Entry, Setting

FIELDS = {"sleep", "hr", "bp", "glu", "temp", "mood", "ex", "dose", "complete", "source"}


def get_settings(s: Session) -> dict:
    d = dict(eng.DEFAULTS)
    d.update({r.key: r.value for r in s.exec(select(Setting)).all()})
    return d


def set_settings(s: Session, upd: dict) -> dict:
    for k, v in upd.items():
        if k in eng.DEFAULTS and v is not None:
            s.merge(Setting(key=k, value=float(v)))
    s.commit()
    return get_settings(s)


def entries(s: Session) -> list[dict]:
    return [e.model_dump() for e in s.exec(select(Entry).order_by(Entry.day)).all()]


def upsert(s: Session, row: dict) -> None:
    """Insert or update one day; only the keys given are changed."""
    e = s.get(Entry, int(row["day"])) or Entry(day=int(row["day"]))
    for k, v in row.items():
        if k in FIELDS:
            setattr(e, k, v)
    s.add(e)
    s.commit()


def reset(s: Session) -> None:
    s.exec(delete(Entry))
    s.commit()


def seed(s: Session, wipe: bool = True) -> int:
    if wipe:
        reset(s)
    set_settings(s, eng.DEFAULTS)
    rows = eng.seed_rows()
    for r in rows:
        upsert(s, r)
    return len(rows)
