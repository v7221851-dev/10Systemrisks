#!/usr/bin/env python3
"""
Проверка формата GOOGLE_CREDENTIALS_JSON для Railway
Показывает, как должна выглядеть переменная окружения
"""
import json
import os

CRED_FILE = "credentials.json"

print("=" * 60)
print("ПРОВЕРКА ФОРМАТА ДЛЯ RAILWAY")
print("=" * 60)

if not os.path.exists(CRED_FILE):
    print(f"❌ Файл {CRED_FILE} не найден!")
    exit(1)

# Читаем JSON
try:
    with open(CRED_FILE, "r", encoding="utf-8") as f:
        creds_data = json.load(f)
    print("✅ JSON файл валиден")
except Exception as e:
    print(f"❌ Ошибка чтения JSON: {e}")
    exit(1)

# Минифицируем JSON (убираем пробелы и переносы строк)
json_string = json.dumps(creds_data, separators=(',', ':'))

print("\n" + "=" * 60)
print("ДЛЯ RAILWAY → Settings → Variables:")
print("=" * 60)
print("\n1. Name (имя переменной):")
print("   GOOGLE_CREDENTIALS_JSON")
print("\n2. Value (значение) - скопируйте ВСЮ строку ниже:")
print("-" * 60)
print(json_string)
print("-" * 60)

print("\n" + "=" * 60)
print("ВАЖНО:")
print("=" * 60)
print("✅ Вставляйте ТОЛЬКО содержимое между линиями выше")
print("✅ БЕЗ префикса 'GOOGLE_CREDENTIALS_JSON ='")
print("✅ БЕЗ кавычек вокруг JSON")
print("✅ БЕЗ тройных кавычек '''")
print("✅ Вся строка должна быть одной строкой (без переносов)")
print("\nПосле добавления переменной Railway автоматически перезапустит деплой.")
