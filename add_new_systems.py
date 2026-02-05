#!/usr/bin/env python3
"""
Скрипт для добавления 7 новых системных групп рисков в Google Sheets
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Конфигурация
SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
CREDENTIALS_FILE = "credentials.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Данные для новых систем
NEW_SYSTEMS_DATA = {
    "Metabolic": [
        {
            "factor_id": "M001",
            "factor_name": "Глюкоза (натощак)",
            "Weight_Coefficient": 0.25,
            "Threshold_High": 0.7,
            "Risk_Group": "Metabolic",
            "unit_type": "range",
            "unit_name": "ммоль/л",
            "norm_min": 3.9,
            "norm_max": 5.9,
            "min_val": 2.0,
            "max_val": 15.0,
            "recommendation": "Повышенный уровень глюкозы может указывать на риск развития диабета. Рекомендуется: снизить потребление простых углеводов, увеличить физическую активность, контролировать вес. При стойком повышении - консультация эндокринолога."
        },
        {
            "factor_id": "M002",
            "factor_name": "Инсулин",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Metabolic",
            "unit_type": "range",
            "unit_name": "мкЕд/мл",
            "norm_min": 2.0,
            "norm_max": 25.0,
            "min_val": 0.0,
            "max_val": 100.0,
            "recommendation": "Нарушение уровня инсулина может указывать на инсулинорезистентность. Рекомендуется: интервальное голодание, низкоуглеводная диета, регулярные физические нагрузки, контроль веса."
        },
        {
            "factor_id": "M003",
            "factor_name": "Гликированный гемоглобин (HbA1c)",
            "Weight_Coefficient": 0.25,
            "Threshold_High": 0.7,
            "Risk_Group": "Metabolic",
            "unit_type": "range",
            "unit_name": "%",
            "norm_min": 4.0,
            "norm_max": 6.0,
            "min_val": 3.0,
            "max_val": 15.0,
            "recommendation": "HbA1c отражает средний уровень глюкозы за 3 месяца. При повышении: контроль углеводов, регулярный мониторинг, консультация эндокринолога."
        },
        {
            "factor_id": "M004",
            "factor_name": "HOMA-IR (индекс инсулинорезистентности)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.6,
            "Risk_Group": "Metabolic",
            "unit_type": "range",
            "unit_name": "индекс",
            "norm_min": 0.0,
            "norm_max": 2.5,
            "min_val": 0.0,
            "max_val": 10.0,
            "recommendation": "Повышенный HOMA-IR указывает на инсулинорезистентность. Рекомендуется: низкоуглеводная диета, интервальное голодание, силовые тренировки, снижение веса."
        },
        {
            "factor_id": "M005",
            "factor_name": "Окружность талии",
            "Weight_Coefficient": 0.10,
            "Threshold_High": 0.5,
            "Risk_Group": "Metabolic",
            "unit_type": "range",
            "unit_name": "см",
            "norm_min": 70.0,
            "norm_max": 90.0,
            "min_val": 50.0,
            "max_val": 150.0,
            "recommendation": "Увеличенная окружность талии - маркер метаболического синдрома. Рекомендуется: снижение веса, кардио-тренировки, контроль питания, измерение регулярно."
        },
        {
            "factor_id": "M006",
            "factor_name": "ИМТ (индекс массы тела)",
            "Weight_Coefficient": 0.05,
            "Threshold_High": 0.5,
            "Risk_Group": "Metabolic",
            "unit_type": "range",
            "unit_name": "кг/м²",
            "norm_min": 18.5,
            "norm_max": 25.0,
            "min_val": 15.0,
            "max_val": 50.0,
            "recommendation": "ИМТ вне нормы увеличивает метаболические риски. Рекомендуется: сбалансированное питание, регулярная физическая активность, консультация диетолога при необходимости."
        }
    ],
    "Immune": [
        {
            "factor_id": "I001",
            "factor_name": "Лейкоциты",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Immune",
            "unit_type": "range",
            "unit_name": "×10⁹/л",
            "norm_min": 4.0,
            "norm_max": 9.0,
            "min_val": 2.0,
            "max_val": 20.0,
            "recommendation": "Отклонение уровня лейкоцитов может указывать на воспаление или иммунодефицит. Рекомендуется: консультация терапевта, дополнительные анализы при необходимости."
        },
        {
            "factor_id": "I002",
            "factor_name": "Лимфоциты",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Immune",
            "unit_type": "range",
            "unit_name": "%",
            "norm_min": 19.0,
            "norm_max": 37.0,
            "min_val": 10.0,
            "max_val": 60.0,
            "recommendation": "Лимфоциты - ключевые клетки иммунитета. При отклонениях: укрепление иммунитета через питание, сон, снижение стресса, консультация иммунолога."
        },
        {
            "factor_id": "I003",
            "factor_name": "Нейтрофилы",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.6,
            "Risk_Group": "Immune",
            "unit_type": "range",
            "unit_name": "%",
            "norm_min": 47.0,
            "norm_max": 72.0,
            "min_val": 30.0,
            "max_val": 80.0,
            "recommendation": "Нейтрофилы - первая линия защиты от инфекций. При отклонениях: укрепление иммунитета, консультация врача."
        },
        {
            "factor_id": "I004",
            "factor_name": "Иммуноглобулин A (IgA)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Immune",
            "unit_type": "range",
            "unit_name": "г/л",
            "norm_min": 0.7,
            "norm_max": 4.0,
            "min_val": 0.0,
            "max_val": 10.0,
            "recommendation": "IgA защищает слизистые оболочки. При снижении: укрепление местного иммунитета, пробиотики, консультация иммунолога."
        },
        {
            "factor_id": "I005",
            "factor_name": "Иммуноглобулин G (IgG)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Immune",
            "unit_type": "range",
            "unit_name": "г/л",
            "norm_min": 7.0,
            "norm_max": 16.0,
            "min_val": 3.0,
            "max_val": 25.0,
            "recommendation": "IgG - основной класс антител. При отклонениях: укрепление иммунитета, полноценное питание, консультация иммунолога."
        },
        {
            "factor_id": "I006",
            "factor_name": "Иммуноглобулин M (IgM)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Immune",
            "unit_type": "range",
            "unit_name": "г/л",
            "norm_min": 0.4,
            "norm_max": 2.3,
            "min_val": 0.0,
            "max_val": 5.0,
            "recommendation": "IgM - первичный иммунный ответ. При отклонениях: укрепление иммунитета, консультация иммунолога."
        }
    ],
    "Renal": [
        {
            "factor_id": "R001",
            "factor_name": "Креатинин",
            "Weight_Coefficient": 0.25,
            "Threshold_High": 0.7,
            "Risk_Group": "Renal",
            "unit_type": "range",
            "unit_name": "мкмоль/л",
            "norm_min": 62.0,
            "norm_max": 106.0,
            "min_val": 40.0,
            "max_val": 200.0,
            "recommendation": "Креатинин - маркер функции почек. При повышении: контроль потребления белка, достаточное питье, консультация нефролога."
        },
        {
            "factor_id": "R002",
            "factor_name": "Мочевина",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Renal",
            "unit_type": "range",
            "unit_name": "ммоль/л",
            "norm_min": 2.5,
            "norm_max": 8.3,
            "min_val": 1.0,
            "max_val": 15.0,
            "recommendation": "Мочевина отражает функцию почек и метаболизм белка. При повышении: контроль белка в питании, достаточное питье, консультация врача."
        },
        {
            "factor_id": "R003",
            "factor_name": "СКФ (скорость клубочковой фильтрации)",
            "Weight_Coefficient": 0.30,
            "Threshold_High": 0.7,
            "Risk_Group": "Renal",
            "unit_type": "range",
            "unit_name": "мл/мин/1.73м²",
            "norm_min": 90.0,
            "norm_max": 120.0,
            "min_val": 30.0,
            "max_val": 150.0,
            "recommendation": "СКФ - основной показатель функции почек. При снижении: контроль артериального давления, ограничение соли, консультация нефролога."
        },
        {
            "factor_id": "R004",
            "factor_name": "Мочевая кислота",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.6,
            "Risk_Group": "Renal",
            "unit_type": "range",
            "unit_name": "мкмоль/л",
            "norm_min": 200.0,
            "norm_max": 420.0,
            "min_val": 100.0,
            "max_val": 600.0,
            "recommendation": "Повышенная мочевая кислота - риск подагры и камней. Рекомендуется: ограничение пуринов, достаточное питье, консультация ревматолога."
        },
        {
            "factor_id": "R005",
            "factor_name": "Микроальбуминурия",
            "Weight_Coefficient": 0.10,
            "Threshold_High": 0.5,
            "Risk_Group": "Renal",
            "unit_type": "range",
            "unit_name": "мг/л",
            "norm_min": 0.0,
            "norm_max": 30.0,
            "min_val": 0.0,
            "max_val": 200.0,
            "recommendation": "Микроальбуминурия - ранний маркер поражения почек. При повышении: контроль АД, сахара, консультация нефролога."
        }
    ],
    "Hepatic": [
        {
            "factor_id": "H001",
            "factor_name": "АЛТ (аланинаминотрансфераза)",
            "Weight_Coefficient": 0.25,
            "Threshold_High": 0.7,
            "Risk_Group": "Hepatic",
            "unit_type": "range",
            "unit_name": "Ед/л",
            "norm_min": 7.0,
            "norm_max": 40.0,
            "min_val": 0.0,
            "max_val": 200.0,
            "recommendation": "АЛТ - маркер повреждения печени. При повышении: исключение алкоголя, гепатопротекторы, консультация гепатолога."
        },
        {
            "factor_id": "H002",
            "factor_name": "АСТ (аспартатаминотрансфераза)",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Hepatic",
            "unit_type": "range",
            "unit_name": "Ед/л",
            "norm_min": 10.0,
            "norm_max": 40.0,
            "min_val": 0.0,
            "max_val": 200.0,
            "recommendation": "АСТ отражает состояние печени и сердца. При повышении: исключение алкоголя, контроль питания, консультация врача."
        },
        {
            "factor_id": "H003",
            "factor_name": "Билирубин общий",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Hepatic",
            "unit_type": "range",
            "unit_name": "мкмоль/л",
            "norm_min": 3.4,
            "norm_max": 20.5,
            "min_val": 0.0,
            "max_val": 100.0,
            "recommendation": "Билирубин - маркер функции печени и желчевыводящих путей. При повышении: консультация гастроэнтеролога, УЗИ печени."
        },
        {
            "factor_id": "H004",
            "factor_name": "Билирубин прямой",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Hepatic",
            "unit_type": "range",
            "unit_name": "мкмоль/л",
            "norm_min": 0.0,
            "norm_max": 5.1,
            "min_val": 0.0,
            "max_val": 50.0,
            "recommendation": "Прямой билирубин указывает на проблемы с оттоком желчи. При повышении: консультация гастроэнтеролога, УЗИ."
        },
        {
            "factor_id": "H005",
            "factor_name": "ГГТ (гамма-глутамилтрансфераза)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.6,
            "Risk_Group": "Hepatic",
            "unit_type": "range",
            "unit_name": "Ед/л",
            "norm_min": 8.0,
            "norm_max": 61.0,
            "min_val": 0.0,
            "max_val": 300.0,
            "recommendation": "ГГТ чувствителен к алкоголю и токсинам. При повышении: исключение алкоголя, гепатопротекторы, консультация врача."
        },
        {
            "factor_id": "H006",
            "factor_name": "Щелочная фосфатаза",
            "Weight_Coefficient": 0.05,
            "Threshold_High": 0.5,
            "Risk_Group": "Hepatic",
            "unit_type": "range",
            "unit_name": "Ед/л",
            "norm_min": 40.0,
            "norm_max": 130.0,
            "min_val": 20.0,
            "max_val": 300.0,
            "recommendation": "ЩФ отражает состояние печени и костей. При отклонениях: консультация врача, дополнительные исследования."
        }
    ],
    "Bone": [
        {
            "factor_id": "B001",
            "factor_name": "Витамин D (25-OH)",
            "Weight_Coefficient": 0.30,
            "Threshold_High": 0.7,
            "Risk_Group": "Bone",
            "unit_type": "range",
            "unit_name": "нг/мл",
            "norm_min": 30.0,
            "norm_max": 100.0,
            "min_val": 10.0,
            "max_val": 150.0,
            "recommendation": "Витамин D критичен для костей и иммунитета. При дефиците: добавки витамина D, солнечные ванны, контроль уровня."
        },
        {
            "factor_id": "B002",
            "factor_name": "Кальций",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Bone",
            "unit_type": "range",
            "unit_name": "ммоль/л",
            "norm_min": 2.1,
            "norm_max": 2.6,
            "min_val": 1.5,
            "max_val": 3.5,
            "recommendation": "Кальций - основа костной ткани. При отклонениях: контроль питания, витамин D, консультация эндокринолога."
        },
        {
            "factor_id": "B003",
            "factor_name": "Фосфор",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Bone",
            "unit_type": "range",
            "unit_name": "ммоль/л",
            "norm_min": 0.87,
            "norm_max": 1.45,
            "min_val": 0.5,
            "max_val": 2.5,
            "recommendation": "Фосфор важен для костей и энергетического обмена. При отклонениях: контроль питания, консультация врача."
        },
        {
            "factor_id": "B004",
            "factor_name": "Паратгормон (ПТГ)",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Bone",
            "unit_type": "range",
            "unit_name": "пг/мл",
            "norm_min": 15.0,
            "norm_max": 65.0,
            "min_val": 5.0,
            "max_val": 150.0,
            "recommendation": "ПТГ регулирует кальций-фосфорный обмен. При отклонениях: консультация эндокринолога, контроль кальция и витамина D."
        },
        {
            "factor_id": "B005",
            "factor_name": "Остеокальцин",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Bone",
            "unit_type": "range",
            "unit_name": "нг/мл",
            "norm_min": 11.0,
            "norm_max": 43.0,
            "min_val": 5.0,
            "max_val": 100.0,
            "recommendation": "Остеокальцин - маркер костного обмена. При отклонениях: контроль витамина D, кальция, консультация эндокринолога."
        }
    ],
    "Oxidative": [
        {
            "factor_id": "O001",
            "factor_name": "Малоновый диальдегид (МДА)",
            "Weight_Coefficient": 0.25,
            "Threshold_High": 0.7,
            "Risk_Group": "Oxidative",
            "unit_type": "range",
            "unit_name": "мкмоль/л",
            "norm_min": 1.0,
            "norm_max": 4.0,
            "min_val": 0.0,
            "max_val": 15.0,
            "recommendation": "МДА - маркер окислительного стресса. При повышении: антиоксиданты (витамины C, E), снижение стресса, здоровое питание."
        },
        {
            "factor_id": "O002",
            "factor_name": "Глутатион",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Oxidative",
            "unit_type": "range",
            "unit_name": "мг/л",
            "norm_min": 5.0,
            "norm_max": 15.0,
            "min_val": 2.0,
            "max_val": 30.0,
            "recommendation": "Глутатион - главный антиоксидант. При снижении: добавки глутатиона, N-ацетилцистеин, селен, витамины группы B."
        },
        {
            "factor_id": "O003",
            "factor_name": "Витамин E",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Oxidative",
            "unit_type": "range",
            "unit_name": "мг/л",
            "norm_min": 5.0,
            "norm_max": 20.0,
            "min_val": 2.0,
            "max_val": 40.0,
            "recommendation": "Витамин E - жирорастворимый антиоксидант. При дефиците: добавки витамина E, орехи, растительные масла."
        },
        {
            "factor_id": "O004",
            "factor_name": "Витамин C",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Oxidative",
            "unit_type": "range",
            "unit_name": "мг/л",
            "norm_min": 4.0,
            "norm_max": 20.0,
            "min_val": 1.0,
            "max_val": 50.0,
            "recommendation": "Витамин C - водорастворимый антиоксидант. При дефиците: добавки витамина C, цитрусовые, овощи."
        },
        {
            "factor_id": "O005",
            "factor_name": "Коэнзим Q10",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Oxidative",
            "unit_type": "range",
            "unit_name": "мкг/мл",
            "norm_min": 0.5,
            "norm_max": 2.0,
            "min_val": 0.2,
            "max_val": 5.0,
            "recommendation": "Q10 важен для энергетики и антиоксидантной защиты. При снижении: добавки Q10, мясо, рыба, орехи."
        }
    ],
    "Inflammatory": [
        {
            "factor_id": "F001",
            "factor_name": "CRP высокочувствительный (hs-CRP)",
            "Weight_Coefficient": 0.30,
            "Threshold_High": 0.7,
            "Risk_Group": "Inflammatory",
            "unit_type": "range",
            "unit_name": "мг/л",
            "norm_min": 0.0,
            "norm_max": 3.0,
            "min_val": 0.0,
            "max_val": 20.0,
            "recommendation": "hs-CRP - маркер хронического воспаления. При повышении: противовоспалительная диета, контроль веса, физическая активность, консультация врача."
        },
        {
            "factor_id": "F002",
            "factor_name": "Фибриноген",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Inflammatory",
            "unit_type": "range",
            "unit_name": "г/л",
            "norm_min": 2.0,
            "norm_max": 4.0,
            "min_val": 1.0,
            "max_val": 8.0,
            "recommendation": "Фибриноген - маркер воспаления и свертываемости. При повышении: противовоспалительная диета, контроль веса, консультация врача."
        },
        {
            "factor_id": "F003",
            "factor_name": "Интерлейкин-6 (IL-6)",
            "Weight_Coefficient": 0.20,
            "Threshold_High": 0.6,
            "Risk_Group": "Inflammatory",
            "unit_type": "range",
            "unit_name": "пг/мл",
            "norm_min": 0.0,
            "norm_max": 3.0,
            "min_val": 0.0,
            "max_val": 20.0,
            "recommendation": "IL-6 - провоспалительный цитокин. При повышении: противовоспалительная диета, снижение стресса, консультация врача."
        },
        {
            "factor_id": "F004",
            "factor_name": "Фактор некроза опухоли-α (TNF-α)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Inflammatory",
            "unit_type": "range",
            "unit_name": "пг/мл",
            "norm_min": 0.0,
            "norm_max": 8.1,
            "min_val": 0.0,
            "max_val": 50.0,
            "recommendation": "TNF-α - маркер воспаления. При повышении: противовоспалительная диета, контроль веса, консультация врача."
        },
        {
            "factor_id": "F005",
            "factor_name": "СОЭ (скорость оседания эритроцитов)",
            "Weight_Coefficient": 0.15,
            "Threshold_High": 0.5,
            "Risk_Group": "Inflammatory",
            "unit_type": "range",
            "unit_name": "мм/ч",
            "norm_min": 2.0,
            "norm_max": 15.0,
            "min_val": 0.0,
            "max_val": 50.0,
            "recommendation": "СОЭ - неспецифический маркер воспаления. При повышении: консультация врача, дополнительные исследования."
        }
    ]
}

def add_new_systems():
    """Добавляет новые системы в Google Sheets"""
    try:
        # Подключение
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        
        # Получаем заголовки
        headers = sheet.row_values(1)
        print(f"Заголовки: {headers}")
        
        # Подготавливаем данные для вставки
        rows_to_add = []
        
        for system_name, factors in NEW_SYSTEMS_DATA.items():
            print(f"\nДобавление системы: {system_name} ({len(factors)} факторов)")
            
            for factor in factors:
                row = []
                for header in headers:
                    if header in factor:
                        row.append(str(factor[header]))
                    else:
                        row.append("")
                rows_to_add.append(row)
        
        # Добавляем все строки одним запросом (более эффективно)
        if rows_to_add:
            sheet.append_rows(rows_to_add)
            print(f"\n✅ Успешно добавлено {len(rows_to_add)} записей")
        else:
            print("❌ Нет данных для добавления")
        
        # Проверяем результат
        all_records = sheet.get_all_records()
        print(f"\nВсего записей в базе: {len(all_records)}")
        
        # Проверяем группы
        risk_groups = {}
        for record in all_records:
            group = record.get('Risk_Group', '')
            if group:
                risk_groups[group] = risk_groups.get(group, 0) + 1
        
        print("\nРаспределение по группам:")
        for group, count in sorted(risk_groups.items()):
            print(f"  - {group}: {count} факторов")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 80)
    print("ДОБАВЛЕНИЕ 7 НОВЫХ СИСТЕМНЫХ ГРУПП РИСКОВ")
    print("=" * 80)
    add_new_systems()
