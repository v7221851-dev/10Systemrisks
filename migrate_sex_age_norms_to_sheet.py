#!/usr/bin/env python3
"""
Перенос пол-зависимых норм из кода в Google Sheets (knowledge_db),
чтобы врач мог редактировать их напрямую в таблице.

Что делает скрипт:
- Добавляет в лист `knowledge_db` колонки:
  norm_min_M, norm_max_M, norm_min_F, norm_max_F (если их ещё нет).
- Для выбранных показателей (factor_id) заполняет эти колонки значениями
  из текущего словаря SEX_AGE_NORMS (как было в коде app.py).

После запуска:
- Врач может менять значения norm_min_M / norm_max_M / norm_min_F / norm_max_F в таблице.
- Приложение берёт пол-зависимые нормы только из таблицы (см. apply_sex_age_norms в app.py).
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

# Исходные пол-зависимые нормы, которые раньше были зашиты в app.py
SEX_AGE_NORMS = {
    "R001": {"M": (62.0, 106.0), "F": (53.0, 97.0)},    # Креатинин (мкмоль/л)
    "MU004": {"M": (62.0, 106.0), "F": (53.0, 97.0)},   # Креатинин в группе мышц
    "R004": {"M": (200.0, 420.0), "F": (140.0, 340.0)}, # Мочевая кислота (мкмоль/л)
    "SK002": {"M": (30.0, 300.0), "F": (10.0, 150.0)},  # Ферритин (мкг/л)
    "M005": {"M": (80.0, 94.0), "F": (70.0, 80.0)},     # Окружность талии (см), IDF
}

NEW_COLS = ["norm_min_M", "norm_max_M", "norm_min_F", "norm_max_F"]


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
        if "factor_id" not in headers:
            print("❌ Нет колонки factor_id")
            return

        # Добавляем недостающие колонки в заголовок
        updated_headers = list(headers)
        for col in NEW_COLS:
            if col not in updated_headers:
                updated_headers.append(col)

        if updated_headers != headers:
            # Перезаписываем строку заголовков (A1: ...), остальные строки не трогаем
            sheet.update("A1", [updated_headers])
            print(f"✅ Добавлены колонки: {', '.join(c for c in NEW_COLS if c not in headers)}")
            headers = updated_headers

        factor_id_idx = headers.index("factor_id")
        col_idx = {name: headers.index(name) + 1 for name in NEW_COLS}  # 1-based

        updated_rows = 0
        data_rows = all_values[1:]
        for i, row in enumerate(data_rows, start=2):  # строки с 2-й (1-based)
            if factor_id_idx >= len(row):
                continue
            fid = (row[factor_id_idx] or "").strip()
            if fid not in SEX_AGE_NORMS:
                continue

            norms = SEX_AGE_NORMS[fid]
            m_min, m_max = norms["M"]
            f_min, f_max = norms["F"]

            # Записываем значения в соответствующие колонки
            sheet.update_cell(i, col_idx["norm_min_M"], m_min)
            sheet.update_cell(i, col_idx["norm_max_M"], m_max)
            sheet.update_cell(i, col_idx["norm_min_F"], f_min)
            sheet.update_cell(i, col_idx["norm_max_F"], f_max)

            updated_rows += 1
            print(f"   {fid}: M=({m_min}-{m_max}), F=({f_min}-{f_max})")

        if updated_rows == 0:
            print("Нет строк с подходящими factor_id для обновления.")
        else:
            print(f"\n✅ Обновлено строк с пол-зависимыми нормами: {updated_rows}")
            print("Теперь врач может редактировать norm_min_M/norm_max_M/norm_min_F/norm_max_F в Google Sheets.")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("МИГРАЦИЯ ПОЛ-ЗАВИСИМЫХ НОРМ В GOOGLE SHEETS")
    print("=" * 60)
    run()

