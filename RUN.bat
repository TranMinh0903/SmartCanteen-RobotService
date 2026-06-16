@echo off
REM Chạy robot-arm-service (DRY_RUN theo .env)
if not exist .venv (
  python -m venv .venv
  call .venv\Scripts\activate
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
if not exist .env copy .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
