#!/usr/bin/env python3
"""
1. Удаление из группы Neuro показателя «качество питания».
2. Удаление дубликатов в костно-мышечной группе (Musculoskeletal):
   - MU002 (Витамин D) — дублирует B001 в той же группе.
   - MU004 (Креатинин) — уже оценивается в группе Renal (R001); в костно-мышечной группе лишний.
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


def run():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")

        all_values = sheet.get_all_values()
        if not all_values:
            print("❌ Таблица пуста")
            return

        headers = all_values[0]
        if "Risk_Group" not in headers or "factor_name" not in headers or "factor_id" not in headers:
            print("❌ Нет колонок Risk_Group, factor_name или factor_id")
            return

        risk_group_idx = headers.index("Risk_Group")
        factor_name_idx = headers.index("factor_name")
        factor_id_idx = headers.index("factor_id")

        # Собираем номера строк для удаления (1-based)
        rows_to_delete = []
        data_rows = all_values[1:]
        for i, row in enumerate(data_rows):
            row_num = i + 2  # 1-based
            if len(row) <= risk_group_idx:
                continue
            rg = (row[risk_group_idx] or "").strip()
            fn = (row[factor_name_idx] or "").strip().lower() if factor_name_idx < len(row) else ""
            fid = (row[factor_id_idx] or "").strip() if factor_id_idx < len(row) else ""

            # Neuro: убрать показатель про качество питания (по названию или factor_id)
            if rg == "Neuro" and ("питание" in fn or fid == "food_qual"):
                name = row[factor_name_idx].strip() if factor_name_idx < len(row) else fid
                rows_to_delete.append((row_num, f"Neuro: {name}"))
            # Musculoskeletal: убрать дубликат витамина D (MU002) и креатинин (MU004)
            if rg == "Musculoskeletal" and fid in ("MU002", "MU004"):
                rows_to_delete.append((row_num, f"Musculoskeletal: {fid} {row[factor_name_idx] if factor_name_idx < len(row) else fid}"))

        if not rows_to_delete:
            print("Нет строк, подходящих под условия удаления.")
            return

        # Удаляем с конца, чтобы номера строк не сбивались
        rows_to_delete.sort(key=lambda x: x[0], reverse=True)
        for row_num, label in rows_to_delete:
            sheet.delete_rows(row_num)
            print(f"   Удалена строка {row_num}: {label}")

        print(f"\n✅ Удалено строк: {len(rows_to_delete)}")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("УДАЛЕНИЕ: НЕЙРО — ПИТАНИЕ; КОСТНО-МЫШЕЧНАЯ — ДУБЛИКАТЫ")
    print("=" * 60)
    run()
