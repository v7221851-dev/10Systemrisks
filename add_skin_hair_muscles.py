#!/usr/bin/env python3
"""
Добавление групп «Кожа и волосы» и «Мышцы» в knowledge_db.
Показатели и нормы — референсные значения для взрослых.
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

# Кожа и волосы (референсные нормы для взрослых)
SKIN_HAIR_FACTORS = [
    {
        "factor_id": "SK001",
        "factor_name": "Витамин D (25-OH)",
        "Risk_Group": "SkinHair",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "нг/мл",
        "norm_min": 30,
        "norm_max": 100,
        "min_val": 5,
        "max_val": 150,
        "recommendation": "Дефицит витамина D ухудшает состояние кожи и волос. Рекомендуется: пребывание на солнце, добавки по назначению врача, контроль уровня через 2–3 месяца.",
    },
    {
        "factor_id": "SK002",
        "factor_name": "Ферритин",
        "Risk_Group": "SkinHair",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "мкг/л",
        "norm_min": 30,
        "norm_max": 200,
        "min_val": 5,
        "max_val": 500,
        "recommendation": "Низкий ферритин часто связан с выпадением волос и сухостью кожи. При дефиците — диета, богатая железом, при необходимости препараты железа по назначению врача.",
    },
    {
        "factor_id": "SK003",
        "factor_name": "Цинк (сыворотка)",
        "Risk_Group": "SkinHair",
        "Weight_Coefficient": 0.2,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "мкмоль/л",
        "norm_min": 12,
        "norm_max": 24,
        "min_val": 5,
        "max_val": 40,
        "recommendation": "Дефицит цинка сказывается на коже и волосах. Коррекция питания (мясо, орехи, бобовые), при выраженном дефиците — препараты цинка по назначению врача.",
    },
    {
        "factor_id": "SK004",
        "factor_name": "ТТГ",
        "Risk_Group": "SkinHair",
        "Weight_Coefficient": 0.15,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "мМЕ/л",
        "norm_min": 0.4,
        "norm_max": 4.0,
        "min_val": 0.1,
        "max_val": 10.0,
        "recommendation": "Гипотиреоз часто проявляется сухостью кожи и выпадением волос. При отклонениях ТТГ — консультация эндокринолога, при необходимости УЗИ щитовидной железы.",
    },
    {
        "factor_id": "SK005",
        "factor_name": "Селен",
        "Risk_Group": "SkinHair",
        "Weight_Coefficient": 0.15,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "мкг/л",
        "norm_min": 70,
        "norm_max": 150,
        "min_val": 30,
        "max_val": 250,
        "recommendation": "Селен участвует в защите кожи и волос. Коррекция питания (орехи, морепродукты), при дефиците — добавки по назначению врача.",
    },
]

# Мышцы (референсные нормы для взрослых)
MUSCLES_FACTORS = [
    {
        "factor_id": "MU001",
        "factor_name": "Креатинкиназа (КФК)",
        "Risk_Group": "Muscles",
        "Weight_Coefficient": 0.3,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "Ед/л",
        "norm_min": 24,
        "norm_max": 195,
        "min_val": 0,
        "max_val": 2000,
        "recommendation": "Повышение КФК отражает повреждение скелетных мышц или миокарда. Исключите нагрузку за 24–48 ч до повторного анализа. При стойком повышении — консультация невролога/кардиолога.",
    },
    {
        "factor_id": "MU002",
        "factor_name": "Витамин D (25-OH)",
        "Risk_Group": "Muscles",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "нг/мл",
        "norm_min": 30,
        "norm_max": 100,
        "min_val": 5,
        "max_val": 150,
        "recommendation": "Дефицит витамина D снижает тонус и силу мышц. Коррекция: солнце, добавки по назначению врача, адекватная физическая нагрузка.",
    },
    {
        "factor_id": "MU003",
        "factor_name": "Магний (сыворотка)",
        "Risk_Group": "Muscles",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 0.7,
        "norm_max": 1.0,
        "min_val": 0.4,
        "max_val": 1.5,
        "recommendation": "Низкий магний способствует судорогам и мышечной слабости. Диета (зелень, орехи, бобовые), при дефиците — препараты магния по назначению врача.",
    },
    {
        "factor_id": "MU004",
        "factor_name": "Креатинин",
        "Risk_Group": "Muscles",
        "Weight_Coefficient": 0.2,
        "Threshold_High": 2.5,
        "unit_type": "range",
        "unit_name": "мкмоль/л",
        "norm_min": 53,
        "norm_max": 106,
        "min_val": 30,
        "max_val": 150,
        "recommendation": "Креатинин отражает мышечный метаболизм и функцию почек. Снижение при малой мышечной массе, повышение при почечной недостаточности. Интерпретация вместе с СКФ, при необходимости — консультация нефролога.",
    },
]


def add_groups():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")

        headers = sheet.row_values(1)
        if not headers:
            print("❌ Таблица пуста или заголовки не найдены")
            return

        required = [
            "factor_id", "factor_name", "Risk_Group", "Weight_Coefficient",
            "Threshold_High", "unit_type", "unit_name", "norm_min", "norm_max",
            "min_val", "max_val", "recommendation",
        ]
        missing = [h for h in required if h not in headers]
        if missing:
            print(f"⚠️ В таблице нет колонок: {missing}")
            return

        all_factors = SKIN_HAIR_FACTORS + MUSCLES_FACTORS
        rows_to_add = []
        for factor in all_factors:
            row = [str(factor.get(h, "")) if factor.get(h, "") != "" else "" for h in headers]
            rows_to_add.append(row)

        sheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")

        print("✅ Добавлены группы «Кожа и волосы» и «Мышцы»:")
        print("\nКожа и волосы (SkinHair):")
        for f in SKIN_HAIR_FACTORS:
            print(f"   - {f['factor_name']} ({f['unit_name']}): норма {f['norm_min']}–{f['norm_max']}")
        print("\nМышцы (Muscles):")
        for f in MUSCLES_FACTORS:
            print(f"   - {f['factor_name']} ({f['unit_name']}): норма {f['norm_min']}–{f['norm_max']}")
        print(f"\nВсего добавлено записей: {len(rows_to_add)}")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ДОБАВЛЕНИЕ ГРУПП: КОЖА И ВОЛОСЫ, МЫШЦЫ")
    print("=" * 60)
    add_groups()
