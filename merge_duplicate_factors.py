#!/usr/bin/env python3
"""
Объединение дубликатов в knowledge_db:

1. Холестерин: оставить один параметр C002, удалить H007.
   - C002: canonical name «Холестерин общий, ммоль/л» (объединяет «Липидограмма (общий холестерин)» и «Холестерин общий»).

2. СРБ: оставить один параметр F001, удалить H009 и OCU005.
   - F001: canonical name «СРБ (С-реактивный белок), мг/л» (объединяет С-реактивный белок (CRP), СРБ, hs-CRP).

Перед запуском: сделайте бэкап таблицы. После запуска выполните update_hepatic_weights.py.
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

# Удалить эти factor_id (дубликаты холестерина и СРБ)
REMOVE_FACTOR_IDS = {"H007", "H009", "OCU005"}

# Канонические названия оставляемых параметров
CANONICAL_NAMES = {
    "C002": "Холестерин общий, ммоль/л",
    "F001": "СРБ (С-реактивный белок), мг/л",
}


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
        if "factor_id" not in headers or "factor_name" not in headers:
            print("❌ Нет колонок factor_id или factor_name")
            return

        factor_id_idx = headers.index("factor_id")
        factor_name_idx = headers.index("factor_name")

        rows_to_delete = []
        updates = []  # (row_num_1based, factor_name_col_1based, new_name)

        for i in range(1, len(all_values)):
            row = all_values[i]
            row_num = i + 1
            if len(row) <= max(factor_id_idx, factor_name_idx):
                continue
            fid = (row[factor_id_idx] or "").strip()
            fname = (row[factor_name_idx] or "").strip()

            if fid in REMOVE_FACTOR_IDS:
                rows_to_delete.append((row_num, f"{fid} — {fname}"))
            elif fid in CANONICAL_NAMES:
                new_name = CANONICAL_NAMES[fid]
                if fname != new_name:
                    updates.append((row_num, factor_name_idx + 1, new_name))

        # Сначала обновляем названия
        for row_num, col_num, new_name in updates:
            sheet.update_cell(row_num, col_num, new_name)
            print(f"   Обновлено: строка {row_num} → «{new_name}»")

        # Удаляем дубликаты с конца
        rows_to_delete.sort(key=lambda x: x[0], reverse=True)
        for row_num, label in rows_to_delete:
            sheet.delete_rows(row_num)
            print(f"   Удалена строка {row_num}: {label}")

        if updates:
            print(f"\n✅ Обновлено названий: {len(updates)}")
        if rows_to_delete:
            print(f"✅ Удалено дубликатов: {len(rows_to_delete)}")
        if not updates and not rows_to_delete:
            print("Нет изменений (дубликаты уже удалены, названия уже канонические).")
        else:
            print("\nРекомендуется запустить: python update_hepatic_weights.py")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ОБЪЕДИНЕНИЕ ДУБЛИКАТОВ: ХОЛЕСТЕРИН (C002), СРБ (F001)")
    print("=" * 60)
    run()
