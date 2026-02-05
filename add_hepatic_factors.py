#!/usr/bin/env python3
"""
Добавление в печеночную группу рисков (Hepatic):
- Холестерин (общий)
- Общий белок
- СРБ (С-реактивный белок)

АСТ (Аспартат аминотрансфераза) уже есть в группе как H002 — используется для оценки гепатита.
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

# Новые факторы для Hepatic (H007, H008, H009)
HEPATIC_NEW_FACTORS = [
    {
        "factor_id": "H007",
        "factor_name": "Холестерин общий",
        "Weight_Coefficient": 0.10,
        "Threshold_High": 0.6,
        "Risk_Group": "Hepatic",
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 3.0,
        "norm_max": 5.2,
        "min_val": 2.0,
        "max_val": 10.0,
        "recommendation": "Холестерин учитывается в печеночном риске (синтез в печени, липидный обмен). При повышении: снижение насыщенных жиров, клетчатка, омега-3, контроль веса, при необходимости консультация гепатолога/кардиолога.",
    },
    {
        "factor_id": "H008",
        "factor_name": "Общий белок",
        "Weight_Coefficient": 0.10,
        "Threshold_High": 0.6,
        "Risk_Group": "Hepatic",
        "unit_type": "range",
        "unit_name": "г/л",
        "norm_min": 65.0,
        "norm_max": 85.0,
        "min_val": 50.0,
        "max_val": 120.0,
        "recommendation": "Общий белок отражает белково-синтетическую функцию печени и питательный статус. При отклонениях: консультация терапевта/гастроэнтеролога, оценка питания, при необходимости дообследование печени.",
    },
    {
        "factor_id": "H009",
        "factor_name": "СРБ (С-реактивный белок)",
        "Weight_Coefficient": 0.08,
        "Threshold_High": 0.6,
        "Risk_Group": "Hepatic",
        "unit_type": "range",
        "unit_name": "мг/л",
        "norm_min": 0.0,
        "norm_max": 5.0,
        "min_val": 0.0,
        "max_val": 100.0,
        "recommendation": "СРБ — маркер воспаления; при поражении печени (гепатит, стеатоз) может быть повышен. При повышении: исключение алкоголя, контроль веса, при стойком повышении — консультация врача и дообследование.",
    },
]


def add_hepatic_factors():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        headers = sheet.row_values(1)
        print("Заголовки:", headers)

        rows_to_add = []
        for factor in HEPATIC_NEW_FACTORS:
            row = []
            for header in headers:
                row.append(str(factor.get(header, "")))
            rows_to_add.append(row)

        if rows_to_add:
            sheet.append_rows(rows_to_add)
            print(f"\n✅ В группу Hepatic добавлено {len(rows_to_add)} факторов:")
            for f in HEPATIC_NEW_FACTORS:
                print(f"   - {f['factor_id']}: {f['factor_name']}")
        else:
            print("❌ Нет данных для добавления")

        # Нормализация весов Hepatic до суммы 1.0
        all_values = sheet.get_all_values()
        headers = all_values[0]
        if "Weight_Coefficient" not in headers or "Risk_Group" not in headers:
            print("\n⚠️ Колонки Weight_Coefficient или Risk_Group не найдены, нормализация пропущена.")
        else:
            col_w = headers.index("Weight_Coefficient") + 1  # 1-based
            col_grp = headers.index("Risk_Group") + 1
            hepatic_rows = []
            for i in range(1, len(all_values)):
                row = all_values[i]
                if len(row) >= max(col_w, col_grp) and row[col_grp - 1] == "Hepatic":
                    try:
                        w = float(row[col_w - 1].replace(",", "."))
                    except (ValueError, TypeError):
                        w = 0.0
                    hepatic_rows.append((i + 1, w))  # row index 1-based, weight
            if hepatic_rows:
                total_w = sum(w for _, w in hepatic_rows)
                if total_w > 0:
                    for row_idx, old_w in hepatic_rows:
                        new_w = round(old_w / total_w, 4)
                        sheet.update_cell(row_idx, col_w, new_w)
                    print(f"\n✅ Веса Hepatic нормализованы (было {total_w:.4f}, стало сумма 1.0).")

        all_records = sheet.get_all_records()
        hepatic_count = sum(1 for r in all_records if r.get("Risk_Group") == "Hepatic")
        print(f"\nВсего факторов в группе Hepatic: {hepatic_count}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ДОБАВЛЕНИЕ ФАКТОРОВ В ПЕЧЕНОЧНУЮ ГРУППУ (Hepatic)")
    print("  Холестерин общий, Общий белок, СРБ")
    print("=" * 60)
    add_hepatic_factors()
