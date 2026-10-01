cd metis
python3 -m venv .venv
source .venv/bin/activate

python -m pip install "fastapi[standard]" pydantic sqlalchemy alembic
python -m uvicorn metis.central.main:create_app \
  --factory \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8000
python -m uvicorn metis.devices.hello_metis.agent_api:create_app \
  --factory \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8001
