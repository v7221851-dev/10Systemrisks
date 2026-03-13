#!/usr/bin/env python3
"""
Анализ обновлённой базы в Google Таблице:
- список и проверка factor_id
- проверка Weight_Coefficient внутри каждой Risk_Group (сумма должна быть 1.0)
"""

import os
import sys
import json
import tempfile
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_credentials_path():
    """Путь к credentials: GOOGLE_CREDENTIALS_JSON или credentials.json."""
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw:
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            # попробуем как путь к файлу
            if os.path.isfile(raw):
                return raw
            return None
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        f.write(raw)
        f.close()
        return f.name
    if os.path.isfile("credentials.json"):
        return "credentials.json"
    return None


def load_data():
    """Загружает лист knowledge_db из Google Sheets."""
    path = get_credentials_path()
    if not path:
        print("❌ Не найден credentials. Задайте GOOGLE_CREDENTIALS_JSON или положите credentials.json в текущую папку.")
        return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(path, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        df = pd.DataFrame(sheet.get_all_records())
        num_cols = [
            "Weight_Coefficient",
            "Threshold_High",
            "min_val",
            "max_val",
            "norm_min",
            "norm_max",
        ]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return None
    finally:
        if path and path != "credentials.json" and os.path.isfile(path):
            try:
                os.unlink(path)
            except Exception:
                pass


def analyze(df: pd.DataFrame) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("АНАЛИЗ ОБНОВЛЁННОЙ БАЗЫ (Google Таблица, лист knowledge_db)")
    lines.append("=" * 80)
    lines.append(f"\nВсего строк: {len(df)}")
    lines.append(f"Колонки: {list(df.columns)}")

    # 1) factor_id
    if "factor_id" not in df.columns:
        lines.append("\n❌ Колонка factor_id отсутствует.")
        return "\n".join(lines)
    fid_series = df["factor_id"].astype(str).str.strip()
    unique_ids = fid_series.dropna().unique().tolist()
    lines.append(f"\n--- 1. FACTOR_ID (всего уникальных: {len(unique_ids)}) ---")
    lines.append("Список factor_id: " + ", ".join(sorted(unique_ids)))
    dup = df.loc[fid_series.duplicated(keep=False)]
    if len(dup) > 0 and "Risk_Group" in df.columns:
        by_group = dup.groupby(["factor_id", "Risk_Group"]).size()
        if len(by_group) > 0:
            lines.append("\nПовторяющиеся factor_id (в одной и той же группе или в разных):")
            for (fid, grp), cnt in by_group.items():
                lines.append(f"  factor_id={fid}, Risk_Group={grp}: {cnt} строк(и)")
    missing_fid = df["factor_id"].isna().sum()
    if missing_fid:
        lines.append(f"\n⚠️ Строк с пустым factor_id: {missing_fid}")

    # 2) Weight_Coefficient по группам
    lines.append("\n--- 2. WEIGHT_COEFFICIENT ВНУТРИ ГРУПП ---")
    if "Weight_Coefficient" not in df.columns:
        lines.append("❌ Колонка Weight_Coefficient отсутствует.")
        return "\n".join(lines)
    if "Risk_Group" not in df.columns:
        lines.append("❌ Колонка Risk_Group отсутствует.")
        return "\n".join(lines)

    groups = df["Risk_Group"].dropna().unique()
    for group in sorted(groups):
        grp_df = df[df["Risk_Group"] == group].copy()
        grp_df = grp_df.sort_values("Weight_Coefficient", ascending=False)
        total = grp_df["Weight_Coefficient"].sum()
        ok = abs(total - 1.0) <= 0.001
        status = "✅" if ok else "❌"
        lines.append(f"\nГруппа: {group}  {status} сумма весов = {total:.4f} (ожидается 1.0)")
        lines.append("-" * 60)
        for _, row in grp_df.iterrows():
            fid = row.get("factor_id", "")
            name = row.get("factor_name", "")
            w = row.get("Weight_Coefficient", 0)
            w_str = f"{w:.4f}" if pd.notna(w) else "NaN"
            lines.append(f"  factor_id: {fid}  |  {name}  |  Weight_Coefficient: {w_str}")
        if not ok:
            lines.append(f"  >> ИТОГО по группе: {total:.4f} — нужно скорректировать веса до суммы 1.0")

    # 3) Отрицательные веса
    neg = df[df["Weight_Coefficient"] < 0]
    if len(neg) > 0:
        lines.append("\n--- 3. ОТРИЦАТЕЛЬНЫЕ ВЕСА ---")
        for _, row in neg.iterrows():
            lines.append(f"  {row.get('factor_name')} (factor_id={row.get('factor_id')}): {row['Weight_Coefficient']}")

    # 4) Итог по группам (кратко)
    lines.append("\n--- 4. СВОДКА ПО ГРУППАМ ---")
    for group in sorted(groups):
        grp_df = df[df["Risk_Group"] == group]
        total = grp_df["Weight_Coefficient"].sum()
        n = len(grp_df)
        ok = "✅" if abs(total - 1.0) <= 0.001 else "❌"
        lines.append(f"  {group}: факторов {n}, сумма весов {total:.4f} {ok}")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def main():
    print("Загрузка данных из Google Таблицы...")
    df = load_data()
    if df is None:
        sys.exit(1)
    print("Данные загружены.\n")
    report = analyze(df)
    print(report)
    out_path = "analysis_google_sheet_report.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nОтчёт сохранён: {out_path}")


if __name__ == "__main__":
    main()
