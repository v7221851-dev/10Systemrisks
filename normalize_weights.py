#!/usr/bin/env python3
"""
Выравнивает Weight_Coefficient внутри каждой Risk_Group (сумма = 1.0),
выделяя самые важные факторы наибольшими коэффициентами.
Важность задаётся текущим весом (что уже выше — считаем важнее) или явным списком.
Результат: таблица и CSV для обновления Google Таблицы.
"""

import os
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

# Сколько «главных» факторов в группе получают повышенный вес (остальные — равномерно)
TOP_N = 2  # топ-1 или топ-2 по текущему весу считаются самыми важными
# Доля веса на «главные» факторы (остальное делим между прочими)
SHARE_FOR_TOP = 0.55  # 55% на топ, 45% на остальные


def get_credentials_path():
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw:
        try:
            json.loads(raw)
        except json.JSONDecodeError:
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
    path = get_credentials_path()
    if not path:
        print("❌ Нет credentials (GOOGLE_CREDENTIALS_JSON или credentials.json).")
        return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(path, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        df = pd.DataFrame(sheet.get_all_records())
        if "Weight_Coefficient" in df.columns:
            df["Weight_Coefficient"] = pd.to_numeric(df["Weight_Coefficient"], errors="coerce")
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


def normalize_group_weights(df: pd.DataFrame) -> pd.DataFrame:
    """По группе: ранжируем по текущему весу (важные выше), выравниваем сумму в 1.0."""
    if "Risk_Group" not in df.columns or "Weight_Coefficient" not in df.columns:
        return df
    out = df.copy()
    out["Weight_Coefficient_old"] = out["Weight_Coefficient"]
    out["new_weight"] = pd.NA

    for group in out["Risk_Group"].dropna().unique():
        mask = out["Risk_Group"] == group
        grp = out.loc[mask].copy()
        n = len(grp)
        if n == 0:
            continue
        w = grp["Weight_Coefficient"].fillna(0)
        # Сортируем по убыванию веса, затем по имени — самые важные первые
        grp = grp.assign(_w=w).sort_values(by=["_w", "factor_name"], ascending=[False, True])
        top_k = min(TOP_N, n)
        # Топ top_k — «главные», остальные — равномерно
        share_rest = 1.0 - SHARE_FOR_TOP
        top_share_each = SHARE_FOR_TOP / top_k if top_k else 0
        rest_share_each = share_rest / (n - top_k) if n > top_k else 0
        new_weights = []
        for i in range(n):
            if i < top_k:
                new_weights.append(round(top_share_each, 4))
            else:
                new_weights.append(round(rest_share_each, 4))
        # Нормализация из-за округления: последнему присвоить остаток до 1.0
        s = sum(new_weights)
        if abs(s - 1.0) > 1e-6:
            new_weights[-1] = round(new_weights[-1] + (1.0 - s), 4)
        idxs = grp.index.tolist()
        for idx, w in zip(idxs, new_weights):
            out.loc[idx, "new_weight"] = w
    out["new_weight"] = pd.to_numeric(out["new_weight"], errors="coerce")
    # Строки без группы: оставить старый вес или 0
    out["new_weight"] = out["new_weight"].fillna(out["Weight_Coefficient_old"]).fillna(0)
    return out


def _col_to_letter(n: int) -> str:
    """1-based column index -> A1 letter (1=A, 26=Z, 27=AA)."""
    s = ""
    while n > 0:
        n, r = (n - 1) // 26, (n - 1) % 26
        s = chr(65 + r) + s
    return s


def write_weights_to_sheet(df: pd.DataFrame) -> bool:
    """Записывает колонку Weight_Coefficient обратно в Google Таблицу."""
    path = get_credentials_path()
    if not path:
        return False
    col_name = "Weight_Coefficient"
    if col_name not in df.columns or "new_weight" not in df.columns:
        print("❌ В данных нет Weight_Coefficient или new_weight.")
        return False
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(path, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        col_idx_0 = list(df.columns).index(col_name)
        col_idx_1 = col_idx_0 + 1
        col_letter = _col_to_letter(col_idx_1)
        values = [[round(float(w), 4)] for w in df["new_weight"]]
        range_a1 = f"{col_letter}2:{col_letter}{len(values) + 1}"
        sheet.update(values, range_a1, value_input_option="USER_ENTERED")
        print(f"✅ В таблицу записаны новые веса (диапазон {range_a1}).")
        return True
    except Exception as e:
        print(f"❌ Ошибка записи в таблицу: {e}")
        return False
    finally:
        if path and path != "credentials.json" and os.path.isfile(path):
            try:
                os.unlink(path)
            except Exception:
                pass


def main():
    import sys
    do_write = "--write" in sys.argv
    print("Загрузка данных из Google Таблицы...")
    df = load_data()
    if df is None:
        return
    print(f"Загружено строк: {len(df)}\n")

    df = normalize_group_weights(df)

    # Отчёт в консоль
    print("=" * 80)
    print("НОВЫЕ ВЕСА (сумма по группе = 1.0, самые важные с большим коэффициентом)")
    print("=" * 80)
    for group in sorted(df["Risk_Group"].dropna().unique()):
        grp = df[df["Risk_Group"] == group].copy()
        grp = grp.sort_values("new_weight", ascending=False)
        total = grp["new_weight"].sum()
        print(f"\n--- {group} (сумма = {total:.4f}) ---")
        for _, row in grp.iterrows():
            old_w = row.get("Weight_Coefficient_old", "")
            old_s = f"{old_w:.3f}" if pd.notna(old_w) else "—"
            new_s = f"{row['new_weight']:.4f}" if pd.notna(row.get("new_weight")) else "—"
            name = row.get("factor_name", "") or row.get("factor_id", "")
            print(f"  {name}: было {old_s} → стало {new_s}")

    # CSV для вставки в таблицу
    csv_path = "weight_coefficient_updates.csv"
    export = df[["factor_id", "Risk_Group", "factor_name", "Weight_Coefficient_old", "new_weight"]].copy()
    export = export.rename(columns={"new_weight": "Weight_Coefficient"})
    export["Weight_Coefficient"] = export["Weight_Coefficient"].round(4)
    export.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nФайл для обновления весов: {csv_path}")

    if do_write:
        print("\nЗапись новых весов в Google Таблицу...")
        write_weights_to_sheet(df)
    else:
        print("Чтобы записать веса в таблицу, запустите: python3 normalize_weights.py --write")


if __name__ == "__main__":
    main()
