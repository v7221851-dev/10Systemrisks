import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import base64
import time

try:
    from ocr_vision import yandex_vision_ocr, tesseract_ocr, parse_lab_text, map_to_factors
    from ocr_vision import TESSERACT_AVAILABLE
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    TESSERACT_AVAILABLE = False

# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="Health Risk Advisor 10.0", page_icon="🏥", layout="wide")

# Стабильный масштаб: ограничение ширины основного блока на больших экранах для читаемости
st.markdown(
    """
    <style>
    .block-container { max-width: 1200px; padding-top: 1rem; padding-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Настройки GigaChat API
# Используем try/except для работы без secrets файла
try:
    GIGACHAT_API_URL = st.secrets.get("GIGACHAT_API_URL", "https://gigachat.devices.sberbank.ru/api/v1/chat/completions")
    GIGACHAT_AUTH_URL = st.secrets.get("GIGACHAT_AUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
    GIGACHAT_CLIENT_ID = st.secrets.get("GIGACHAT_CLIENT_ID", "")
    GIGACHAT_SCOPE = st.secrets.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    GIGACHAT_API_KEY = st.secrets.get("GIGACHAT_API_KEY", "")  # Для self-hosted версии
except (AttributeError, FileNotFoundError, Exception):
    # Дефолтные значения, если secrets недоступны
    GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    GIGACHAT_CLIENT_ID = ""
    GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
    GIGACHAT_API_KEY = ""

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

# Словарь переводов названий систем на русский
SYSTEM_NAMES_RU = {
    'Neuro': 'Нервная система',
    'Cardio': 'Сердце и сосуды',
    'Hormone': 'Щитовидная железа',
    'Metabolic': 'Метаболизм',
    'Immune': 'Иммунитет',
    'Renal': 'Почки',
    'Hepatic': 'Печень',
    'Bone': 'Кости и мышцы',
    'Musculoskeletal': 'Кости и мышцы',
    'Oxidative': 'Окислительный стресс',
    'Inflammatory': 'Системное воспаление',
    'SkinHair': 'Кожа и волосы',
    'Muscles': 'Костно-мышечная система',
    'Gastric': 'Желудок',
    'Ocular': 'Глаза',
}

def get_system_name_ru(system_name_en):
    """Возвращает русское название системы"""
    return SYSTEM_NAMES_RU.get(system_name_en, system_name_en)

# Краткие описания систем рисков: что оценивается
SYSTEM_DESCRIPTIONS = {
    "Neuro": "Нервная система — оценка рисков неврологических нарушений по показателям, связанным с функцией нервной системы и обменом веществ, влияющим на мозг и периферические нервы.",
    "Cardio": "Сердце и сосуды — оценка кардиорисков по маркерам повреждения миокарда, липидам, глюкозе и электролитам (калий, натрий, хлор).",
    "Hormone": "Щитовидная железа — оценка функции щитовидной железы и связанных с ней рисков по гормональным и метаболическим показателям.",
    "Metabolic": "Метаболизм — оценка рисков диабета и метаболического синдрома: глюкоза, инсулин, HbA1c, HOMA-IR, окружность талии и ИМТ.",
    "Immune": "Иммунитет — оценка состояния иммунной системы по лейкоцитам, лимфоцитам, нейтрофилам и иммуноглобулинам (IgA, IgG, IgM).",
    "Renal": "Почки — оценка функции почек и риска ХБП по креатинину, мочевине, СКФ, мочевой кислоте и микроальбуминурии.",
    "Hepatic": "Печень и желчные пути — оценка функции печени по АЛТ, АСТ, билирубину, ГГТ и щелочной фосфатазе.",
    "Bone": "Кости и мышцы — оценка минерального обмена и состояния костной и мышечной ткани (витамин D, кальций, фосфор, ПТГ, остеокальцин, КФК, магний, креатинин).",
    "Musculoskeletal": "Кости и мышцы — оценка минерального обмена и состояния костной и мышечной ткани (витамин D, кальций, фосфор, ПТГ, остеокальцин, КФК, магний, креатинин).",
    "Muscles": "Костно-мышечная система — см. описание «Кости и мышцы».",
    "Oxidative": "Окислительный стресс — оценка антиоксидантной защиты и повреждения окислением (МДА, глутатион, витамины E и C, коэнзим Q10).",
    "Inflammatory": "Системное воспаление — оценка фона хронического воспаления по hs-CRP, фибриногену, IL-6, TNF-α и СОЭ.",
    "SkinHair": "Кожа и волосы — оценка факторов, влияющих на состояние кожи и волос: витамин D, ферритин, цинк, ТТГ и селен.",
    "Gastric": "Желудок — оценка рисков желудочно-кишечной системы по пепсиногенам I/II, гастрину-17, H. pylori и витамину B12.",
    "Ocular": "Глаза — оценка офтальмологических рисков по ВГД, витамину A, гомоцистеину, глюкозе и CRP.",
}

def get_system_description(system_name_en):
    """Возвращает краткое описание системы рисков (из кода, fallback)."""
    return SYSTEM_DESCRIPTIONS.get(system_name_en, "")


def get_system_description_from_df(df, group):
    """Возвращает описание системы из столбца «Описание_системы» в df, иначе из SYSTEM_DESCRIPTIONS."""
    if df is not None and not df.empty and "Описание_системы" in df.columns:
        grp = df.loc[df["Risk_Group"] == group, "Описание_системы"].dropna()
        if not grp.empty and str(grp.iloc[0]).strip():
            return str(grp.iloc[0]).strip()
    return SYSTEM_DESCRIPTIONS.get(group, "")


def score_to_percent(score):
    """
    Пересчёт итогового балла (шкала 1–5) в процентный индекс: балл × 20 = %.
    5 = 100%, 1 = 20%.
    """
    if score is None:
        return None
    p = float(score) * 20.0
    return max(0.0, min(100.0, round(p, 1)))


def get_zone_by_percent(percent):
    """
    Зоны по проценту (шкала 20–100%): 20–44% красная, 45–65% жёлтая, 66–100% зелёная.
    Возвращает (color_hex, zone_name).
    """
    if percent is None:
        return "#95a5a6", "НЕТ ДАННЫХ"
    if percent <= 44:
        return "#e74c3c", "Красная зона"
    if percent <= 65:
        return "#f1c40f", "Жёлтая зона"
    return "#2ecc71", "Зелёная зона"


# URL силуэта тела для блока «Проекция на человека» (Wikimedia Commons, public domain)
# Локальный файл: assets/body_silhouette.png — положите свой PNG в проект, тогда он будет использован
BODY_SILHOUETTE_URL = "https://upload.wikimedia.org/wikipedia/commons/5/53/Human_body_outline.png"


def _body_projection_svg_html(system_names, group_scores, get_system_name_ru_fn):
    """
    Генерирует HTML: силуэт тела (PNG) + 12 сносок (название системы + %) с линиями к телу.
    Силуэт — из assets/body_silhouette.png или по умолчанию PNG с Wikimedia Commons.
    """
    import os
    # Локальный PNG имеет приоритет
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_body_path = os.path.join(script_dir, "assets", "body_silhouette.png")
    body_src = local_body_path if os.path.isfile(local_body_path) else BODY_SILHOUETTE_URL
    # Для img в HTML нужен URL; локальный путь в Streamlit не сработает как src, используем data или URL
    if os.path.isfile(local_body_path):
        try:
            import base64
            with open(local_body_path, "rb") as f:
                body_b64 = base64.b64encode(f.read()).decode("utf-8")
            body_src = f"data:image/png;base64,{body_b64}"
        except Exception:
            body_src = BODY_SILHOUETTE_URL

    # viewBox 0 0 1000 560: запас по краям, подписи не обрезаются (тело по центру 500)
    # Слева x=220 — текст заканчивается у линии (anchor end). Справа x=780 — текст начинается у линии (anchor start)
    label_positions = [
        (220, 28), (780, 120), (780, 28), (500, 532), (780, 200), (220, 200),
        (780, 280), (220, 360), (780, 360), (220, 100), (220, 280), (500, 28),
    ]
    body_cx, body_cy = 500, 280

    def esc(s):
        if s is None:
            return ""
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    lines_and_labels = []
    for i, system in enumerate(system_names):
        if i >= len(label_positions):
            break
        lx, ly = label_positions[i]
        name_ru = get_system_name_ru_fn(system)
        score = group_scores.get(system)
        if score is not None:
            pct = max(0.0, min(100.0, round(float(score) * 20.0, 0)))
            text = f"{esc(name_ru)} {pct:.0f}%"
            if pct <= 44:
                color = "#e74c3c"
            elif pct <= 65:
                color = "#f1c40f"
            else:
                color = "#2ecc71"
        else:
            text = f"{esc(name_ru)} —"
            color = "#95a5a6"
        lines_and_labels.append((lx, ly, text, color))

    def ellipse_point(lx, ly):
        import math
        dx, dy = lx - body_cx, ly - body_cy
        if dx == 0 and dy == 0:
            return body_cx + 70, body_cy
        r = math.sqrt(dx * dx + dy * dy)
        if r == 0:
            return body_cx + 70, body_cy
        rx, ry = 70, 200
        nx, ny = dx / r, dy / r
        t = math.atan2(ny * rx, nx * ry)
        ex = body_cx + rx * math.cos(t)
        ey = body_cy + ry * math.sin(t)
        return ex, ey

    def curved_path(lx, ly, ex, ey):
        """Квадратичная кривая Безье: от подписи к телу с контрольной точкой."""
        import math
        mid_y = (ly + ey) / 2
        # Контрольная точка смещена от прямой, чтобы линия изгибалась
        bend = 50
        if lx < body_cx:
            cpx, cpy = lx - bend, mid_y
        else:
            cpx, cpy = lx + bend, mid_y
        return f"M {lx:.1f} {ly:.1f} Q {cpx:.1f} {cpy:.1f} {ex:.1f} {ey:.1f}"

    # SVG: overflow visible, чтобы длинные подписи не обрезались по краям
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 560" preserveAspectRatio="xMidYMid meet" overflow="visible" '
        'style="position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;font-family:system-ui,sans-serif;overflow:visible;">',
    ]
    for (lx, ly, text, color) in lines_and_labels:
        ex, ey = ellipse_point(lx, ly)
        path_d = curved_path(lx, ly, ex, ey)
        svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.8"/>')
        # Слева от тела: текст заканчивается у линии (anchor end), чтобы вся подпись была в зоне 0..200
        # Справа: текст начинается у линии (anchor start), подпись в зоне 700..900
        if lx < body_cx:
            anchor, x_off = "end", -12
        else:
            anchor, x_off = "start", 12
        tx = lx + x_off
        svg_parts.append(f'<text x="{tx}" y="{ly + 4}" text-anchor="{anchor}" font-size="12" fill="#2c3e50" style="white-space:nowrap;">{text}</text>')
    svg_parts.append("</svg>")

    # Контейнер: ширина до 1000px, overflow visible
    return (
        '<div style="text-align:center;padding:1rem 0;overflow:visible;">'
        '<div style="position:relative;min-width:320px;width:100%;max-width:1000px;height:560px;margin:0 auto;overflow:visible;">'
        f'<img src="{body_src}" alt="Силуэт тела" style="position:absolute;left:50%;top:0;transform:translateX(-50%);width:auto;max-width:280px;height:100%;object-fit:contain;pointer-events:none;"/>'
        f'{"".join(svg_parts)}'
        '</div></div>'
    )


# Референсы, зависящие от пола (factor_id -> пол -> (norm_min, norm_max))
# Источники: NKF/KDOQI, WHO/IDF, лабораторные референсы для взрослых
SEX_AGE_NORMS = {
    "R001": {"M": (62.0, 106.0), "F": (53.0, 97.0)},   # Креатинин (мкмоль/л)
    "MU004": {"M": (62.0, 106.0), "F": (53.0, 97.0)},  # Креатинин в группе мышц
    "R004": {"M": (200.0, 420.0), "F": (140.0, 340.0)}, # Мочевая кислота (мкмоль/л)
    "SK002": {"M": (30.0, 300.0), "F": (10.0, 150.0)},  # Ферритин (мкг/л)
    "M005": {"M": (80.0, 94.0), "F": (70.0, 80.0)},    # Окружность талии (см), IDF
}

def apply_sex_age_norms(df, sex, age):
    """
    Возвращает копию df с подставленными norm_min, norm_max для показателей,
    зависящих от пола (и при необходимости возраста). Без изменений, если sex не задан.
    """
    if df is None or df.empty:
        return df
    if not sex or str(sex).strip() not in ("M", "F", "М", "Ж", "Мужской", "Женский"):
        return df.copy()
    sex_key = "M" if str(sex).strip() in ("M", "М", "Мужской") else "F"
    out = df.copy()
    for idx, row in out.iterrows():
        fid = row.get("factor_id")
        if fid and fid in SEX_AGE_NORMS and sex_key in SEX_AGE_NORMS[fid]:
            nmin, nmax = SEX_AGE_NORMS[fid][sex_key]
            out.at[idx, "norm_min"] = nmin
            out.at[idx, "norm_max"] = nmax
    return out

def calculate_risk(val, v_min, v_max, n_min, n_max, u_type):
    """
    Рассчитывает балл риска по инвертированной шкале:
    - 5.0 = отлично (норма)
    - 1.0 = критично (плохо)
    """
    if u_type == "select":
        # Для select: 0.0 -> 5.0, 0.5 -> 3.0, 1.0 -> 1.0
        risk = float(val)
        return 5.0 - (risk * 4.0)
    
    # Если значение в норме - возвращаем максимальный балл
    if n_min <= val <= n_max:
        return 5.0
    
    # Рассчитываем риск отклонения (0.0-1.0)
    if val < n_min:
        denom = n_min - v_min
        risk = abs(n_min - val) / denom if denom != 0 else 1.0
    else:
        denom = v_max - n_max
        risk = abs(val - n_max) / denom if denom != 0 else 1.0
    
    risk = min(max(risk, 0.0), 1.0)
    # Инвертируем: 0.0 риск -> 5.0 балл, 1.0 риск -> 1.0 балл
    return 5.0 - (risk * 4.0)

def has_sufficient_data(group_df, user_inputs, min_factors=3):
    """Проверяет, достаточно ли данных для расчета группы"""
    available_factors = sum(1 for _, row in group_df.iterrows() 
                           if user_inputs.get(row['factor_id'], 0) is not None)
    return available_factors >= min_factors

def calculate_adaptive_score(group_scores, available_groups, min_groups=4):
    """
    Адаптивная модель расчета итогового индекса
    Работает даже при неполных данных
    Теперь работает с баллами 1-5 (5 = хорошо, 1 = плохо)
    """
    if len(available_groups) < min_groups:
        # Недостаточно данных - упрощенный расчет
        if len(available_groups) == 0:
            return None, "Недостаточно данных для расчета"
        
        # Используем только доступные группы
        avg_score = sum(group_scores[g] for g in available_groups) / len(available_groups)
        min_score = min(group_scores[g] for g in available_groups)  # Минимальный балл (самый плохой)
        # Учитываем средний балл и худший показатель
        final_score = (avg_score * 0.7) + (min_score * 0.3)
        
        warning = f"⚠️ Данные доступны только для {len(available_groups)} из 9 систем. Результат может быть менее точным."
        return final_score, warning
    
    # Достаточно данных - полный расчет
    avg_score = sum(group_scores.values()) / len(group_scores)
    min_score = min(group_scores.values())  # Учитываем худший показатель
    final_score = (avg_score * 0.6) + (min_score * 0.4)
    
    return final_score, None

def _clear_gigachat_token():
    """Сбрасывает сохранённый токен GigaChat (для обновления при 401)."""
    for key in ("gigachat_access_token", "gigachat_token_expires_at"):
        if key in st.session_state:
            del st.session_state[key]


def get_gigachat_access_token():
    """
    Получение access token для GigaChat API через OAuth.
    Токен кэшируется в session_state с учётом срока жизни (expires_at/expires_in из ответа).
    При истечении срока или при 401 вызывающий код сбрасывает токен через _clear_gigachat_token() и запрашивает заново.
    """
    if not GIGACHAT_CLIENT_ID:
        return None, "Client ID не указан"
    
    # Используем сохранённый токен, если он ещё действителен (с запасом 60 сек)
    now = time.time()
    cached = st.session_state.get("gigachat_access_token")
    expires_at = st.session_state.get("gigachat_token_expires_at", 0)
    if cached and expires_at > now + 60:
        return cached, None
    
    try:
        # Получаем Authorization key из secrets (если указан напрямую)
        auth_data = None
        try:
            auth_key = st.secrets.get("GIGACHAT_AUTH_KEY", "")
            if auth_key:
                # Если указан готовый Authorization key в base64 (без префикса Basic)
                auth_data = auth_key.strip()
        except Exception:
            pass
        
        # Если нет готового ключа, формируем из Client ID и Secret
        if not auth_data:
            try:
                client_secret = st.secrets.get("GIGACHAT_CLIENT_SECRET", "")
            except Exception:
                client_secret = ""
            
            if not client_secret:
                return None, "Требуется GIGACHAT_CLIENT_SECRET или GIGACHAT_AUTH_KEY в secrets.toml. Client Secret можно получить на developers.sber.ru"
            
            # Формируем Basic Auth (Client ID:Client Secret в base64)
            auth_string = f"{GIGACHAT_CLIENT_ID}:{client_secret}"
            auth_data = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8').strip()
        
        import uuid
        rquid = str(uuid.uuid4())
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        max_retries = 3
        timeout = 30
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    GIGACHAT_AUTH_URL,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "RqUID": rquid,
                        "Authorization": f"Basic {auth_data}"
                    },
                    data={"scope": GIGACHAT_SCOPE},
                    timeout=timeout,
                    verify=False
                )
                break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    continue
                return None, f"Превышено время ожидания ({timeout} сек) после {max_retries} попыток. Проверьте интернет-соединение или попробуйте позже."
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    continue
                return None, f"Ошибка подключения к серверу GigaChat: {str(e)}. Проверьте интернет-соединение."
            except Exception as e:
                return None, f"Неожиданная ошибка при запросе токена: {str(e)}"
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            if not access_token:
                return None, f"Не получен access_token в ответе. Ответ: {result}"
            # Срок жизни: GigaChat может вернуть expires_at (Unix) или expires_in (секунды)
            expires_at_sec = result.get('expires_at')  # Unix timestamp
            expires_in_sec = result.get('expires_in')   # секунды до истечения
            if expires_at_sec is not None:
                st.session_state["gigachat_token_expires_at"] = float(expires_at_sec)
            elif expires_in_sec is not None:
                st.session_state["gigachat_token_expires_at"] = now + float(expires_in_sec)
            else:
                # По умолчанию считаем токен действительным 25 минут (типично для OAuth)
                st.session_state["gigachat_token_expires_at"] = now + 1500
            st.session_state["gigachat_access_token"] = access_token
            return access_token, None
        else:
            error_text = response.text[:500] if response.text else "Пустой ответ"
            try:
                error_json = response.json()
                error_msg = error_json.get('message', error_text)
                error_code = error_json.get('code', '')
                if error_code == 4:
                    return None, f"Ошибка авторизации (код {error_code}): {error_msg}. Проверьте, что GIGACHAT_CLIENT_SECRET указан правильно в secrets.toml."
                return None, f"Ошибка авторизации (код {error_code}): {error_msg}"
            except Exception:
                return None, f"Ошибка авторизации: {response.status_code} - {error_text}"
    except Exception as e:
        return None, f"Ошибка при получении токена: {str(e)}"

def get_gigachat_chat_response(user_message, chat_history, user_inputs=None, group_scores=None, df=None, user_sex=None, user_age=None):
    """
    Получение ответа от GigaChat для диалога
    """
    # Проверка наличия настроек API
    if not GIGACHAT_CLIENT_ID and not GIGACHAT_API_KEY:
        return None, "API не настроен. Требуется GIGACHAT_CLIENT_ID в secrets.toml"
    
    # Получаем access token (если используется OAuth)
    access_token = None
    if GIGACHAT_CLIENT_ID:
        token, error = get_gigachat_access_token()
        if error:
            return None, f"Ошибка авторизации: {error}"
        access_token = token
    elif GIGACHAT_API_KEY:
        access_token = GIGACHAT_API_KEY
    
    # Получаем настройки промпта
    try:
        system_role = st.secrets.get("GIGACHAT_SYSTEM_ROLE", "Ты эксперт по превентивной медицине и здоровому образу жизни.")
        prompt_style = st.secrets.get("GIGACHAT_PROMPT_STYLE", "практичный, мотивирующий")
        max_words = st.secrets.get("GIGACHAT_MAX_WORDS", 200)
        prompt_tone = st.secrets.get("GIGACHAT_PROMPT_TONE", "дружелюбный, поддерживающий")
        focus_areas = st.secrets.get("GIGACHAT_FOCUS_AREAS", "образ жизни, питание, физическая активность, сон, управление стрессом")
        restrictions = st.secrets.get("GIGACHAT_RESTRICTIONS", "Не назначай лекарства и не стави диагнозы. Фокусируйся на профилактике и образе жизни.")
    except:
        system_role = "Ты эксперт по превентивной медицине и здоровому образу жизни."
        prompt_style = "практичный, мотивирующий"
        max_words = 200
        prompt_tone = "дружелюбный, поддерживающий"
        focus_areas = "образ жизни, питание, физическая активность, сон, управление стрессом"
        restrictions = "Не назначай лекарства и не стави диагнозы. Фокусируйся на профилактике и образе жизни."
    
    # Формируем сообщения для API
    messages = [{"role": "system", "content": system_role}]
    
    # Проверяем, был ли уже добавлен контекст здоровья (по наличию сообщения assistant в истории)
    context_added = any(msg.get("role") == "assistant" and "ознакомился с данными" in msg.get("content", "") for msg in chat_history)
    
    # Добавляем контекст здоровья только один раз в начале диалога
    if not context_added and user_inputs and group_scores and df is not None:
        low_score_factors = []
        for _, row in df.iterrows():
            score_value = user_inputs.get(row['factor_id'], None)
            # Теперь низкий балл (<= 2.5) означает проблему
            if score_value is not None and score_value <= 2.5:
                low_score_factors.append({
                    'factor': row['factor_name'],
                    'score': score_value,
                })
        
        if low_score_factors or group_scores:
            sex_age_line = ""
            if user_sex or user_age is not None:
                sex_str = "Мужской" if user_sex == "M" else "Женский" if user_sex == "F" else "не указан"
                age_str = f"{user_age} лет" if user_age is not None else "не указан"
                sex_age_line = f"Пол: {sex_str}, Возраст: {age_str}.\n\n"
            health_context = f"""Контекст о здоровье пользователя:
{sex_age_line}Оценки здоровья по системам (шкала 1-5, где 5 = отлично, 1 = критично):
{json.dumps(group_scores, ensure_ascii=False, indent=2)}

"""
            if low_score_factors:
                health_context += f"""Факторы с низким баллом (требуют внимания):
{json.dumps(low_score_factors, ensure_ascii=False, indent=2)}

"""
            health_context += "Теперь можешь отвечать на вопросы пользователя, учитывая эти данные о здоровье (в т.ч. пол и возраст)."
            
            messages.append({
                "role": "user",
                "content": health_context
            })
            messages.append({
                "role": "assistant",
                "content": "Понял, я ознакомился с данными о здоровье. Готов отвечать на ваши вопросы."
            })
    
    # Добавляем историю чата (только реальные сообщения пользователя и ассистента, без служебных)
    for msg in chat_history:
        # Пропускаем служебное сообщение о контексте здоровья, если оно уже было
        if msg.get("role") == "assistant" and "ознакомился с данными" in msg.get("content", ""):
            continue
        # Добавляем только сообщения с ролями user и assistant
        if msg.get("role") in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": user_message})
    
    if not access_token:
        return None, "Не удалось получить access token"
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        max_retries = 2
        timeout = 30
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    GIGACHAT_API_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "GigaChat",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=timeout,
                    verify=False
                )
                break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    continue
                else:
                    return None, f"Превышено время ожидания ответа ({timeout} сек) после {max_retries} попыток."
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    continue
                else:
                    return None, f"Не удалось подключиться к серверу по адресу {GIGACHAT_API_URL}."
            except Exception as e:
                return None, f"Ошибка при запросе к API: {str(e)}"
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content:
                return content, None
            else:
                return None, "Пустой ответ от API"
        if response.status_code == 401 and GIGACHAT_CLIENT_ID:
            # Токен истёк — сбрасываем и повторяем запрос один раз с новым токеном
            _clear_gigachat_token()
            token, err = get_gigachat_access_token()
            if err:
                return None, f"Токен истёк, не удалось обновить: {err}"
            access_token = token
            try:
                response = requests.post(
                    GIGACHAT_API_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "GigaChat",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=timeout,
                    verify=False
                )
            except Exception as e:
                return None, f"Ошибка при повторном запросе: {str(e)}"
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if content:
                    return content, None
            return None, f"Ошибка API: {response.status_code} - {response.text[:100]}"
        return None, f"Ошибка API: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return None, f"Ошибка при запросе к API: {str(e)}"
    
    return None, "Неизвестная ошибка"

def get_gigachat_recommendations(user_inputs, group_scores, df, user_sex=None, user_age=None):
    """
    Получение персонализированных рекомендаций от GigaChat
    """
    # Проверка наличия настроек API
    if not GIGACHAT_CLIENT_ID and not GIGACHAT_API_KEY:
        return None, "API не настроен. Требуется GIGACHAT_CLIENT_ID в secrets.toml"
    
    # Получаем access token (если используется OAuth)
    access_token = None
    if GIGACHAT_CLIENT_ID:
        token, error = get_gigachat_access_token()
        if error:
            return None, f"Ошибка авторизации: {error}"
        access_token = token
    elif GIGACHAT_API_KEY:
        # Для обратной совместимости с self-hosted версиями
        access_token = GIGACHAT_API_KEY
    
    # Подготовка контекста для AI
    low_score_factors = []
    for _, row in df.iterrows():
        score_value = user_inputs.get(row['factor_id'], None)
        # Теперь низкий балл (<= 2.5) означает проблему
        if score_value is not None and score_value <= 2.5:
            low_score_factors.append({
                'factor': row['factor_name'],
                'score': score_value,
                'recommendation': row.get('recommendation', '')
            })
    
    # Получаем настройки промпта из secrets (с значениями по умолчанию)
    try:
        system_role = st.secrets.get("GIGACHAT_SYSTEM_ROLE", "Ты эксперт по превентивной медицине и здоровому образу жизни.")
        prompt_style = st.secrets.get("GIGACHAT_PROMPT_STYLE", "практичный, мотивирующий")
        max_words = st.secrets.get("GIGACHAT_MAX_WORDS", 200)
        prompt_tone = st.secrets.get("GIGACHAT_PROMPT_TONE", "дружелюбный, поддерживающий")
        focus_areas = st.secrets.get("GIGACHAT_FOCUS_AREAS", "образ жизни, питание, физическая активность, сон, управление стрессом")
        restrictions = st.secrets.get("GIGACHAT_RESTRICTIONS", "Не назначай лекарства и не стави диагнозы. Фокусируйся на профилактике и образе жизни.")
    except:
        # Значения по умолчанию
        system_role = "Ты эксперт по превентивной медицине и здоровому образу жизни."
        prompt_style = "практичный, мотивирующий"
        max_words = 200
        prompt_tone = "дружелюбный, поддерживающий"
        focus_areas = "образ жизни, питание, физическая активность, сон, управление стрессом"
        restrictions = "Не назначай лекарства и не стави диагнозы. Фокусируйся на профилактике и образе жизни."
    
    sex_age_line = ""
    if user_sex or user_age is not None:
        sex_str = "Мужской" if user_sex == "M" else "Женский" if user_sex == "F" else "не указан"
        age_str = f"{user_age} лет" if user_age is not None else "не указан"
        sex_age_line = f"Пол: {sex_str}, Возраст: {age_str}.\n\n"
    # Формирование запроса с настраиваемыми параметрами
    prompt = f"""
    Проанализируй следующие данные о здоровье пользователя:
    {sex_age_line}Оценки здоровья по системам (шкала 1-5, где 5 = отлично, 1 = критично):
    {json.dumps(group_scores, ensure_ascii=False, indent=2)}
    
    Факторы с низким баллом (требуют внимания):
    {json.dumps(low_score_factors, ensure_ascii=False, indent=2)}
    
    Предоставь персонализированные рекомендации по улучшению здоровья, учитывая взаимосвязи между системами.
    
    Требования к ответу:
    - Стиль: {prompt_style}
    - Тон: {prompt_tone}
    - Объем: до {max_words} слов
    - Фокус на: {focus_areas}
    - Ограничения: {restrictions}
    
    Ответ должен быть структурированным, конкретным и легко применимым на практике.
    """
    
    if not access_token:
        return None, "Не удалось получить access token"
    
    try:
        # Отключаем проверку SSL для self-hosted или корпоративных серверов
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Увеличиваем таймаут для запроса рекомендаций
        max_retries = 2
        timeout = 30  # Увеличиваем таймаут до 30 секунд
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    GIGACHAT_API_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                json={
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
                    timeout=timeout,
                    verify=False  # Отключаем проверку SSL для работы с self-signed сертификатами
                )
                break  # Успешный запрос, выходим из цикла
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    continue  # Пробуем еще раз
                else:
                    return None, f"Превышено время ожидания ответа от GigaChat ({timeout} сек) после {max_retries} попыток. Сервер может быть перегружен, попробуйте позже."
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    continue  # Пробуем еще раз
                else:
                    return None, f"Не удалось подключиться к GigaChat серверу по адресу {GIGACHAT_API_URL}. Проверьте интернет-соединение."
            except Exception as e:
                return None, f"Ошибка при запросе к API: {str(e)}"
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content:
                return content, None
            return None, "Пустой ответ от API"
        if response.status_code == 401 and GIGACHAT_CLIENT_ID:
            _clear_gigachat_token()
            token, err = get_gigachat_access_token()
            if err:
                return None, f"Токен истёк, не удалось обновить: {err}"
            access_token = token
            try:
                response = requests.post(
                    GIGACHAT_API_URL,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    json={
                        "model": "GigaChat",
                        "messages": [
                            {"role": "system", "content": system_role},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    },
                    timeout=timeout,
                    verify=False
                )
            except Exception as e:
                return None, f"Ошибка при повторном запросе: {str(e)}"
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if content:
                    return content, None
            return None, f"Ошибка API: {response.status_code} - {response.text[:100]}"
        return None, f"Ошибка API: {response.status_code} - {response.text[:100]}"
    except requests.exceptions.ConnectionError:
        return None, f"Не удалось подключиться к GigaChat серверу по адресу {GIGACHAT_API_URL}. Проверьте, что сервер запущен."
    except requests.exceptions.Timeout:
        return None, "Превышено время ожидания ответа от GigaChat сервера."
    except Exception as e:
        return None, f"Ошибка при запросе к API: {str(e)}"
    
    return None, "Неизвестная ошибка"

def build_inputs(df, risk_groups, mode, calculation_done_state=False):
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
            group_name_ru = get_system_name_ru(group)
            st.sidebar.markdown(f"## {group_name_ru}")
            desc = get_system_description_from_df(df, group)
            if desc:
                st.sidebar.caption(desc)
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
                    options = {"Норма": 5.0, "Умеренно": 3.0, "Критично": 1.0}
                    choice = st.sidebar.selectbox(label, list(options.keys()), key=f"sel_{f_id}")
                    user_inputs[f_id] = options[choice]
    else:
        # В режиме "Тест"
        if calculation_done_state:
            # Если расчет уже выполнен (перезагрузка страницы после расчета), просто формируем user_inputs
            # без отображения UI теста.
            user_inputs = {}
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
                    options = {"Норма": 5.0, "Умеренно": 3.0, "Критично": 1.0}
                    choice = st.session_state.test_answers.get(f_id, "Норма")
                    user_inputs[f_id] = options.get(choice, 5.0)
            return user_inputs

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
        current_group_ru = get_system_name_ru(current_group)
        st.markdown(f"### Шаг {step + 1} из {total_steps}: {current_group_ru}")
        desc = get_system_description_from_df(df, current_group)
        if desc:
            st.caption(desc)

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
                options = {"Норма": 5.0, "Умеренно": 3.0, "Критично": 1.0}
                choice = st.session_state.test_answers.get(f_id, "Норма")
                user_inputs[f_id] = options.get(choice, 5.0)
    return user_inputs

df = get_data()

if df is not None and not df.empty:
    st.title("🛡️ Integral Health Score 10.0")
    st.markdown("_Комплексная оценка 12 системных рисков здоровью_")
    
    # --- Пол и возраст (влияют на референсы части показателей) ---
    if "user_sex" not in st.session_state:
        st.session_state.user_sex = None
    if "user_age" not in st.session_state:
        st.session_state.user_age = None
    
    st.sidebar.markdown("### 👤 Базовые данные")
    user_sex = st.sidebar.radio("Пол", ["Не указан", "Мужской", "Женский"], index=0, key="input_sex")
    user_age = st.sidebar.number_input("Возраст (лет)", min_value=1, max_value=120, value=30, step=1, key="input_age")
    st.sidebar.caption("Пол влияет на нормы креатинина, ферритина, окружности талии и мочевой кислоты. Возраст передаётся в рекомендации.")
    
    if user_sex == "Не указан":
        st.session_state.user_sex = None
    else:
        st.session_state.user_sex = "M" if user_sex == "Мужской" else "F"
    st.session_state.user_age = int(user_age) if user_age else None
    
    # Применяем полозависимые нормы (креатинин, ферритин, окружность талии, мочевая кислота)
    df = apply_sex_age_norms(df, st.session_state.user_sex, st.session_state.user_age)
    
    # Исключаем Oxidative из расчета
    risk_groups = sorted([g for g in df['Risk_Group'].unique() if g and pd.notna(g) and g != 'Oxidative'])
    input_mode = st.sidebar.radio("Режим ввода", ["Тест (по порядку)", "Слайдеры"], index=0)

    # --- Загрузить бланк (OCR) ---
    if OCR_AVAILABLE:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📄 Загрузить бланк")
        ocr_engine = st.sidebar.radio(
            "Способ распознавания",
            ["Локальный (Tesseract)", "Yandex Vision (облако)"],
            index=0,
            help="Локальный — без облака и ключей; Yandex — нужен API-ключ и права.",
        )
        use_local_ocr = ocr_engine == "Локальный (Tesseract)"
        st.sidebar.caption("Распознавание показателей с фото/скана или PDF (первая страница).")
        _secrets = st.secrets if hasattr(st, "secrets") else {}
        yandex_key = _secrets.get("YANDEX_VISION_API_KEY", "") or ""
        yandex_iam = _secrets.get("YANDEX_VISION_IAM_TOKEN", "") or ""
        yandex_folder_id = (_secrets.get("YANDEX_VISION_FOLDER_ID", "") or "").strip()
        if not yandex_folder_id and yandex_iam.strip():
            yandex_folder_id = "b1gaq3t2uh4lfs56jtks"
        ocr_auth = yandex_key.strip() or yandex_iam.strip()
        ocr_can_run = use_local_ocr and TESSERACT_AVAILABLE or (not use_local_ocr and ocr_auth)
        ocr_upload = st.sidebar.file_uploader("Фото, скан или PDF", type=["png", "jpg", "jpeg", "pdf"], key="ocr_upload")
        ocr_recognize = st.sidebar.button("🔍 Распознать", key="ocr_recognize", help="Лучше работает со сканом или чётким фото")
        if ocr_recognize and ocr_upload and ocr_can_run:
            with st.spinner("Распознавание..."):
                raw_bytes = ocr_upload.getvalue()
                is_pdf = (ocr_upload.type or "").strip().lower() == "application/pdf" or (ocr_upload.name or "").lower().endswith(".pdf")
                if is_pdf:
                    from ocr_vision import pdf_to_image_bytes
                    img_bytes, pdf_err = pdf_to_image_bytes(raw_bytes, page_index=0)
                    if pdf_err:
                        st.sidebar.error(pdf_err)
                        img_bytes = None
                else:
                    img_bytes = raw_bytes
                if img_bytes is not None:
                    if use_local_ocr:
                        raw_text, err = tesseract_ocr(img_bytes)
                    else:
                        raw_text, err = yandex_vision_ocr(
                            img_bytes,
                            api_key=yandex_key or None,
                            iam_token=yandex_iam or None,
                            folder_id=yandex_folder_id or None,
                        )
                    if err:
                        st.sidebar.error(err)
                    else:
                        parsed = parse_lab_text(raw_text or "")
                        extracted = map_to_factors(parsed, df)
                        st.session_state.ocr_extracted = extracted
                        st.session_state.ocr_parsed = parsed
                        st.session_state.ocr_raw_text = raw_text or ""
                        st.session_state.ocr_show_modal = True
                        st.rerun()
        if use_local_ocr and not TESSERACT_AVAILABLE and OCR_AVAILABLE:
            st.sidebar.caption("Установите: pip install pytesseract Pillow и Tesseract (macOS: brew install tesseract tesseract-lang)")
        if not use_local_ocr and not ocr_auth and OCR_AVAILABLE:
            st.sidebar.caption("Для Yandex Vision укажите YANDEX_VISION_API_KEY в `.streamlit/secrets.toml`")

        # Попап с результатами сканирования (открывается после «Распознать»)
        if st.session_state.get("ocr_show_modal") and st.session_state.get("ocr_extracted") is not None:

            @st.dialog("Результаты сканирования", width="large", dismissible=False)
            def show_ocr_dialog(dataframe):
                ocr_extracted = st.session_state.ocr_extracted
                ocr_parsed = st.session_state.get("ocr_parsed", [])
                ocr_raw_text = st.session_state.get("ocr_raw_text", "")
                st.caption("Проверьте распознанные данные, затем нажмите «Добавить в расчёт» или закройте окно.")
                with st.expander("📄 Текст с бланка (OCR)", expanded=False):
                    if ocr_raw_text:
                        st.text_area("", value=ocr_raw_text, height=100, disabled=True, key="ocr_popup_raw", label_visibility="collapsed")
                    else:
                        st.caption("Текст не сохранён.")
                with st.expander("📊 Распознанные показатели (до маппинга)", expanded=True):
                    if ocr_parsed:
                        parsed_rows = [{"Показатель": p.get("name", ""), "Значение": p.get("value", ""), "Ед.": p.get("unit", "")} for p in ocr_parsed]
                        st.dataframe(pd.DataFrame(parsed_rows), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Нет распарсенных строк.")
                st.markdown("**Подставлено в модель рисков:**")
                rows = []
                for fid, val in ocr_extracted.items():
                    r = dataframe[dataframe["factor_id"] == fid]
                    if not r.empty:
                        name = r.iloc[0].get("factor_name", fid)
                        unit = r.iloc[0].get("unit_name", "")
                        rows.append({"Показатель": name, "Значение": val, "Ед.": unit})
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                add_btn = st.button("✅ Добавить в расчёт", type="primary", key="ocr_popup_add")
                close_btn = st.button("Закрыть", key="ocr_popup_close")
                if add_btn:
                    if "test_answers" not in st.session_state:
                        st.session_state.test_answers = {}
                    for _, row in dataframe.iterrows():
                        f_id, u_type = row["factor_id"], str(row.get("unit_type", "")).strip()
                        if f_id in ocr_extracted and "range" in u_type:
                            st.session_state.test_answers[f_id] = ocr_extracted[f_id]
                    st.session_state.calculation_done = False
                    for key in ("ocr_extracted", "ocr_parsed", "ocr_raw_text", "ocr_show_modal"):
                        if key in st.session_state:
                            del st.session_state[key]
                    st.success("Добавлено в расчёт. Закройте окно или перейдите в «Тест (по порядку)» и нажмите «Рассчитать».")
                    st.rerun()
                if close_btn:
                    for key in ("ocr_extracted", "ocr_parsed", "ocr_raw_text", "ocr_show_modal"):
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

            show_ocr_dialog(df)

    # Для тестирования: сразу перейти к результатам с значениями по умолчанию (без прохода по 12 шагам)
    if input_mode == "Тест (по порядку)" and not st.session_state.get("calculation_done", False):
        if st.sidebar.button("⚡ Перейти к результатам (значения по умолчанию)", help="Заполняет все показатели серединой нормы и запускает расчёт"):
            defaults = {}
            for _, row in df.iterrows():
                f_id = row.get("factor_id")
                u_type = str(row.get("unit_type", "")).strip()
                if "range" in u_type:
                    min_val = float(row.get("min_val", 0))
                    max_val = float(row.get("max_val", 1))
                    n_min = float(row.get("norm_min", 0))
                    n_max = float(row.get("norm_max", 1))
                    mid = (n_min + n_max) / 2.0
                    defaults[f_id] = max(min_val, min(max_val, mid))
                elif u_type == "select":
                    defaults[f_id] = "Норма"
            st.session_state.test_answers = defaults
            st.session_state.test_done = True
            st.session_state.test_step = max(len(risk_groups), 1) - 1
            st.rerun()

    user_inputs = build_inputs(df, risk_groups, "Слайдеры" if input_mode == "Слайдеры" else "Тест", st.session_state.get("calculation_done", False))

    # Инициализация session state для результатов расчета
    if "calculation_done" not in st.session_state:
        st.session_state.calculation_done = False
    if "group_scores" not in st.session_state:
        st.session_state.group_scores = {}
    if "final_score" not in st.session_state:
        st.session_state.final_score = None
    if "warning" not in st.session_state:
        st.session_state.warning = None

    # Кнопка расчета только для режима "Слайдеры" (в сайдбаре)
    # В режиме "Тест" расчет запускается автоматически после нажатия "Рассчитать" в навигации
    calculate_button = False
    if input_mode == "Слайдеры":
        st.sidebar.markdown("---")
        calculate_button = st.sidebar.button("🔢 Рассчитать", type="primary", use_container_width=True)
    elif input_mode == "Тест (по порядку)":
        # В режиме "Тест" расчёт запускаем только один раз: когда пользователь нажал «Рассчитать» (test_done),
        # но расчёт ещё не выполнялся (иначе после rerun снова бы запускался расчёт и цикл rerun).
        if st.session_state.get("test_done", False) and not st.session_state.get("calculation_done", False):
            calculate_button = True
    
    if calculate_button:
        # --- АДАПТИВНЫЙ РАСЧЕТ ---
        group_scores = {}
        available_groups = []
        
        for group in risk_groups:
            g_df = df[df['Risk_Group'] == group]
            if not g_df.empty and has_sufficient_data(g_df, user_inputs, min_factors=2):
                total_w = g_df['Weight_Coefficient'].sum()
                # Теперь user_inputs содержит баллы 1-5, а не риски 0-1
                raw_score = sum(user_inputs.get(r['factor_id'], 0) * r['Weight_Coefficient'] 
                              for _, r in g_df.iterrows() 
                              if user_inputs.get(r['factor_id'], 0) is not None)
                if total_w > 0:
                    # Средневзвешенный балл группы (1-5)
                    group_scores[group] = raw_score / total_w
                    available_groups.append(group)

        # Адаптивный расчет итогового индекса
        final_score, warning = calculate_adaptive_score(group_scores, available_groups, min_groups=5)
        
        # Сохраняем результаты в session state
        st.session_state.group_scores = group_scores
        st.session_state.final_score = final_score
        st.session_state.warning = warning
        st.session_state.calculation_done = True
        st.rerun()
    
    # Используем сохраненные результаты
    group_scores = st.session_state.group_scores
    final_score = st.session_state.final_score
    warning = st.session_state.warning
    
    if not st.session_state.calculation_done:
        st.info("👆 Заполните параметры и нажмите кнопку 'Рассчитать' для получения результатов")
        st.stop()
    
    if warning:
        st.warning(warning)

    # --- Пересчёт в проценты и зоны (внутренний балл 1–5 не меняется) ---
    percent = score_to_percent(final_score)
    color, zone_name = get_zone_by_percent(percent)

    if percent is None:
        brief = "Недостаточно данных для расчета."
    elif percent >= 66:
        brief = "Состояние в норме."
    elif percent >= 31:
        brief = "Начало расхода резервных сил."
    else:
        brief = "Высокий риск системного отказа."

    st.markdown("---")
    percent_display = f"{percent:.0f}%" if percent is not None else "N/A"
    st.markdown(f"""
        <div style="background-color:{color}; padding:40px; border-radius:20px; text-align:center; color:white; border: 2px solid rgba(0,0,0,0.1);">
            <p style="margin:0; font-size:18px; font-weight:bold; opacity:0.8;">ИНТЕГРАЛЬНЫЙ ИНДЕКС ЗДОРОВЬЯ</p>
            <h1 style="margin:0; font-size:110px; line-height:1;">{percent_display}</h1>
            <h2 style="margin:5px 0; letter-spacing:3px;">{zone_name}</h2>
            <p style="font-size:20px; font-style:italic;">{brief}</p>
            <p style="font-size:14px; opacity:0.8; margin-top:10px;">20–44% красная зона · 45–65% жёлтая зона · 66–100% зелёная зона</p>
        </div>
    """, unsafe_allow_html=True)

    # Кнопка перезапуска теста (в режиме «Тест» — сброс шагов и расчёта)
    if input_mode == "Тест (по порядку)":
        if st.button("🔄 Начать сначала", type="secondary"):
            st.session_state.test_step = 0
            st.session_state.test_done = False
            st.session_state.test_answers = {}
            st.session_state.calculation_done = False
            st.session_state.group_scores = {}
            st.session_state.final_score = None
            st.session_state.warning = None
            st.rerun()

    # Оценка по системам: проекция на человека (12 групп рисков со сносками к телу)
    if group_scores:
        st.markdown("---")
        st.subheader("📊 Оценка по системам")
        system_names_list = ['Neuro', 'Cardio', 'Hormone', 'Metabolic', 'Immune',
                            'Renal', 'Hepatic', 'Musculoskeletal', 'Inflammatory', 'SkinHair',
                            'Gastric', 'Ocular']
        body_html = _body_projection_svg_html(system_names_list, group_scores, get_system_name_ru)
        st.markdown(body_html, unsafe_allow_html=True)
        # Таблица баллов по системам (свёрнутый блок)
        with st.expander("Таблица показателей по системам"):
            cols = st.columns(3)
            for col_idx in range(3):
                with cols[col_idx]:
                    for i in range(4):
                        system_idx = col_idx * 4 + i
                        if system_idx < len(system_names_list):
                            system = system_names_list[system_idx]
                            system_ru = get_system_name_ru(system)
                            if system in group_scores:
                                score = group_scores[system]
                                percent_system = max(0.0, min(100.0, round(score * 20.0, 0)))
                                st.metric(f"**{system_ru}**", f"{percent_system:.0f}%", delta=None)
                                st.progress(max(0.0, min(1.0, (score - 1.0) / 4.0)))
                            else:
                                st.metric(f"**{system_ru}**", "—", delta="Нет данных")
                                st.progress(0.0)

    # Чат с AI (опционально)
    st.markdown("---")
    ai_chat_enabled = st.sidebar.checkbox("💬 Чат с AI-консультантом", value=False)
    
    if ai_chat_enabled:
        st.subheader("💬 Диалог с AI-консультантом")
        
        # Инициализация истории чата в session state
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "health_context_sent" not in st.session_state:
            st.session_state.health_context_sent = False
        
        # Отображаем историю чата
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Поле ввода сообщения
        user_message = st.chat_input("Задайте вопрос о вашем здоровье...")
        
        if user_message:
            # Добавляем сообщение пользователя в историю и отображаем
            st.session_state.chat_history.append({"role": "user", "content": user_message})
            with st.chat_message("user"):
                st.markdown(user_message)
            
            # Получаем ответ от AI
            with st.chat_message("assistant"):
                with st.spinner("Думаю..."):
                    # Передаем историю без текущего сообщения пользователя
                    history_for_api = st.session_state.chat_history[:-1]
                    ai_response, error = get_gigachat_chat_response(
                        user_message,
                        history_for_api,
                        user_inputs,
                        group_scores,
                        df,
                        user_sex=st.session_state.get("user_sex"),
                        user_age=st.session_state.get("user_age"),
                    )
                
                if ai_response:
                    st.markdown(ai_response)
                    # Добавляем ответ AI в историю
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    # Помечаем, что контекст здоровья был отправлен (если это первый ответ)
                    if not st.session_state.health_context_sent and user_inputs and group_scores:
                        st.session_state.health_context_sent = True
                elif error:
                    st.error(f"⚠️ {error}")
                    # Не добавляем ошибку в историю, чтобы не ломать диалог
                    with st.expander("ℹ️ Как настроить GigaChat API"):
                        st.markdown("""
                        ### Настройка GigaChat API
                        
                        Для работы чата с AI требуется настроить GigaChat API в файле `.streamlit/secrets.toml`:
                        
                        ```toml
                        GIGACHAT_CLIENT_ID = "ваш-client-id"
                        GIGACHAT_CLIENT_SECRET = "ваш-client-secret"
                        GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
                        ```
                        
                        Или используйте готовый Authorization key:
                        ```toml
                        GIGACHAT_AUTH_KEY = "ваш-base64-ключ"
                        ```
                        
                        Подробные инструкции см. в файле `GIGACHAT_SETUP.md`
                        """)
        
        # Кнопка очистки истории
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Очистить историю"):
                st.session_state.chat_history = []
                st.session_state.health_context_sent = False
                st.rerun()
    
    # AI рекомендации (опционально, старый функционал)
    st.markdown("---")
    ai_enabled = st.sidebar.checkbox("🤖 Получить AI рекомендации", value=False)
    
    if ai_enabled:
        with st.spinner("Генерация персонализированных рекомендаций от AI..."):
            ai_result = get_gigachat_recommendations(
                user_inputs, group_scores, df,
                user_sex=st.session_state.get("user_sex"),
                user_age=st.session_state.get("user_age"),
            )
            
            if isinstance(ai_result, tuple):
                ai_recommendations, error_msg = ai_result
            else:
                ai_recommendations, error_msg = ai_result, None
            
            if ai_recommendations:
                st.subheader("🤖 Персонализированные рекомендации")
                st.markdown("""
                <div style="background-color:#e8f4f8; padding:20px; border-radius:10px; border-left:4px solid #1f77b4;">
                """, unsafe_allow_html=True)
                st.markdown(ai_recommendations)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error(f"⚠️ {error_msg if error_msg else 'Не удалось получить рекомендации от AI'}")
                with st.expander("ℹ️ Как настроить GigaChat API"):
                    st.markdown("""
                    **Для работы AI рекомендаций требуется:**
                    
                    1. **Self-hosted GigaChat сервер** (должен быть запущен и доступен)
                    2. **API URL** - адрес вашего GigaChat сервера (например: `http://localhost:8000/v1/chat/completions`)
                    3. **API Key** - ключ для авторизации
                    
                    **Настройка через Streamlit secrets:**
                    - Создайте файл `.streamlit/secrets.toml` в корне проекта
                    - Добавьте:
                    ```toml
                    GIGACHAT_API_URL = "http://ваш-сервер:порт/v1/chat/completions"
                    GIGACHAT_API_KEY = "ваш-api-ключ"
                    ```
                    
                    **Или через переменные окружения:**
                    ```bash
                    export GIGACHAT_API_URL="http://ваш-сервер:порт/v1/chat/completions"
                    export GIGACHAT_API_KEY="ваш-api-ключ"
                    ```
                    
                    **Без AI:** Приложение работает и без GigaChat - вы получите базовые рекомендации из базы данных.
                    """)

    st.markdown("---")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📋 План коррекции")
        low_score_count = 0
        for _, row in df.iterrows():
            factor_score = user_inputs.get(row['factor_id'], None)
            # Теперь низкий балл (<= 2.5) означает проблему
            if factor_score is not None and factor_score <= 2.5:
                low_score_count += 1
                with st.expander(f"📍 {row['factor_name']} (балл: {factor_score:.1f})", expanded=(low_score_count <= 3)):
                    st.warning(row['recommendation'])
        if low_score_count == 0:
            st.success("Все показатели в пределах нормы!")
    
    with col_r:
        st.subheader("💡 Анализ вклада факторов")
        # Показываем факторы с низкими баллами (проблемные)
        impact = {row['factor_name']: user_inputs.get(row['factor_id'], None)
                 for _, row in df.iterrows() 
                 if user_inputs.get(row['factor_id'], None) is not None}
        if impact:
            # Сортируем по возрастанию (худшие первыми)
            impact_series = pd.Series(impact).sort_values(ascending=True).head(10)
            st.bar_chart(impact_series)
            st.caption("Факторы отсортированы от худших (низкий балл) к лучшим")
        else:
            st.info("Нет данных для анализа")
else:
    st.error("Не удалось загрузить данные. Проверьте подключение к Google Sheets и файл credentials.json.")
    st.info("Пожалуйста, убедитесь, что файл credentials.json существует и содержит корректные учетные данные Google API.")
