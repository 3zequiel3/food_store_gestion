release: alembic -c backend/alembic.ini upgrade head
web: python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
