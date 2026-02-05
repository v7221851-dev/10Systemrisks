#!/usr/bin/env python3
"""
Добавление столбца «Описание_системы» в knowledge_db и заполнение его
краткими описаниями для каждой системы рисков.
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

COLUMN_NAME = "Описание_системы"

SYSTEM_DESCRIPTIONS = {
    "Neuro": "Нервная система — оценка рисков неврологических нарушений по показателям, связанным с функцией нервной системы и обменом веществ, влияющим на мозг и периферические нервы.",
    "Cardio": "Сердце и сосуды — оценка кардиорисков по маркерам повреждения миокарда, липидам, глюкозе и электролитам (калий, натрий, хлор).",
    "Hormone": "Щитовидная железа — оценка функции щитовидной железы и связанных с ней рисков по гормональным и метаболическим показателям.",
    "Metabolic": "Метаболизм — оценка рисков диабета и метаболического синдрома: глюкоза, инсулин, HbA1c, HOMA-IR, окружность талии и ИМТ.",
    "Immune": "Иммунитет — оценка состояния иммунной системы по лейкоцитам, лимфоцитам, нейтрофилам и иммуноглобулинам (IgA, IgG, IgM).",
    "Renal": "Почки — оценка функции почек и риска ХБП по креатинину, мочевине, СКФ, мочевой кислоте и микроальбуминурии.",
    "Hepatic": "Печень и желчные пути — оценка функции печени и риска гепатита по АЛТ, АСТ (аспартат аминотрансфераза), билирубину, ГГТ, щелочной фосфатазе, холестерину, общему белку и СРБ.",
    "Bone": "Кости и мышцы — оценка минерального обмена и состояния костной и мышечной ткани (витамин D, кальций, фосфор, ПТГ, остеокальцин, КФК, магний, креатинин).",
    "Musculoskeletal": "Кости и мышцы — оценка минерального обмена и состояния костной и мышечной ткани (витамин D, кальций, фосфор, ПТГ, остеокальцин, КФК, магний, креатинин).",
    "Muscles": "Костно-мышечная система — см. описание «Кости и мышцы».",
    "Oxidative": "Окислительный стресс — оценка антиоксидантной защиты и повреждения окислением (МДА, глутатион, витамины E и C, коэнзим Q10).",
    "Inflammatory": "Системное воспаление — оценка фона хронического воспаления по hs-CRP, фибриногену, IL-6, TNF-α и СОЭ.",
    "SkinHair": "Кожа и волосы — оценка факторов, влияющих на состояние кожи и волос: витамин D, ферритин, цинк, ТТГ и селен.",
}


def add_descriptions():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")

        all_values = sheet.get_all_values()
        if not all_values:
            print("❌ Таблица пуста")
            return

        headers = all_values[0]
        data_rows = all_values[1:]

        if "Risk_Group" not in headers:
            print("❌ В таблице нет колонки Risk_Group")
            return

        risk_group_idx = headers.index("Risk_Group")

        # Добавляем столбец, если его ещё нет
        if COLUMN_NAME not in headers:
            headers = list(headers) + [COLUMN_NAME]
        desc_col_idx = headers.index(COLUMN_NAME)

        # Собираем новые строки: у каждой строки значение в столбце описания по Risk_Group
        new_data = [headers]
        for row in data_rows:
            row_extended = list(row)
            while len(row_extended) < len(headers):
                row_extended.append("")
            risk_group = row_extended[risk_group_idx].strip() if risk_group_idx < len(row_extended) else ""
            desc = SYSTEM_DESCRIPTIONS.get(risk_group, "")
            if desc_col_idx < len(row_extended):
                row_extended[desc_col_idx] = desc
            else:
                row_extended.append(desc)
            new_data.append(row_extended)

        sheet.clear()
        sheet.update(range_name="A1", values=new_data, value_input_option="USER_ENTERED")

        print(f"✅ Столбец «{COLUMN_NAME}» добавлен/обновлён в knowledge_db.")
        print(f"   Заполнено описаний для {len(data_rows)} строк.")
        groups_filled = set(
            row[risk_group_idx].strip() for row in data_rows
            if risk_group_idx < len(row) and row[risk_group_idx].strip() in SYSTEM_DESCRIPTIONS
        )
        print(f"   Систем с описанием: {len(groups_filled)}")

    except FileNotFoundError:
        print(f"❌ Файл {CREDENTIALS_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("ДОБАВЛЕНИЕ СТОЛБЦА «ОПИСАНИЕ_СИСТЕМЫ» В GOOGLE SHEETS")
    print("=" * 60)
    add_descriptions()
