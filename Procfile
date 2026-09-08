# Start the full Mnema stack: backend API + worker + frontend.
# Usage (from the repo root):
#   backend/.venv/bin/honcho start
api: cd backend && uv run uvicorn app.main:app --reload
worker: cd backend && uv run arq app.workers.worker.WorkerSettings
web: cd frontend && PORT=3000 npm run dev
