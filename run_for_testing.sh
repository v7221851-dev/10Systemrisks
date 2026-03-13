#!/bin/bash
# Запуск валидации данных и проверки связки, затем — приложения для тестирования.
# Требуется: credentials.json или GOOGLE_CREDENTIALS_JSON в окружении.

set -e
cd "$(dirname "$0")"

echo "=== 1. Валидация данных (validate_data.py) ==="
python3 validate_data.py
echo ""

echo "=== 2. Проверка связки данных (test_data_integration.py) ==="
python3 test_data_integration.py
echo ""

echo "=== 3. Запуск приложения для тестирования ==="
echo "Откройте в браузере: http://localhost:8501"
exec streamlit run app.py
