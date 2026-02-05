#!/usr/bin/env python3
"""
Добавление групп «Желудок» (Gastric) и «Глаза» (Ocular) в knowledge_db.
Интегральные показатели для оценки рисков желудочно-кишечной и офтальмологической систем.
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

# Желудок (Gastric) — интегральные показатели: секреторная функция, атрофия, H. pylori, всасывание
GASTRIC_FACTORS = [
    {
        "factor_id": "GAS001",
        "factor_name": "Пепсиноген I",
        "Risk_Group": "Gastric",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "нг/мл",
        "norm_min": 30.0,
        "norm_max": 160.0,
        "min_val": 10.0,
        "max_val": 300.0,
        "recommendation": "Снижение пепсиногена I может указывать на атрофический гастрит. Рекомендуется: консультация гастроэнтеролога, при необходимости гастроскопия и тест на H. pylori.",
    },
    {
        "factor_id": "GAS002",
        "factor_name": "Пепсиноген II",
        "Risk_Group": "Gastric",
        "Weight_Coefficient": 0.20,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "нг/мл",
        "norm_min": 3.0,
        "norm_max": 15.0,
        "min_val": 1.0,
        "max_val": 50.0,
        "recommendation": "Отклонение пепсиногена II связано с состоянием слизистой желудка. При изменениях — консультация гастроэнтеролога, контроль в паре с пепсиногеном I.",
    },
    {
        "factor_id": "GAS003",
        "factor_name": "Гастрин-17 (базальный)",
        "Risk_Group": "Gastric",
        "Weight_Coefficient": 0.20,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "пмоль/л",
        "norm_min": 1.0,
        "norm_max": 7.0,
        "min_val": 0.5,
        "max_val": 30.0,
        "recommendation": "Гастрин-17 отражает кислотность и состояние антрального отдела. При отклонениях — консультация гастроэнтеролога, при необходимости гастроскопия.",
    },
    {
        "factor_id": "GAS004",
        "factor_name": "Anti-Helicobacter pylori IgG",
        "Risk_Group": "Gastric",
        "Weight_Coefficient": 0.20,
        "Threshold_High": 0.5,
        "unit_type": "range",
        "unit_name": "коэф. позитивности (S/CO)",
        "norm_min": 0.0,
        "norm_max": 0.9,
        "min_val": 0.0,
        "max_val": 5.0,
        "recommendation": "Положительный результат указывает на контакт с H. pylori. При клинике и по решению врача — эрадикационная терапия, контроль после лечения.",
    },
    {
        "factor_id": "GAS005",
        "factor_name": "Витамин B12",
        "Risk_Group": "Gastric",
        "Weight_Coefficient": 0.15,
        "Threshold_High": 0.5,
        "unit_type": "range",
        "unit_name": "пг/мл",
        "norm_min": 200.0,
        "norm_max": 900.0,
        "min_val": 100.0,
        "max_val": 1500.0,
        "recommendation": "Снижение B12 может быть связано с нарушением всасывания в желудке (атрофия, недостаток фактора Касла). При дефиците — консультация врача, при необходимости препараты B12.",
    },
]

# Глаза (Ocular) — интегральные показатели: ВГД, питание сетчатки, сосудистый и метаболический риск
OCULAR_FACTORS = [
    {
        "factor_id": "OCU001",
        "factor_name": "ВГД (внутриглазное давление)",
        "Risk_Group": "Ocular",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "мм рт. ст.",
        "norm_min": 10.0,
        "norm_max": 21.0,
        "min_val": 5.0,
        "max_val": 40.0,
        "recommendation": "Повышенное ВГД — фактор риска глаукомы. Рекомендуется: контроль у офтальмолога, соблюдение режима капель при назначении, ограничение избыточной жидкости и кофеина.",
    },
    {
        "factor_id": "OCU002",
        "factor_name": "Витамин A (ретинол)",
        "Risk_Group": "Ocular",
        "Weight_Coefficient": 0.25,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "мкг/дл",
        "norm_min": 30.0,
        "norm_max": 100.0,
        "min_val": 10.0,
        "max_val": 200.0,
        "recommendation": "Ретинол необходим для сетчатки и сумеречного зрения. При дефиците — коррекция питания (печень, морковь, зелень), при выраженном дефиците — добавки по назначению врача.",
    },
    {
        "factor_id": "OCU003",
        "factor_name": "Гомоцистеин",
        "Risk_Group": "Ocular",
        "Weight_Coefficient": 0.20,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "мкмоль/л",
        "norm_min": 5.0,
        "norm_max": 15.0,
        "min_val": 3.0,
        "max_val": 50.0,
        "recommendation": "Повышенный гомоцистеин увеличивает сосудистый риск, в т.ч. для сосудов сетчатки. Рекомендуется: фолиевая кислота, B6, B12 по назначению врача, контроль уровня.",
    },
    {
        "factor_id": "OCU004",
        "factor_name": "Глюкоза (натощак)",
        "Risk_Group": "Ocular",
        "Weight_Coefficient": 0.15,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "ммоль/л",
        "norm_min": 3.9,
        "norm_max": 5.9,
        "min_val": 2.0,
        "max_val": 15.0,
        "recommendation": "Повышенная глюкоза — фактор риска диабетической ретинопатии. Контроль углеводов, регулярный мониторинг глюкозы и осмотры офтальмолога при диабете.",
    },
    {
        "factor_id": "OCU005",
        "factor_name": "С-реактивный белок (CRP)",
        "Risk_Group": "Ocular",
        "Weight_Coefficient": 0.15,
        "Threshold_High": 0.6,
        "unit_type": "range",
        "unit_name": "мг/л",
        "norm_min": 0.0,
        "norm_max": 3.0,
        "min_val": 0.0,
        "max_val": 20.0,
        "recommendation": "Хроническое воспаление связано с риском сосудистых и воспалительных заболеваний глаз. Противовоспалительная диета, контроль веса, при стойком повышении — консультация врача.",
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

        all_factors = GASTRIC_FACTORS + OCULAR_FACTORS
        rows_to_add = []
        for factor in all_factors:
            row = [str(factor.get(h, "")) if factor.get(h, "") != "" else "" for h in headers]
            rows_to_add.append(row)

        sheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")

        print("✅ Добавлены группы «Желудок» (Gastric) и «Глаза» (Ocular):")
        print("\nЖелудок (Gastric):")
        for f in GASTRIC_FACTORS:
            print(f"   - {f['factor_name']} ({f['unit_name']}): норма {f['norm_min']}–{f['norm_max']}")
        print("\nГлаза (Ocular):")
        for f in OCULAR_FACTORS:
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
    print("ДОБАВЛЕНИЕ ГРУПП: ЖЕЛУДОК (Gastric), ГЛАЗА (Ocular)")
    print("=" * 60)
    add_groups()
