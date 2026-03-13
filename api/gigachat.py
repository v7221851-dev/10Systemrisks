"""
GigaChat API для получения рекомендаций (без Streamlit).
"""
import os
import json
import base64
import time
import requests

GIGACHAT_API_URL = os.getenv("GIGACHAT_API_URL", "https://gigachat.devices.sberbank.ru/api/v1/chat/completions")
GIGACHAT_AUTH_URL = os.getenv("GIGACHAT_AUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET", "")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY", "")


def get_access_token():
    if GIGACHAT_API_KEY:
        return GIGACHAT_API_KEY, None
    if not GIGACHAT_CLIENT_ID:
        return None, "GIGACHAT_CLIENT_ID не указан"
    auth_data = GIGACHAT_AUTH_KEY.strip() if GIGACHAT_AUTH_KEY else None
    if not auth_data and GIGACHAT_CLIENT_SECRET:
        auth_string = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
        auth_data = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8").strip()
    if not auth_data:
        return None, "Требуется GIGACHAT_AUTH_KEY или GIGACHAT_CLIENT_SECRET"
    import uuid
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.post(
            GIGACHAT_AUTH_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": f"Basic {auth_data}",
            },
            data={"scope": GIGACHAT_SCOPE},
            timeout=30,
            verify=False,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("access_token"), None
        return None, f"Ошибка авторизации: {r.status_code} - {r.text[:300]}"
    except Exception as e:
        return None, str(e)


def get_recommendations(user_inputs, group_scores, df_records, user_sex=None, user_age=None):
    """Возвращает (text, error)."""
    token, err = get_access_token()
    if err:
        return None, err
    low_score_factors = []
    for row in df_records:
        fid = row.get("factor_id")
        score_val = user_inputs.get(fid)
        if score_val is not None and score_val <= 2.5:
            low_score_factors.append({
                "factor": row.get("factor_name", fid),
                "score": score_val,
                "recommendation": row.get("recommendation", ""),
            })
    sex_str = "Мужской" if user_sex == "M" else "Женский" if user_sex == "F" else "не указан"
    age_str = f"{user_age} лет" if user_age is not None else "не указан"
    prompt = f"""Проанализируй данные о здоровье пользователя:
Пол: {sex_str}, Возраст: {age_str}.

Оценки по системам (1-5, 5=отлично):
{json.dumps(group_scores, ensure_ascii=False, indent=2)}

Факторы с низким баллом:
{json.dumps(low_score_factors, ensure_ascii=False, indent=2)}

Дай персонализированные рекомендации по улучшению здоровья. Стиль: практичный, мотивирующий. До 200 слов. Не назначай лекарства."""
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.post(
            GIGACHAT_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": "Ты эксперт по превентивной медицине и здоровому образу жизни."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
            },
            timeout=30,
            verify=False,
        )
        if r.status_code == 200:
            data = r.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return content, None
            return None, "Пустой ответ от GigaChat"
        return None, f"Ошибка API: {r.status_code} - {r.text[:300]}"
    except Exception as e:
        return None, str(e)


def chat(user_message, chat_history, user_inputs=None, group_scores=None, df_records=None, user_sex=None, user_age=None):
    """Диалог с GigaChat. Возвращает (text, error)."""
    token, err = get_access_token()
    if err:
        return None, err
    messages = [{"role": "system", "content": "Ты эксперт по превентивной медицине и здоровому образу жизни. Отвечай кратко и по делу."}]
    context_added = any(m.get("role") == "assistant" and "ознакомился" in (m.get("content") or "") for m in (chat_history or []))
    if not context_added and user_inputs and group_scores and df_records:
        low = [{"factor": r.get("factor_name"), "score": user_inputs.get(r.get("factor_id"))} for r in df_records if user_inputs.get(r.get("factor_id")) is not None and user_inputs.get(r.get("factor_id")) <= 2.5]
        sex_s = "М" if user_sex == "M" else "Ж" if user_sex == "F" else "—"
        age_s = str(user_age) if user_age else "—"
        ctx = f"Контекст: пол {sex_s}, возраст {age_s}. Оценки систем: {json.dumps(group_scores, ensure_ascii=False)}. Низкие факторы: {json.dumps(low, ensure_ascii=False)}. Отвечай на вопросы с учётом этих данных."
        messages.append({"role": "user", "content": ctx})
        messages.append({"role": "assistant", "content": "Ознакомился с данными. Готов отвечать на вопросы."})
    for m in (chat_history or []):
        if m.get("role") in ("user", "assistant") and "ознакомился" not in (m.get("content") or ""):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_message})
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.post(GIGACHAT_API_URL, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"model": "GigaChat", "messages": messages, "temperature": 0.7, "max_tokens": 500}, timeout=30, verify=False)
        if r.status_code == 200:
            c = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return c or None, None
        return None, f"Ошибка: {r.status_code}"
    except Exception as e:
        return None, str(e)
