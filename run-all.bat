@echo off
echo Starting NoteGeneration Platform...

echo Starting Backend Server in a new window...
start cmd /k "cd backend && ..\.venv\Scripts\python run.py"

echo Starting Celery Worker in a new window...
start cmd /k "cd backend && ..\.venv\Scripts\celery -A app.celery_app worker --loglevel=info -P threads"

echo Starting Next.js Frontend Server in a new window...
start cmd /k "cd frontend && npm run dev"

echo All services initiated! 
echo Press any key to exit this script.
pause > null
