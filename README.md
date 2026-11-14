# Vitalis---NASA-Space-Apps
Long space missions expose astronauts to five hazards: radiation, isolation and confinement, distance from Earth, gravity fields, and a hostile closed environment. The Space Apps challenge asks for a visual tool that gathers indicators and helps them judge and act on their own health.

# Vitalis platform

**Streamlit** front ends, **FastAPI** back ends, **SQLite via SQLModel**.

```
 Astronaut app (Streamlit :8501) --> Main API  (FastAPI :8000) --\
                                                                   +--> vitalis.db (SQLite)
 Admin portal  (Streamlit :8502) --> Admin API (FastAPI :8001) --/
                     both APIs share  core/  (models, engine, service)
```

| Piece | File | Port |
|---|---|---|
| Astronaut app: home, check-in, detail, report, suit link | `app.py` | 8501 |
| Main API: dashboard, check-in, indicators, EVA dose, report | `api_main.py` | 8000 |
| Admin portal: CSV loader, manual entry, budget and limits, entries | `admin_portal.py` | 8502 |
| Admin API: bulk load, seed, settings, stats, reset | `api_admin.py` | 8001 |
| Shared: tables, health engine, DB helpers | `core/` | - |

## Run
```
pip install -r requirements.txt
python run.py
```
Or start each one by hand:
```
uvicorn api_main:app --port 8000
uvicorn api_admin:app --port 8001
streamlit run app.py --server.port 8501
streamlit run admin_portal.py --server.port 8502
```
The main API seeds 14 demo days on first start if the database is empty.

## Rules enforced in the backend
- `POST /checkin` returns 422 if the radiation dose is missing (mandatory).
- Status comes from hard limits plus drift from the person's own median.
- Budget, per-EVA limit, habitat dose and mission day are editable in the admin portal and are placeholders.

Simulated data. Guidance, not diagnosis.
