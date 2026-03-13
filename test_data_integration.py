#!/usr/bin/env python3
"""
Проверка связки данных: загрузка из Google Таблицы, нормализация весов, расчёт баллов.
Запуск: python3 test_data_integration.py
Требуется: credentials.json или GOOGLE_CREDENTIALS_JSON.
"""

import sys

def main():
    print("1. Загрузка данных (validate_data.load_data)...")
    try:
        from validate_data import load_data
    except ImportError:
        print("❌ Не найден validate_data.py")
        return 1
    df = load_data()
    if df is None or df.empty:
        print("❌ Данные не загружены")
        return 1
    print(f"   Загружено строк: {len(df)}, групп: {df['Risk_Group'].nunique()}")

    print("2. Нормализация Weight_Coefficient по группам (как в app)...")
    if "Weight_Coefficient" not in df.columns or "Risk_Group" not in df.columns:
        print("   ❌ Нет колонок Weight_Coefficient или Risk_Group")
        return 1
    df = df.copy()
    for group in df["Risk_Group"].dropna().unique():
        mask = df["Risk_Group"] == group
        total = df.loc[mask, "Weight_Coefficient"].sum()
        if total > 0:
            df.loc[mask, "Weight_Coefficient"] = df.loc[mask, "Weight_Coefficient"] / total

    print("3. Проверка: сумма весов в каждой группе = 1.0")
    ok = True
    for group in df["Risk_Group"].dropna().unique():
        s = df[df["Risk_Group"] == group]["Weight_Coefficient"].sum()
        if abs(s - 1.0) > 0.001:
            print(f"   ❌ {group}: сумма = {s:.4f}")
            ok = False
        else:
            print(f"   ✅ {group}: {s:.4f}")
    if not ok:
        return 1

    print("4. Пробный расчёт балла по одной группе...")
    risk_groups = df["Risk_Group"].dropna().unique()
    if len(risk_groups) == 0:
        print("   ❌ Нет групп")
        return 1
    group = risk_groups[0]
    g_df = df[df["Risk_Group"] == group]
    # Имитация ввода: всем факторам группы балл 4.0
    user_inputs = {r["factor_id"]: 4.0 for _, r in g_df.iterrows()}
    total_w = g_df["Weight_Coefficient"].sum()
    raw_score = sum(user_inputs.get(r["factor_id"], 0) * r["Weight_Coefficient"] for _, r in g_df.iterrows())
    group_score = raw_score / total_w if total_w > 0 else 0
    print(f"   Группа {group}: total_w={total_w:.4f}, raw_score={raw_score:.4f}, group_score={group_score:.4f}")
    if total_w < 0.99 or group_score <= 0:
        print("   ❌ Некорректный расчёт")
        return 1
    print("   ✅ Расчёт корректен")

    print("\n✅ Связка данных готова к тестированию приложения.")
    print("   Запуск приложения: streamlit run app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
