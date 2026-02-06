#!/usr/bin/env python3
"""
Проверка подключения к Google Sheets через credentials.json
Запуск: python3 test_google_credentials.py
"""
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
import gspread

SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
CRED_FILE = "credentials.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

print("=" * 60)
print("ПРОВЕРКА ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS")
print("=" * 60)

# Проверка файла
if not os.path.exists(CRED_FILE):
    print(f"❌ Файл {CRED_FILE} не найден!")
    exit(1)

print(f"✅ Файл {CRED_FILE} найден")

# Чтение и проверка JSON
try:
    with open(CRED_FILE, "r", encoding="utf-8") as f:
        creds_data = json.load(f)
    print("✅ JSON файл валиден")
    print(f"   Project ID: {creds_data.get('project_id', 'N/A')}")
    print(f"   Client Email: {creds_data.get('client_email', 'N/A')}")
except json.JSONDecodeError as e:
    print(f"❌ Ошибка парсинга JSON: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Ошибка чтения файла: {e}")
    exit(1)

# Подключение
try:
    print("\nПодключение к Google Sheets...")
    creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, SCOPE)
    client = gspread.authorize(creds)
    print("✅ Авторизация успешна")
except Exception as e:
    print(f"❌ Ошибка авторизации: {e}")
    exit(1)

# Открытие таблицы
try:
    print(f"\nОткрытие таблицы {SPREADSHEET_ID}...")
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    print(f"✅ Таблица открыта: {spreadsheet.title}")
except Exception as e:
    print(f"❌ Ошибка открытия таблицы: {e}")
    print("   Проверьте:")
    print("   1. SPREADSHEET_ID правильный")
    print("   2. Service account email имеет доступ к таблице")
    print("   3. Таблица не удалена")
    exit(1)

# Чтение листа knowledge_db
try:
    print("\nЧтение листа 'knowledge_db'...")
    worksheet = spreadsheet.worksheet("knowledge_db")
    records = worksheet.get_all_records()
    print(f"✅ Лист найден, записей: {len(records)}")
    
    if len(records) > 0:
        print("\nПервые 3 записи:")
        for i, rec in enumerate(records[:3], 1):
            factor_name = rec.get("factor_name", "N/A")
            risk_group = rec.get("Risk_Group", "N/A")
            print(f"   {i}. {factor_name} ({risk_group})")
    
    # Проверка групп рисков
    risk_groups = set(r.get("Risk_Group", "") for r in records if r.get("Risk_Group"))
    print(f"\n✅ Групп рисков найдено: {len(risk_groups)}")
    print(f"   Группы: {', '.join(sorted(risk_groups))}")
    
except Exception as e:
    print(f"❌ Ошибка чтения листа: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО")
print("=" * 60)
print("\nCredentials.json работает корректно!")
print("Для Streamlit Cloud: используйте export_google_credentials_secret.py")
