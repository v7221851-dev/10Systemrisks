#!/bin/bash
cd "$(dirname "$0")"
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi
echo "Запуск API на http://localhost:8000"
echo "Убедитесь, что GOOGLE_CREDENTIALS_JSON задан (или есть credentials.json)"
exec uvicorn api.main:app --reload --port 8000
