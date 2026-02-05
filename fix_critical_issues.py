#!/usr/bin/env python3
"""
Скрипт для исправления критических ошибок в базе данных:
1. Исправление диапазона холестерина (norm_min)
2. Нормализация весов в группе Cardio
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

def fix_issues():
    """Исправляет критические ошибки в базе данных."""
    try:
        # Подключение к Google Sheets
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        
        # Получаем все данные
        all_values = sheet.get_all_values()
        headers = all_values[0]
        data_rows = all_values[1:]
        
        # Находим индексы колонок
        norm_min_idx = headers.index('norm_min')
        min_val_idx = headers.index('min_val')
        factor_name_idx = headers.index('factor_name')
        weight_idx = headers.index('Weight_Coefficient')
        risk_group_idx = headers.index('Risk_Group')
        
        print("=" * 80)
        print("ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ ОШИБОК В БАЗЕ ДАННЫХ")
        print("=" * 80)
        
        # Исправление 1: Холестерин - norm_min
        print("\n1. ИСПРАВЛЕНИЕ ДИАПАЗОНА ХОЛЕСТЕРИНА")
        print("-" * 80)
        
        for i, row in enumerate(data_rows, start=2):  # start=2 потому что строка 1 - заголовки
            if len(row) > factor_name_idx:
                factor_name = row[factor_name_idx] if factor_name_idx < len(row) else ''
                
                if 'холестерин' in factor_name.lower():
                    current_norm_min = row[norm_min_idx] if norm_min_idx < len(row) else ''
                    current_min_val = row[min_val_idx] if min_val_idx < len(row) else ''
                    
                    print(f"Найдена запись: {factor_name}")
                    print(f"  Текущие значения: min_val={current_min_val}, norm_min={current_norm_min}")
                    
                    # Исправляем norm_min на 3.0 (медицинский стандарт)
                    new_norm_min = "3.0"
                    sheet.update_cell(i, norm_min_idx + 1, new_norm_min)  # +1 потому что Google Sheets использует 1-based индексацию
                    
                    print(f"  ✅ Исправлено: norm_min изменен с {current_norm_min} на {new_norm_min}")
                    break
        
        # Исправление 2: Нормализация весов в группе Cardio
        print("\n2. НОРМАЛИЗАЦИЯ ВЕСОВ В ГРУППЕ CARDIO")
        print("-" * 80)
        
        # Коэффициент нормализации: 1.0 / 0.8 = 1.25
        normalization_factor = 1.25
        
        # Новые веса после нормализации
        new_weights = {
            'Артериальное давление (сист.)': 0.4 * normalization_factor,  # 0.5
            'Уровень холестерина': 0.2 * normalization_factor,  # 0.25
            'Уровень ЧСС (покой)': 0.1 * normalization_factor,  # 0.125
            'С-реактивный белок': 0.1 * normalization_factor,  # 0.125
        }
        
        print(f"Коэффициент нормализации: {normalization_factor}")
        print(f"Новые веса:")
        for name, weight in new_weights.items():
            print(f"  - {name}: {weight:.3f}")
        
        for i, row in enumerate(data_rows, start=2):
            if len(row) > factor_name_idx and len(row) > risk_group_idx:
                factor_name = row[factor_name_idx] if factor_name_idx < len(row) else ''
                risk_group = row[risk_group_idx] if risk_group_idx < len(row) else ''
                
                if risk_group == 'Cardio' and factor_name in new_weights:
                    current_weight = row[weight_idx] if weight_idx < len(row) else '0'
                    new_weight = str(new_weights[factor_name])
                    
                    print(f"\nОбновление: {factor_name}")
                    print(f"  Старый вес: {current_weight}")
                    print(f"  Новый вес: {new_weight}")
                    
                    sheet.update_cell(i, weight_idx + 1, new_weight)
                    print(f"  ✅ Обновлено")
        
        print("\n" + "=" * 80)
        print("✅ ВСЕ КРИТИЧЕСКИЕ ОШИБКИ ИСПРАВЛЕНЫ")
        print("=" * 80)
        
        # Проверка результатов
        print("\n3. ПРОВЕРКА РЕЗУЛЬТАТОВ")
        print("-" * 80)
        
        all_values = sheet.get_all_values()
        data_rows = all_values[1:]
        
        # Проверяем холестерин
        for i, row in enumerate(data_rows, start=2):
            if len(row) > factor_name_idx:
                factor_name = row[factor_name_idx] if factor_name_idx < len(row) else ''
                if 'холестерин' in factor_name.lower():
                    norm_min = row[norm_min_idx] if norm_min_idx < len(row) else ''
                    min_val = row[min_val_idx] if min_val_idx < len(row) else ''
                    print(f"Холестерин: min_val={min_val}, norm_min={norm_min}")
                    if float(norm_min) >= float(min_val):
                        print("  ✅ Диапазон исправлен корректно")
                    else:
                        print("  ⚠️ Требуется дополнительная проверка")
        
        # Проверяем сумму весов Cardio
        cardio_total = 0.0
        print("\nCardio группа - веса:")
        for i, row in enumerate(data_rows, start=2):
            if len(row) > risk_group_idx:
                risk_group = row[risk_group_idx] if risk_group_idx < len(row) else ''
                if risk_group == 'Cardio' and len(row) > weight_idx:
                    factor_name = row[factor_name_idx] if factor_name_idx < len(row) else ''
                    weight = float(row[weight_idx]) if weight_idx < len(row) and row[weight_idx] else 0.0
                    cardio_total += weight
                    print(f"  - {factor_name}: {weight:.3f}")
        
        print(f"\nСумма весов Cardio: {cardio_total:.3f}")
        if abs(cardio_total - 1.0) < 0.01:
            print("  ✅ Веса нормализованы корректно")
        else:
            print(f"  ⚠️ Сумма весов = {cardio_total:.3f} (ожидается 1.0)")
        
    except Exception as e:
        print(f"\n❌ Ошибка при исправлении: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_issues()
