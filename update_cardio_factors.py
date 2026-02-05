#!/usr/bin/env python3
"""
Скрипт замены показателей в группе Cardio на новый набор:
Креатинкиназа, Липидограмма, ЛДГ, Глюкоза, Калий/натрий/хлор.
Границы и нормы — референсные значения для взрослых.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
CREDENTIALS_FILE = "credentials.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Новый набор показателей Cardio (нормы для взрослых)
CARDIO_FACTORS = [
    {
        "factor_id": "C001",
        "factor_name": "Креатинкиназа",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.18,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "Ед/л",
        "norm_min": 24,
        "norm_max": 195,
        "min_val": 0,
        "max_val": 2000,
        "recommendation": "Повышение КФК может указывать на повреждение мышц или миокарда. Исключите физическую нагрузку за 24–48 ч до повторного анализа. При стойком повышении — ЭКГ, тропонины, консультация кардиолога.",
    },
    {
        "factor_id": "C002",
        "factor_name": "Липидограмма (общий холестерин)",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.18,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 3.0,
        "norm_max": 5.2,
        "min_val": 2.0,
        "max_val": 12.0,
        "recommendation": "При повышении холестерина: снижение насыщенных жиров, увеличение клетчатки, омега-3, контроль веса, физическая активность. При высоком риске — консультация кардиолога и решение о гиполипидемической терапии.",
    },
    {
        "factor_id": "C003",
        "factor_name": "Лактатдегидрогиназа (ЛДГ)",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.18,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "Ед/л",
        "norm_min": 125,
        "norm_max": 250,
        "min_val": 50,
        "max_val": 1000,
        "recommendation": "Повышение ЛДГ возможно при повреждении тканей (сердце, печень, мышцы, эритроциты). Исключите гемолиз пробы. Повторный анализ, при необходимости — ЭКГ, УЗИ сердца, консультация терапевта.",
    },
    {
        "factor_id": "C004",
        "factor_name": "Глюкоза",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.18,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 3.9,
        "norm_max": 6.1,
        "min_val": 2.0,
        "max_val": 25.0,
        "recommendation": "Контроль глюкозы важен для сердечно-сосудистого риска. При повышении: диета с ограничением простых углеводов, движение, контроль веса. При стойкой гипергликемии — HbA1c и консультация эндокринолога.",
    },
    {
        "factor_id": "C005",
        "factor_name": "Калий",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.1,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 3.5,
        "norm_max": 5.1,
        "min_val": 2.0,
        "max_val": 7.0,
        "recommendation": "Гипо- и гиперкалиемия влияют на ритм сердца и проводимость. При отклонениях — повторный анализ (исключить гемолиз), ЭКГ, коррекция по назначению врача.",
    },
    {
        "factor_id": "C006",
        "factor_name": "Натрий",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.09,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 136,
        "norm_max": 145,
        "min_val": 120,
        "max_val": 160,
        "recommendation": "Нарушения натрия связаны с объёмом жидкости и риском отёков, АД. Контроль питьевого режима и диуреза, при стойких отклонениях — консультация терапевта/нефролога.",
    },
    {
        "factor_id": "C007",
        "factor_name": "Хлор",
        "Risk_Group": "Cardio",
        "Weight_Coefficient": 0.09,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 98,
        "norm_max": 106,
        "min_val": 85,
        "max_val": 120,
        "recommendation": "Отклонения хлора часто сопутствуют изменениям натрия и кислотно-щелочного баланса. Интерпретация вместе с Na и K, при необходимости — повторный анализ и консультация врача.",
    },
]


def update_cardio():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")

        # Загружаем все данные
        all_values = sheet.get_all_values()
        if not all_values:
            print("❌ Таблица пуста")
            return

        headers = all_values[0]
        data_rows = all_values[1:]

        # Убедимся, что все нужные колонки есть
        required = [
            "factor_id", "factor_name", "Risk_Group", "Weight_Coefficient",
            "Threshold_High", "unit_type", "unit_name", "norm_min", "norm_max",
            "min_val", "max_val", "recommendation",
        ]
        missing = [h for h in required if h not in headers]
        if missing:
            print(f"⚠️ В таблице нет колонок: {missing}")
            print(f"   Заголовки: {headers}")
            return

        # Убираем строки Cardio, остальное оставляем
        rest_rows = []
        for row in data_rows:
            if len(row) <= headers.index("Risk_Group"):
                rest_rows.append(row)
                continue
            risk_group = row[headers.index("Risk_Group")].strip()
            if risk_group != "Cardio":
                rest_rows.append(row)

        # Формируем строки для новых Cardio-факторов
        cardio_rows = []
        for factor in CARDIO_FACTORS:
            row = []
            for h in headers:
                val = factor.get(h, "")
                row.append(str(val) if val != "" else "")
            cardio_rows.append(row)

        # Собираем новые данные: заголовок + все строки без Cardio + новые Cardio
        new_data = [headers] + rest_rows + cardio_rows

        # Очищаем лист и записываем заново
        sheet.clear()
        sheet.update(range_name="A1", values=new_data, value_input_option="USER_ENTERED")

        print("✅ Группа Cardio заменена на новый набор показателей:")
        for f in CARDIO_FACTORS:
            print(f"   - {f['factor_name']} ({f['unit_name']}): норма {f['norm_min']}–{f['norm_max']}")
        print(f"\nВсего записей в таблице: {len(rest_rows) + len(cardio_rows)}")
        print(f"Из них Cardio: {len(cardio_rows)}")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ЗАМЕНА ПОКАЗАТЕЛЕЙ В ГРУППЕ CARDIO")
    print("=" * 60)
    update_cardio()
