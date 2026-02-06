#!/usr/bin/env python3
"""
Распределение весов для группы Hepatic по данным гепатологии.

Обоснование (ACG/EASL, оценка повреждения и функции печени):
- АЛТ — наиболее специфичный маркер гепатоцеллюлярного повреждения, ассоциирован с печеночной смертностью → высший вес.
- АСТ — гепатоцеллюлярное повреждение, соотношение АСТ/АЛТ при гепатитах → высокий вес.
- Билирубин общий — функция печени, прогноз → высокий вес.
- ГГТ — холестаз, алкоголь, уточнение при повышении ЩФ → высокий вес.
- Билирубин прямой — холестаз, отток желчи → умеренный вес.
- Щелочная фосфатаза — холестатический паттерн (печень/кости) → умеренный вес.
- Общий белок — белково-синтетическая функция печени → умеренный вес.
- Холестерин — синтез в печени, менее специфичен для поражения печени → низкий вес.
- СРБ — неспецифичное воспаление → низкий вес.
- Триглицериды — липидный обмен, NAFLD/жировой гепатоз → умеренный вес.
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

# Веса по factor_id (сумма = 1.0). Холестерин (C002) и СРБ (F001) вынесены в Cardio/Inflammatory — в Hepatic не дублируются.
HEPATIC_WEIGHTS = {
    "H001": 0.208,  # АЛТ — основной маркер повреждения гепатоцитов
    "H002": 0.176,  # АСТ — повреждение печени/гепатит
    "H003": 0.165,  # Билирубин общий — функция, прогноз
    "H004": 0.110,  # Билирубин прямой — холестаз
    "H005": 0.132,  # ГГТ — желчные пути, алкоголь
    "H006": 0.088,  # Щелочная фосфатаза — холестатический паттерн
    "H008": 0.066,  # Общий белок — синтетическая функция
    "H010": 0.055,  # Триглицериды — липидный обмен, NAFLD/жировой гепатоз
}


def update_hepatic_weights():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        all_values = sheet.get_all_values()
        headers = all_values[0]

        if "Weight_Coefficient" not in headers or "Risk_Group" not in headers or "factor_id" not in headers:
            print("❌ В таблице нет колонок Weight_Coefficient, Risk_Group или factor_id")
            return

        col_w = headers.index("Weight_Coefficient") + 1
        col_grp = headers.index("Risk_Group") + 1
        col_fid = headers.index("factor_id") + 1

        updated = 0
        for i in range(1, len(all_values)):
            row = all_values[i]
            if len(row) < max(col_w, col_grp, col_fid):
                continue
            if row[col_grp - 1] != "Hepatic":
                continue
            fid = (row[col_fid - 1] or "").strip()
            if fid not in HEPATIC_WEIGHTS:
                print(f"   ⚠️ Неизвестный factor_id в Hepatic: '{fid}' (строка {i + 1})")
                continue
            new_weight = HEPATIC_WEIGHTS[fid]
            sheet.update_cell(i + 1, col_w, new_weight)
            updated += 1
            print(f"   {fid}: Weight_Coefficient = {new_weight}")

        print(f"\n✅ Обновлено весов: {updated}")
        print(f"   Сумма весов Hepatic: {sum(HEPATIC_WEIGHTS.values()):.2f}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ВЕСА ГРУППЫ HEPATIC ПО ДАННЫМ ГЕПАТОЛОГИИ")
    print("=" * 60)
    for fid, w in HEPATIC_WEIGHTS.items():
        print(f"  {fid}: {w}")
    print("  ---")
    print(f"  Сумма: {sum(HEPATIC_WEIGHTS.values())}")
    print("=" * 60)
    update_hepatic_weights()
