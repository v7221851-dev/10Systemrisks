#!/usr/bin/env python3
"""
Скрипт для валидации данных в базе знаний для анализа рисков
сердечных, неврологических и гормональных заболеваний.
"""

import gspread
import pandas as pd
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
from typing import Dict, List, Tuple

# Конфигурация
SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
CREDENTIALS_FILE = "credentials.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Медицинские референсные диапазоны для проверки (примерные)
MEDICAL_REFERENCE_RANGES = {
    # Сердечно-сосудистые показатели
    'артериальное давление': {'systolic': (90, 140), 'diastolic': (60, 90)},
    'пульс': (60, 100),
    'холестерин': (3.0, 5.2),  # ммоль/л
    'ldl': (0, 3.0),  # ммоль/л
    'hdl': (1.0, 2.5),  # ммоль/л
    'триглицериды': (0.5, 1.7),  # ммоль/л
    
    # Неврологические показатели
    'кортизол': (138, 690),  # нмоль/л утром
    'дофамин': (0.1, 0.5),  # нмоль/л
    'серотонин': (0.5, 1.5),  # мкмоль/л
    'норадреналин': (0.6, 3.0),  # нмоль/л
    
    # Гормональные показатели
    'тестостерон': (10, 35),  # нмоль/л (мужчины)
    'эстрадиол': (0.1, 0.3),  # нмоль/л (женщины, фолликулярная фаза)
    'пролактин': (2, 25),  # нг/мл
    'ттг': (0.4, 4.0),  # мМЕ/л
    'т4': (10, 25),  # пмоль/л
    'инсулин': (2, 25),  # мкЕд/мл
    'глюкоза': (3.9, 5.9),  # ммоль/л (натощак)
}

def load_data():
    """Загружает данные из Google Sheets."""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        df = pd.DataFrame(sheet.get_all_records())
        
        # Преобразование числовых колонок
        num_cols = ['Weight_Coefficient', 'Threshold_High', 'min_val', 'max_val', 'norm_min', 'norm_max']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return None

def check_completeness(df: pd.DataFrame) -> List[str]:
    """Проверяет полноту данных."""
    issues = []
    required_cols = ['factor_id', 'factor_name', 'Risk_Group', 'Weight_Coefficient', 
                     'min_val', 'max_val', 'norm_min', 'norm_max', 'unit_type']
    
    # Проверка наличия колонок
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        issues.append(f"⚠️ Отсутствуют обязательные колонки: {', '.join(missing_cols)}")
    
    # Проверка пропусков в данных
    for col in required_cols:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                issues.append(f"⚠️ Пропущено значений в колонке '{col}': {missing_count} ({missing_count/len(df)*100:.1f}%)")
    
    return issues

def check_value_ranges(df: pd.DataFrame) -> List[str]:
    """Проверяет логическую согласованность диапазонов значений."""
    issues = []
    
    range_rows = df[df['unit_type'].str.contains('range', case=False, na=False)]
    
    for idx, row in range_rows.iterrows():
        factor_name = row.get('factor_name', f'ID:{row.get("factor_id", idx)}')
        
        # Проверка наличия всех необходимых значений
        required_vals = ['min_val', 'max_val', 'norm_min', 'norm_max']
        if any(pd.isna(row.get(v)) for v in required_vals):
            issues.append(f"⚠️ {factor_name}: отсутствуют значения диапазонов")
            continue
        
        min_val = float(row['min_val'])
        max_val = float(row['max_val'])
        norm_min = float(row['norm_min'])
        norm_max = float(row['norm_max'])
        
        # Проверка: min_val <= norm_min <= norm_max <= max_val
        if min_val > max_val:
            issues.append(f"❌ {factor_name}: min_val ({min_val}) > max_val ({max_val})")
        
        if norm_min > norm_max:
            issues.append(f"❌ {factor_name}: norm_min ({norm_min}) > norm_max ({norm_max})")
        
        if norm_min < min_val:
            issues.append(f"⚠️ {factor_name}: norm_min ({norm_min}) < min_val ({min_val}) - норма выходит за допустимый диапазон")
        
        if norm_max > max_val:
            issues.append(f"⚠️ {factor_name}: norm_max ({norm_max}) > max_val ({max_val}) - норма выходит за допустимый диапазон")
        
        # Проверка на нулевые или отрицательные диапазоны (если не должны быть)
        if min_val == max_val:
            issues.append(f"⚠️ {factor_name}: min_val == max_val ({min_val}) - диапазон равен нулю")
        
        if norm_min == norm_max and norm_min != 0:
            issues.append(f"⚠️ {factor_name}: нормальный диапазон равен одной точке ({norm_min})")
    
    return issues

def _normalize_weight_sum(raw_sum: float) -> float:
    """В таблице веса могут быть в шкале 1000 = 1.0; приводим к 0..1 для проверки."""
    if pd.isna(raw_sum):
        return raw_sum
    if raw_sum >= 10:
        return raw_sum / 1000.0
    return raw_sum


def check_weights(df: pd.DataFrame) -> List[str]:
    """Проверяет корректность весовых коэффициентов (сумма по группе = 1.0; в таблице может быть 1000 = 1.0)."""
    issues = []
    
    # Проверка наличия весов
    if 'Weight_Coefficient' not in df.columns:
        issues.append("❌ Колонка Weight_Coefficient отсутствует")
        return issues
    
    # Проверка на отрицательные веса (уже в нормализованной шкале или сырой — отрицательное всё равно ошибка)
    negative_weights = df[df['Weight_Coefficient'] < 0]
    if len(negative_weights) > 0:
        issues.append(f"⚠️ Найдено {len(negative_weights)} факторов с отрицательными весами")
        for idx, row in negative_weights.iterrows():
            issues.append(f"   - {row.get('factor_name', 'Unknown')}: {row['Weight_Coefficient']}")
    
    # Проверка весов по группам рисков (1000 в таблице = 1.0)
    risk_groups = df['Risk_Group'].dropna().unique()
    for group in risk_groups:
        group_df = df[df['Risk_Group'] == group]
        total_raw = group_df['Weight_Coefficient'].sum()
        total_norm = _normalize_weight_sum(total_raw)
        
        if total_raw == 0:
            issues.append(f"⚠️ Группа '{group}': сумма весов равна 0")
        elif total_raw < 0:
            issues.append(f"❌ Группа '{group}': сумма весов отрицательная ({total_raw:.3f})")
        else:
            # Проверка: после нормализации (1000→1.0) сумма должна быть 1.0
            if abs(total_norm - 1.0) > 0.01:
                issues.append(f"ℹ️ Группа '{group}': сумма весов = {total_norm:.3f} (ожидается 1.0, в таблице: {total_raw:.0f})")
    
    return issues

def check_thresholds(df: pd.DataFrame) -> List[str]:
    """Проверяет корректность пороговых значений."""
    issues = []
    
    if 'Threshold_High' not in df.columns:
        return issues
    
    for idx, row in df.iterrows():
        threshold = row.get('Threshold_High')
        if pd.isna(threshold):
            continue
        
        threshold = float(threshold)
        
        # Порог должен быть в диапазоне [0, 1] для риска
        if threshold < 0 or threshold > 1:
            factor_name = row.get('factor_name', f'ID:{row.get("factor_id", idx)}')
            issues.append(f"⚠️ {factor_name}: Threshold_High ({threshold}) вне диапазона [0, 1]")
    
    return issues

def check_medical_validity(df: pd.DataFrame) -> List[str]:
    """Проверяет медицинскую валидность нормальных диапазонов."""
    issues = []
    
    range_rows = df[df['unit_type'].str.contains('range', case=False, na=False)]
    
    for idx, row in range_rows.iterrows():
        factor_name = str(row.get('factor_name', '')).lower()
        unit_name = str(row.get('unit_name', '')).lower()
        
        # Попытка найти соответствие в медицинских референсах
        found_match = False
        for ref_key, ref_value in MEDICAL_REFERENCE_RANGES.items():
            if ref_key in factor_name or ref_key in unit_name:
                found_match = True
                
                if isinstance(ref_value, tuple):
                    ref_min, ref_max = ref_value
                    norm_min = row.get('norm_min')
                    norm_max = row.get('norm_max')
                    
                    if pd.notna(norm_min) and pd.notna(norm_max):
                        # Проверка, находится ли норма в референсном диапазоне
                        if norm_min < ref_min or norm_max > ref_max:
                            issues.append(
                                f"⚠️ {row.get('factor_name')}: норма ({norm_min}-{norm_max}) "
                                f"выходит за медицинский референс ({ref_min}-{ref_max})"
                            )
                break
        
        # Если не найдено соответствие, но есть подозрительные значения
        if not found_match:
            norm_min = row.get('norm_min')
            norm_max = row.get('norm_max')
            if pd.notna(norm_min) and pd.notna(norm_max):
                # Проверка на разумность диапазона
                if norm_max - norm_min < 0:
                    issues.append(f"⚠️ {row.get('factor_name')}: нормальный диапазон некорректен")
    
    return issues

def check_group_distribution(df: pd.DataFrame) -> List[str]:
    """Проверяет распределение факторов по группам рисков."""
    issues = []
    
    risk_groups = df['Risk_Group'].dropna().unique()
    
    if len(risk_groups) == 0:
        issues.append("❌ Не найдено групп рисков")
        return issues
    
    issues.append(f"\n📊 Распределение факторов по группам:")
    for group in risk_groups:
        group_df = df[df['Risk_Group'] == group]
        count = len(group_df)
        total_raw = group_df['Weight_Coefficient'].sum()
        total_display = _normalize_weight_sum(total_raw)
        issues.append(f"   - {group}: {count} факторов, сумма весов: {total_display:.3f}")
        
        # Проверка на пустые группы
        if count == 0:
            issues.append(f"⚠️ Группа '{group}' пуста")
    
    return issues

def generate_report(df: pd.DataFrame) -> str:
    """Генерирует полный отчет о валидности данных."""
    report = []
    report.append("=" * 80)
    report.append("ОТЧЕТ О ВАЛИДНОСТИ ДАННЫХ ДЛЯ АНАЛИЗА РИСКОВ ЗАБОЛЕВАНИЙ")
    report.append("=" * 80)
    report.append(f"\nВсего записей в базе: {len(df)}")
    report.append(f"Групп рисков: {len(df['Risk_Group'].dropna().unique())}")
    report.append("\n" + "-" * 80)
    
    # 1. Полнота данных
    report.append("\n1. ПРОВЕРКА ПОЛНОТЫ ДАННЫХ")
    report.append("-" * 80)
    completeness_issues = check_completeness(df)
    if completeness_issues:
        report.extend(completeness_issues)
    else:
        report.append("✅ Все обязательные поля заполнены")
    
    # 2. Диапазоны значений
    report.append("\n2. ПРОВЕРКА ДИАПАЗОНОВ ЗНАЧЕНИЙ")
    report.append("-" * 80)
    range_issues = check_value_ranges(df)
    if range_issues:
        report.extend(range_issues)
    else:
        report.append("✅ Все диапазоны значений корректны")
    
    # 3. Весовые коэффициенты
    report.append("\n3. ПРОВЕРКА ВЕСОВЫХ КОЭФФИЦИЕНТОВ")
    report.append("-" * 80)
    weight_issues = check_weights(df)
    if weight_issues:
        report.extend(weight_issues)
    else:
        report.append("✅ Все весовые коэффициенты корректны")
    
    # 4. Пороговые значения
    report.append("\n4. ПРОВЕРКА ПОРОГОВЫХ ЗНАЧЕНИЙ")
    report.append("-" * 80)
    threshold_issues = check_thresholds(df)
    if threshold_issues:
        report.extend(threshold_issues)
    else:
        report.append("✅ Все пороговые значения корректны")
    
    # 5. Медицинская валидность
    report.append("\n5. ПРОВЕРКА МЕДИЦИНСКОЙ ВАЛИДНОСТИ")
    report.append("-" * 80)
    medical_issues = check_medical_validity(df)
    if medical_issues:
        report.extend(medical_issues)
    else:
        report.append("✅ Нормальные диапазоны соответствуют медицинским стандартам")
    
    # 6. Распределение по группам
    report.append("\n6. РАСПРЕДЕЛЕНИЕ ПО ГРУППАМ РИСКОВ")
    report.append("-" * 80)
    group_issues = check_group_distribution(df)
    report.extend(group_issues)
    
    # Итоговая оценка
    report.append("\n" + "=" * 80)
    report.append("ИТОГОВАЯ ОЦЕНКА")
    report.append("=" * 80)
    
    all_issues = completeness_issues + range_issues + weight_issues + threshold_issues + medical_issues
    critical_issues = [i for i in all_issues if i.startswith("❌")]
    warnings = [i for i in all_issues if i.startswith("⚠️")]
    info = [i for i in all_issues if i.startswith("ℹ️") or i.startswith("📊")]
    
    report.append(f"\nКритические ошибки: {len(critical_issues)}")
    report.append(f"Предупреждения: {len(warnings)}")
    report.append(f"Информационные сообщения: {len(info)}")
    
    if len(critical_issues) == 0 and len(warnings) == 0:
        report.append("\n✅ ДАННЫЕ ВАЛИДНЫ И ГОТОВЫ К ИСПОЛЬЗОВАНИЮ")
    elif len(critical_issues) == 0:
        report.append("\n⚠️ ДАННЫЕ В ОСНОВНОМ КОРРЕКТНЫ, НО ЕСТЬ ПРЕДУПРЕЖДЕНИЯ")
    else:
        report.append("\n❌ ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ОШИБКИ - ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ")
    
    return "\n".join(report)

def main():
    """Основная функция."""
    print("Загрузка данных из Google Sheets...")
    df = load_data()
    
    if df is None:
        print("Не удалось загрузить данные. Проверьте подключение.")
        return
    
    print(f"✅ Загружено {len(df)} записей\n")
    
    # Генерация отчета
    report = generate_report(df)
    print(report)
    
    # Сохранение отчета в файл
    with open("validation_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n\nОтчет сохранен в файл: validation_report.txt")

if __name__ == "__main__":
    main()
