"""Vitalis ADMIN API (data loader).  uvicorn api_admin:app --port 8001"""
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session

from core import engine as eng, service
from core.config import settings
from core.db import create_db_and_tables, get_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Vitalis Admin API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class Bulk(BaseModel):
    rows: List[Dict[str, Any]]
    source: str = "csv"


class Limits(BaseModel):
    budget: Optional[float] = None
    mission_len: Optional[float] = None
    per_eva_limit: Optional[float] = None
    habitat_daily: Optional[float] = None
    today: Optional[float] = None


@app.get("/health")
def health():
    return {"status": "healthy", "service": "admin"}


@app.get("/admin/stats")
def stats(s: Session = Depends(get_session)):
    es = service.entries(s)
    return {"entries": len(es), "first_day": es[0]["day"] if es else None, "last_day": es[-1]["day"] if es else None,
            "cumulative_dose": round(sum(e.get("dose") or 0 for e in es), 2), "settings": service.get_settings(s)}


@app.get("/admin/entries")
def list_entries(s: Session = Depends(get_session)):
    return service.entries(s)


@app.post("/admin/entries/bulk")
def bulk(body: Bulk, s: Session = Depends(get_session)):
    ok, errors = 0, []
    for i, r in enumerate(body.rows):
        try:
            service.upsert(s, {**{k: v for k, v in r.items() if k == "day" or k in eng.BY}, "source": body.source, "complete": True})
            ok += 1
        except Exception as e:  # keep going, report per row
            s.rollback()
            errors.append(f"row {i + 1}: {e}")
    return {"loaded": ok, "errors": errors}


@app.post("/admin/seed")
def seed(s: Session = Depends(get_session)):
    return {"loaded": service.seed(s)}


@app.delete("/admin/entries")
def wipe(s: Session = Depends(get_session)):
    service.reset(s)
    return {"deleted": True}


@app.get("/admin/settings")
def get_limits(s: Session = Depends(get_session)):
    return service.get_settings(s)


@app.put("/admin/settings")
def put_limits(body: Limits, s: Session = Depends(get_session)):
    return service.set_settings(s, body.model_dump())
