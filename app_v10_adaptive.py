import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json

# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="Health Risk Advisor 10.0", page_icon="🏥", layout="wide")

# Настройки GigaChat (self-hosted)
GIGACHAT_API_URL = st.secrets.get("GIGACHAT_API_URL", "http://localhost:8000/v1/chat/completions")
GIGACHAT_API_KEY = st.secrets.get("GIGACHAT_API_KEY", "")

@st.cache_data(ttl=5)
def get_data():
    SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
    CREDENTIALS_FILE = "credentials.json"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        df = pd.DataFrame(sheet.get_all_records())
        num_cols = ['Weight_Coefficient', 'Threshold_High', 'min_val', 'max_val', 'norm_min', 'norm_max']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Ошибка связи: {e}")
        return None

def calculate_risk(val, v_min, v_max, n_min, n_max, u_type):
    if u_type == "select": return float(val)
    if n_min <= val <= n_max: return 0.0
    if val < n_min:
        denom = n_min - v_min
        res = abs(n_min - val) / denom if denom != 0 else 1.0
    else:
        denom = v_max - n_max
        res = abs(val - n_max) / denom if denom != 0 else 1.0
    return min(max(res, 0.0), 1.0)

def has_sufficient_data(group_df, user_inputs, min_factors=3):
    """Проверяет, достаточно ли данных для расчета группы"""
    available_factors = sum(1 for _, row in group_df.iterrows() 
                           if user_inputs.get(row['factor_id'], 0) is not None)
    return available_factors >= min_factors

def calculate_adaptive_score(group_scores, available_groups, min_groups=5):
    """
    Адаптивная модель расчета итогового индекса
    Работает даже при неполных данных
    """
    if len(available_groups) < min_groups:
        # Недостаточно данных - упрощенный расчет
        if len(available_groups) == 0:
            return 0.0, "Недостаточно данных для расчета"
        
        # Используем только доступные группы
        avg_score = sum(group_scores[g] for g in available_groups) / len(available_groups)
        max_score = max(group_scores[g] for g in available_groups)
        final_score = (avg_score * 0.7) + (max_score * 0.3)
        
        warning = f"⚠️ Данные доступны только для {len(available_groups)} из 10 систем. Результат может быть менее точным."
        return final_score, warning
    
    # Достаточно данных - полный расчет
    avg_score = sum(group_scores.values()) / len(group_scores)
    max_score = max(group_scores.values())
    final_score = (avg_score * 0.6) + (max_score * 0.4)
    
    return final_score, None

def get_gigachat_recommendations(user_inputs, group_scores, df):
    """
    Получение персонализированных рекомендаций от GigaChat
    """
    if not GIGACHAT_API_URL or not GIGACHAT_API_KEY:
        return None
    
    # Подготовка контекста для AI
    high_risk_factors = []
    for _, row in df.iterrows():
        risk_value = user_inputs.get(row['factor_id'], 0)
        if risk_value >= row.get('Threshold_High', 0.5):
            high_risk_factors.append({
                'factor': row['factor_name'],
                'risk': risk_value,
                'recommendation': row.get('recommendation', '')
            })
    
    # Формирование запроса
    prompt = f"""
    Проанализируй следующие данные о здоровье пользователя:
    
    Оценки рисков по системам:
    {json.dumps(group_scores, ensure_ascii=False, indent=2)}
    
    Факторы с высоким риском:
    {json.dumps(high_risk_factors, ensure_ascii=False, indent=2)}
    
    Предоставь персонализированные рекомендации по улучшению здоровья, учитывая взаимосвязи между системами.
    Ответ должен быть кратким (до 200 слов) и практичным.
    """
    
    try:
        response = requests.post(
            GIGACHAT_API_URL,
            headers={
                "Authorization": f"Bearer {GIGACHAT_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": "Ты эксперт по превентивной медицине и здоровому образу жизни."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        st.warning(f"Не удалось получить рекомендации от AI: {e}")
    
    return None

def build_inputs(df, risk_groups, mode):
    def clamp_start(row):
        min_val = float(row['min_val'])
        max_val = float(row['max_val'])
        start_val = float((row['norm_min'] + row['norm_max']) / 2)
        if start_val < min_val:
            start_val = min_val
        if start_val > max_val:
            start_val = max_val
        return min_val, max_val, start_val

    user_inputs = {}
    if mode == "Слайдеры":
        for group in risk_groups:
            st.sidebar.markdown(f"## {group}")
            g_df = df[df['Risk_Group'] == group]
            for _, row in g_df.iterrows():
                f_id, f_name = row['factor_id'], row['factor_name']
                u_type, u_name = str(row['unit_type']).strip(), str(row.get('unit_name', ''))
                label = f"{f_name}, {u_name}" if u_name else f_name
                if "range" in u_type:
                    _, _, start_val = clamp_start(row)
                    val = st.sidebar.slider(
                        label,
                        float(row['min_val']),
                        float(row['max_val']),
                        start_val,
                        step=0.1,
                        key=f"s_{f_id}",
                    )
                    user_inputs[f_id] = calculate_risk(
                        val,
                        row['min_val'],
                        row['max_val'],
                        row['norm_min'],
                        row['norm_max'],
                        u_type,
                    )
                elif u_type == "select":
                    options = {"Норма": 0.0, "Умеренно": 0.5, "Критично": 1.0}
                    choice = st.sidebar.selectbox(label, list(options.keys()), key=f"sel_{f_id}")
                    user_inputs[f_id] = options[choice]
    else:
        st.subheader("🧪 Тест: пошаговый ввод")
        if "test_step" not in st.session_state:
            st.session_state.test_step = 0
        if "test_done" not in st.session_state:
            st.session_state.test_done = False
        if "test_answers" not in st.session_state:
            st.session_state.test_answers = {}

        total_steps = max(len(risk_groups), 1)
        step = min(st.session_state.test_step, total_steps - 1)
        current_group = risk_groups[step]

        st.progress((step + 1) / total_steps)
        st.markdown(f"### Шаг {step + 1} из {total_steps}: {current_group}")

        g_df = df[df['Risk_Group'] == current_group]
        for _, row in g_df.iterrows():
            f_id, f_name = row['factor_id'], row['factor_name']
            u_type, u_name = str(row['unit_type']).strip(), str(row.get('unit_name', ''))
            label = f"{f_name}, {u_name}" if u_name else f_name
            if "range" in u_type:
                min_val, max_val, start_val = clamp_start(row)
                help_text = None
                if pd.notna(row.get('norm_min')) and pd.notna(row.get('norm_max')):
                    help_text = f"Норма: {row['norm_min']}–{row['norm_max']}"
                stored_val = st.session_state.test_answers.get(f_id, start_val)
                st.number_input(
                    label,
                    min_value=min_val,
                    max_value=max_val,
                    value=stored_val,
                    step=0.1,
                    key=f"temp_{f_id}",
                    help=help_text,
                )
            elif u_type == "select":
                options = ["Норма", "Умеренно", "Критично"]
                stored_choice = st.session_state.test_answers.get(f_id, "Норма")
                st.selectbox(label, options, index=options.index(stored_choice), key=f"temp_sel_{f_id}")

        nav_left, nav_mid, nav_right = st.columns([1, 1, 2])
        go_back = nav_left.button("Назад", disabled=step == 0)
        go_next = nav_mid.button("Далее", disabled=step >= total_steps - 1)
        finish = nav_right.button("Рассчитать", disabled=step < total_steps - 1)

        if go_back:
            st.session_state.test_step = max(step - 1, 0)
            st.session_state.test_done = False
            st.rerun()
        if go_next:
            for _, row in g_df.iterrows():
                f_id = row['factor_id']
                u_type = str(row['unit_type']).strip()
                if "range" in u_type:
                    st.session_state.test_answers[f_id] = st.session_state.get(f"temp_{f_id}")
                elif u_type == "select":
                    st.session_state.test_answers[f_id] = st.session_state.get(f"temp_sel_{f_id}", "Норма")
            st.session_state.test_step = min(step + 1, total_steps - 1)
            st.session_state.test_done = False
            st.rerun()
        if finish:
            for _, row in g_df.iterrows():
                f_id = row['factor_id']
                u_type = str(row['unit_type']).strip()
                if "range" in u_type:
                    st.session_state.test_answers[f_id] = st.session_state.get(f"temp_{f_id}")
                elif u_type == "select":
                    st.session_state.test_answers[f_id] = st.session_state.get(f"temp_sel_{f_id}", "Норма")
            st.session_state.test_done = True

        if not st.session_state.test_done:
            st.info("Заполните поля и переходите по шагам. В конце нажмите «Рассчитать».")
            st.stop()

        for _, row in df.iterrows():
            f_id = row['factor_id']
            u_type = str(row['unit_type']).strip()
            if "range" in u_type:
                _, _, start_val = clamp_start(row)
                val = st.session_state.test_answers.get(f_id, start_val)
                user_inputs[f_id] = calculate_risk(
                    val,
                    row['min_val'],
                    row['max_val'],
                    row['norm_min'],
                    row['norm_max'],
                    u_type,
                )
            elif u_type == "select":
                options = {"Норма": 0.0, "Умеренно": 0.5, "Критично": 1.0}
                choice = st.session_state.test_answers.get(f_id, "Норма")
                user_inputs[f_id] = options.get(choice, 0.0)
    return user_inputs

df = get_data()

if df is not None and not df.empty:
    st.title("🛡️ Integral Health Score 10.0")
    st.markdown("_Комплексная оценка 12 системных рисков здоровью_")
    
    risk_groups = sorted([g for g in df['Risk_Group'].unique() if g and pd.notna(g)])
    input_mode = st.sidebar.radio("Режим ввода", ["Тест (по порядку)", "Слайдеры"], index=0)
    user_inputs = build_inputs(df, risk_groups, "Слайдеры" if input_mode == "Слайдеры" else "Тест")

    # --- АДАПТИВНЫЙ РАСЧЕТ ---
    group_scores = {}
    available_groups = []
    
    for group in risk_groups:
        g_df = df[df['Risk_Group'] == group]
        if not g_df.empty and has_sufficient_data(g_df, user_inputs, min_factors=2):
            total_w = g_df['Weight_Coefficient'].sum()
            raw_score = sum(user_inputs.get(r['factor_id'], 0) * r['Weight_Coefficient'] 
                          for _, r in g_df.iterrows() 
                          if user_inputs.get(r['factor_id'], 0) is not None)
            if total_w > 0:
                group_scores[group] = (raw_score / total_w) * 10
                available_groups.append(group)

    # Адаптивный расчет итогового индекса
    final_score, warning = calculate_adaptive_score(group_scores, available_groups, min_groups=5)
    
    if warning:
        st.warning(warning)

    # --- ИНТЕРПРЕТАЦИЯ ---
    if final_score <= 2.5:
        color, status = "#2ecc71", "ОПТИМУМ"
        brief = "Состояние физиологического покоя."
        long_desc = "Ваши показатели находятся в пределах медицинских норм. Ресурсы организма (адаптационный потенциал) высоки. Риск внезапных сбоев минимален. Текущий образ жизни поддерживает гомеостаз."
    elif final_score <= 5.0:
        color, status = "#f1c40f", "КОМПЕНСАЦИЯ"
        brief = "Начало расхода резервных сил."
        long_desc = "Система работает с повышенной нагрузкой. Организм компенсирует отклонения, но делает это за счет внутренних ресурсов. Вы можете чувствовать фоновую усталость, но серьезных патологий еще нет. Требуется точечная коррекция факторов."
    elif final_score <= 7.5:
        color, status = "#e67e22", "СУБКОМПЕНСАЦИЯ"
        brief = "Стадия выраженного напряжения."
        long_desc = "Критическое напряжение регуляторных систем. Резервы на исходе. Один или несколько показателей вышли из-под контроля. Высока вероятность перехода функциональных нарушений в хроническую стадию."
    else:
        color, status = "#e74c3c", "ДЕКОМПЕНСАЦИЯ"
        brief = "Высокий риск системного отказа."
        long_desc = "Организм больше не может поддерживать баланс. Состояние характеризуется высокой вероятностью острых событий (кризов). Требуется немедленная профессиональная диагностика и жесткая коррекция режима."

    st.markdown("---")
    st.markdown(f"""
        <div style="background-color:{color}; padding:40px; border-radius:20px; text-align:center; color:white; border: 2px solid rgba(0,0,0,0.1);">
            <p style="margin:0; font-size:18px; font-weight:bold; opacity:0.8;">ИТОГОВЫЙ БАЛЛ РИСКА</p>
            <h1 style="margin:0; font-size:110px; line-height:1;">{final_score:.1f}</h1>
            <h2 style="margin:5px 0; letter-spacing:3px;">{status}</h2>
            <p style="font-size:20px; font-style:italic;">{brief}</p>
        </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.write("")
        st.info(f"**Аналитический вердикт:** {long_desc}")

    # Метрики по всем 10 системам (сетка 2x5)
    if group_scores:
        st.markdown("---")
        st.subheader("📊 Оценка по системам")
        
        # Создаем сетку 2x5 для 10 систем
        system_names = ['Neuro', 'Cardio', 'Hormone', 'Metabolic', 'Immune', 
                       'Renal', 'Hepatic', 'Bone', 'Oxidative', 'Inflammatory']
        
        # Разбиваем на 2 колонки по 5 систем
        cols = st.columns(2)
        for col_idx in range(2):
            with cols[col_idx]:
                for i in range(5):
                    system_idx = col_idx * 5 + i
                    if system_idx < len(system_names):
                        system = system_names[system_idx]
                        if system in group_scores:
                            score = group_scores[system]
                            st.metric(f"**{system}**", f"{score:.1f}", delta=None)
                            st.progress(min(float(score)/10, 1.0))
                        else:
                            st.metric(f"**{system}**", "N/A", delta="Нет данных")
                            st.progress(0.0)

    # AI рекомендации (опционально)
    if st.sidebar.checkbox("Получить AI рекомендации (GigaChat)", value=False):
        with st.spinner("Генерация персонализированных рекомендаций..."):
            ai_recommendations = get_gigachat_recommendations(user_inputs, group_scores, df)
            if ai_recommendations:
                st.markdown("---")
                st.subheader("🤖 Персонализированные рекомендации от AI")
                st.info(ai_recommendations)

    st.markdown("---")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📋 План коррекции")
        high_risk_count = 0
        for _, row in df.iterrows():
            if user_inputs.get(row['factor_id'], 0) >= row['Threshold_High'] and user_inputs.get(row['factor_id'], 0) > 0:
                high_risk_count += 1
                with st.expander(f"📍 {row['factor_name']}", expanded=(high_risk_count <= 3)):
                    st.warning(row['recommendation'])
        if high_risk_count == 0:
            st.success("Все показатели в пределах нормы!")
    
    with col_r:
        st.subheader("💡 Анализ вклада факторов")
        impact = {row['factor_name']: user_inputs[row['factor_id']] * 10 
                 for _, row in df.iterrows() 
                 if user_inputs.get(row['factor_id'], 0) > 0}
        if impact:
            st.bar_chart(pd.Series(impact).sort_values(ascending=False).head(10))
        else:
            st.info("Нет данных для анализа")
else:
    st.error("Не удалось загрузить данные. Проверьте подключение к Google Sheets и файл credentials.json.")
    st.info("Пожалуйста, убедитесь, что файл credentials.json существует и содержит корректные учетные данные Google API.")
