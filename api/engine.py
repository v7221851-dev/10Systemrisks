"""
Движок расчёта рисков — логика из app.py для использования в API.
"""
import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
RISK_GROUPS_ORDER = [
    'Neuro', 'Cardio', 'Hormone', 'Metabolic', 'Immune', 'Renal',
    'Hepatic', 'Musculoskeletal', 'Inflammatory', 'SkinHair', 'Gastric', 'Ocular',
]


def _get_credentials():
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw:
        try:
            data = json.loads(raw)
            return data
        except json.JSONDecodeError:
            pass
    for path in ["credentials.json", os.path.join(os.path.dirname(__file__), "..", "credentials.json")]:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("GOOGLE_CREDENTIALS_JSON не найден. Положите credentials.json в корень проекта.")


def get_knowledge_df():
    creds_data = _get_credentials()
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(creds_data, f, ensure_ascii=False)
        path = f.name
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(path, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        df = pd.DataFrame(sheet.get_all_records())
    finally:
        os.unlink(path)

    num_cols = [
        'Weight_Coefficient', 'Threshold_High',
        'min_val', 'max_val', 'norm_min', 'norm_max',
        'norm_min_M', 'norm_max_M', 'norm_min_F', 'norm_max_F',
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if "Weight_Coefficient" in df.columns and "Risk_Group" in df.columns:
        for group in df["Risk_Group"].dropna().unique():
            mask = df["Risk_Group"] == group
            total = df.loc[mask, "Weight_Coefficient"].sum()
            if total > 0:
                df.loc[mask, "Weight_Coefficient"] = df.loc[mask, "Weight_Coefficient"] / total
    return df


def apply_sex_age_norms(df, sex, age):
    out = df.copy()
    has_m_cols = "norm_min_M" in df.columns and "norm_max_M" in df.columns
    has_f_cols = "norm_min_F" in df.columns and "norm_max_F" in df.columns
    if not (has_m_cols or has_f_cols):
        return out
    sex_key = "M" if sex == "M" else "F" if sex == "F" else None
    if sex_key == "M" and has_m_cols:
        min_col, max_col = "norm_min_M", "norm_max_M"
    elif sex_key == "F" and has_f_cols:
        min_col, max_col = "norm_min_F", "norm_max_F"
    else:
        return out
    for idx, row in out.iterrows():
        nmin, nmax = row.get(min_col), row.get(max_col)
        if pd.notna(nmin) and pd.notna(nmax):
            out.at[idx, "norm_min"] = float(nmin)
            out.at[idx, "norm_max"] = float(nmax)
    return out


def calculate_risk(val, v_min, v_max, n_min, n_max, u_type):
    if u_type == "select":
        risk = float(val)
        return 5.0 - (risk * 4.0)
    n_min, n_max = float(n_min), float(n_max)
    v_min, v_max = float(v_min), float(v_max)
    if n_min <= val <= n_max:
        return 5.0
    if val < n_min:
        denom = n_min - v_min
        risk = abs(n_min - val) / denom if denom != 0 else 1.0
    else:
        denom = v_max - n_max
        risk = abs(val - n_max) / denom if denom != 0 else 1.0
    risk = min(max(risk, 0.0), 1.0)
    return 5.0 - (risk * 4.0)


def has_sufficient_data(group_df, user_inputs, min_factors=3):
    available = sum(1 for _, row in group_df.iterrows()
                    if user_inputs.get(row['factor_id'], 0) is not None)
    return available >= min_factors


def calculate_adaptive_score(group_scores, available_groups, min_groups=4):
    if len(available_groups) < min_groups:
        if len(available_groups) == 0:
            return None, "Недостаточно данных для расчета"
        avg = sum(group_scores[g] for g in available_groups) / len(available_groups)
        min_s = min(group_scores[g] for g in available_groups)
        final = (avg * 0.7) + (min_s * 0.3)
        warning = f"Данные доступны только для {len(available_groups)} систем. Результат может быть менее точным."
        return final, warning
    avg = sum(group_scores.values()) / len(group_scores)
    min_s = min(group_scores.values())
    return (avg * 0.6) + (min_s * 0.4), None


def run_calculation(df, test_answers, sex=None, age=None):
    df = apply_sex_age_norms(df, sex, age)
    risk_groups = sorted([g for g in df['Risk_Group'].unique() if g and pd.notna(g) and g != 'Oxidative'])

    user_inputs = {}
    select_options = {"Норма": 5.0, "Умеренно": 3.0, "Критично": 1.0}
    for _, row in df.iterrows():
        f_id = row['factor_id']
        u_type = str(row.get('unit_type', '')).strip()
        if "range" in u_type:
            n_min, n_max = float(row['norm_min']), float(row['norm_max'])
            v_min, v_max = float(row['min_val']), float(row['max_val'])
            if n_min == n_max == 0:
                start = (v_min + v_max) / 2.0 if v_max > v_min else v_min
            else:
                start = (n_min + n_max) / 2.0
            start = max(v_min, min(v_max, start))
            val = test_answers.get(f_id, start)
            if isinstance(val, (int, float)):
                user_inputs[f_id] = calculate_risk(val, v_min, v_max, n_min, n_max, u_type)
            else:
                user_inputs[f_id] = 5.0
        elif u_type == "select":
            choice = test_answers.get(f_id, "Норма")
            user_inputs[f_id] = select_options.get(choice, 5.0)

    group_scores = {}
    available_groups = []
    for group in risk_groups:
        g_df = df[df['Risk_Group'] == group]
        if g_df.empty:
            continue
        min_required = min(2, len(g_df))
        if not has_sufficient_data(g_df, user_inputs, min_factors=min_required):
            continue
        total_w = float(g_df['Weight_Coefficient'].sum())
        raw_score = sum(
            user_inputs.get(r['factor_id'], 0) * r['Weight_Coefficient']
            for _, r in g_df.iterrows()
            if user_inputs.get(r['factor_id']) is not None
        )
        if total_w <= 0 and len(g_df) == 1:
            fid = g_df.iloc[0]['factor_id']
            val = user_inputs.get(fid)
            group_scores[group] = float(val) if val is not None else 0.0
            available_groups.append(group)
            continue
        if total_w > 0:
            group_scores[group] = raw_score / total_w
            available_groups.append(group)

    final_score, warning = calculate_adaptive_score(group_scores, available_groups, min_groups=5)
    percent = (final_score * 20.0) if final_score else None
    if percent is not None:
        percent = max(0, min(100, round(percent, 1)))
    if percent is None:
        zone_name, brief = "НЕТ ДАННЫХ", "Недостаточно данных для расчета."
    elif percent <= 44:
        zone_name, brief = "Красная зона", "Высокий риск системного отказа."
    elif percent <= 65:
        zone_name, brief = "Жёлтая зона", "Начало расхода резервных сил."
    else:
        zone_name, brief = "Зелёная зона", "Состояние в норме."

    return {
        "group_scores": group_scores,
        "final_score": final_score,
        "percent": percent,
        "zone_name": zone_name,
        "brief": brief,
        "warning": warning,
        "user_inputs": user_inputs,
    }
