#!/usr/bin/env python3
"""
Читает credentials.json и выводит строку для секрета GOOGLE_CREDENTIALS_JSON
(для вставки в Streamlit Cloud → Secrets).
Запуск: python3 export_google_credentials_secret.py
Файл credentials.json должен лежать в текущей папке.
"""
import json
import os

CRED_FILE = "credentials.json"
if not os.path.exists(CRED_FILE):
    print(f"Файл {CRED_FILE} не найден. Положите его в папку с проектом и запустите снова.")
    exit(1)

with open(CRED_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Одна строка JSON (без лишних пробелов/переносов)
one_line = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

print("Скопируйте строку ниже целиком и вставьте в Secrets на share.streamlit.io:")
print()
print("ВАРИАНТ 1 (тройные кавычки — рекомендуется для TOML):")
print("GOOGLE_CREDENTIALS_JSON = '''" + one_line + "'''")
print()
print("ВАРИАНТ 2 (одинарные кавычки, если вариант 1 не работает):")
escaped = one_line.replace("\\", "\\\\").replace("'", "''")
print("GOOGLE_CREDENTIALS_JSON = '" + escaped + "'")
print()
print("(Рекомендуется использовать вариант 1 с тройными кавычками '''...''')")
