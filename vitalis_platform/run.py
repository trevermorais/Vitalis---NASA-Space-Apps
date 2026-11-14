"""Start all four processes:  python run.py
  main API   :8000   admin API :8001
  main app   :8501   admin app :8502"""
import subprocess, sys, time

py = sys.executable
procs = [
    [py, "-m", "uvicorn", "api_main:app", "--port", "8000"],
    [py, "-m", "uvicorn", "api_admin:app", "--port", "8001"],
    [py, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"],
    [py, "-m", "streamlit", "run", "admin_portal.py", "--server.port", "8502", "--server.headless", "true"],
]
running = [subprocess.Popen(p) for p in procs]
print("\nAstronaut app: http://localhost:8501\nAdmin portal:  http://localhost:8502\nMain API docs: http://localhost:8000/docs\nAdmin API docs: http://localhost:8001/docs\n")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for p in running:
        p.terminate()
