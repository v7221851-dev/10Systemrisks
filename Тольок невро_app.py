import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="System Risk Advisor Pro", page_icon="🛡️", layout="wide")

@st.cache_data(ttl=60)
def get_data():
    SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
    CREDENTIALS_FILE = "credentials.json"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
        df = pd.DataFrame(sheet.get_all_records())
        
        # Чистка типов данных
        for col in ['Weight_Coefficient', 'Threshold_High', 'min_val', 'max_val']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Ошибка доступа: {e}")
        return None

df = get_data()

if df is not None:
    st.title("🛡️ Система анализа нейро-рисков")
    st.sidebar.header("📋 Текущие показатели")
    
    user_normalized_values = {}
    
    # --- ВВОД ДАННЫХ ---
    for _, row in df.iterrows():
        f_id = row['factor_id']
        f_name = row['factor_name']
        u_type = str(row['unit_type']).strip()
        u_name = str(row.get('unit_name', '')).strip()
        min_v = float(row['min_val'])
        max_v = float(row['max_val'])
        
        label = f"{f_name}, {u_name}" if u_name else f_name

        if "range" in u_type:
            step_val = 0.5 if u_name in ['ч', 'ч.', 'час'] else 1.0
            raw_val = st.sidebar.slider(label, min_v, max_v, value=(min_v + max_v)/2, step=step_val, key=f"in_{f_id}")
            
            # Нормализация
            norm = (raw_val - min_v) / (max_v - min_v) if (max_v - min_v) != 0 else 0
            if u_type == "range_inv":
                norm = 1.0 - norm
            user_normalized_values[f_id] = norm

        elif u_type == "select":
            options = {"Отличное / Регулярное": 0.0, "Среднее / Смешанное": 0.5, "Плохое / Фастфуд": 1.0}
            choice = st.sidebar.selectbox(label, list(options.keys()), key=f"in_{f_id}")
            user_normalized_values[f_id] = options[choice]

    # --- РАСЧЕТ И АНАЛИЗ ---
    total_risk = 0.0
    active_recommendations = []

    for _, row in df.iterrows():
        f_id = row['factor_id']
        weight = float(row['Weight_Coefficient'])
        threshold = float(row['Threshold_High'])
        norm_val = user_normalized_values[f_id]
        
        total_risk += norm_val * weight
        
        # Собираем рекомендации, если порог превышен
        if norm_val >= threshold:
            active_recommendations.append({
                "factor": row['factor_name'],
                "text": row.get('recommendation', 'Рекомендация не заполнена в таблице')
            })

    # --- ВИЗУАЛИЗАЦИЯ ---
    st.markdown("---")
    res_col, advice_col = st.columns([1, 1])

    with res_col:
        st.subheader("Итоговый индекс")
        # Только цвет и число
        color = "#2ecc71" if total_risk < 0.35 else "#f1c40f" if total_risk < 0.7 else "#e74c3c"
        st.markdown(f"""
            <div style="background-color:{color}; padding:50px; border-radius:20px; text-align:center;">
                <h1 style="color:white; font-size:80px; margin:0;">{total_risk:.3f}</h1>
            </div>
        """, unsafe_allow_html=True)
        st.write("")
        st.progress(min(total_risk, 1.0))

    with advice_col:
        st.subheader("📋 Рекомендации")
        if active_recommendations:
            for rec in active_recommendations:
                with st.expander(f"📍 {rec['factor']}", expanded=True):
                    st.info(rec['text'])
        else:
            st.success("Все показатели в норме. Специфических рекомендаций нет.")

    # Вклад факторов
    st.markdown("---")
    st.subheader("💡 Влияние факторов на риск")
    impact_series = pd.Series({
        row['factor_name']: user_normalized_values[row['factor_id']] * float(row['Weight_Coefficient']) 
        for _, row in df.iterrows()
    }).sort_values()
    st.bar_chart(impact_series)

else:
    st.error("Данные не загружены. Проверьте соединение.")