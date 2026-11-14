"""Vitalis MAIN API (astronaut app).  uvicorn api_main:app --port 8000"""
from contextlib import asynccontextmanager
from typing import Dict, Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session

from core import engine as eng, service
from core.config import settings
from core.db import create_db_and_tables, engine as db_engine, get_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(db_engine) as s:
        if not service.entries(s):
            service.seed(s)  # demo data until the admin loads real data
    yield


app = FastAPI(title="Vitalis API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class CheckIn(BaseModel):
    values: Dict[str, Optional[float]]


class Eva(BaseModel):
    dose_msv: float = Field(ge=0)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "main"}


@app.get("/dashboard")
def dashboard(s: Session = Depends(get_session)):
    return eng.dashboard(service.entries(s), service.get_settings(s))


@app.get("/indicators")
def indicators():
    return eng.IND


@app.get("/indicators/{k}")
def indicator(k: str, s: Session = Depends(get_session)):
    if k not in eng.BY:
        raise HTTPException(404, "Unknown indicator")
    return eng.detail(service.entries(s), k)


@app.post("/checkin")
def checkin(body: CheckIn, s: Session = Depends(get_session)):
    if body.values.get("dose") is None:  # mandatory, enforced server-side
        raise HTTPException(422, "Daily radiation dose is mandatory.")
    day = int(service.get_settings(s)["today"])
    service.upsert(s, {"day": day, "complete": True, "source": "manual", **{k: body.values.get(k) for k in eng.BY}})
    return {"saved": True, "day": day}


@app.post("/radiation/eva")
def log_eva(body: Eva, s: Session = Depends(get_session)):
    """Suit auto-log: adds an EVA dose to today's total."""
    S = service.get_settings(s)
    day = int(S["today"])
    cur = next((e for e in service.entries(s) if e["day"] == day), None)
    base = cur["dose"] if cur and cur.get("dose") is not None else S["habitat_daily"]
    row = {"day": day, "dose": round(base + body.dose_msv, 3)}
    if not cur:
        row["source"] = "suit"
    service.upsert(s, row)
    return {"day": day, "dose": row["dose"]}


@app.get("/report")
def report(s: Session = Depends(get_session)):
    return {"text": eng.report(service.entries(s), service.get_settings(s))}
