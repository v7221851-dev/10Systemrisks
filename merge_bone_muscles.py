#!/usr/bin/env python3
"""
Объединение групп Bone (костная система) и Muscles (мышцы) в одну группу
Musculoskeletal (костно-мышечная система) — общие лабораторные показатели.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
CREDENTIALS_FILE = "credentials.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

NEW_GROUP_NAME = "Musculoskeletal"


def merge_groups():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")

        all_values = sheet.get_all_values()
        if not all_values:
            print("❌ Таблица пуста")
            return

        headers = all_values[0]
        if "Risk_Group" not in headers:
            print("❌ Колонка Risk_Group не найдена")
            return

        risk_group_idx = headers.index("Risk_Group")
        updated = 0

        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) <= risk_group_idx:
                continue
            current = row[risk_group_idx].strip()
            if current in ("Bone", "Muscles"):
                sheet.update_cell(row_idx, risk_group_idx + 1, NEW_GROUP_NAME)
                updated += 1
                factor_name = row[headers.index("factor_name")] if "factor_name" in headers and len(row) > headers.index("factor_name") else "?"
                print(f"   Строка {row_idx}: {current} → Musculoskeletal ({factor_name})")

        print(f"\n✅ Группы Bone и Muscles объединены в «{NEW_GROUP_NAME}» (Костно-мышечная система).")
        print(f"   Обновлено записей: {updated}")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ОБЪЕДИНЕНИЕ: КОСТНАЯ СИСТЕМА + МЫШЦЫ → КОСТНО-МЫШЕЧНАЯ СИСТЕМА")
    print("=" * 60)
    merge_groups()
