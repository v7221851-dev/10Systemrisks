"""
Модуль распознавания лабораторных бланков.
- Yandex Vision API (облако).
Парсинг «показатель — значение — единица», маппинг на factor_id.
"""

import base64
import io
import re
import requests

VISION_URL = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"

# Опциональная поддержка PDF через PyMuPDF
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def pdf_to_image_bytes(pdf_bytes: bytes, page_index: int = 0, dpi: int = 150) -> tuple[bytes | None, str | None]:
    """
    Конвертирует одну страницу PDF в PNG (bytes).
    Возвращает (png_bytes, None) при успехе или (None, error_message).
    Для работы нужен пакет: pip install pymupdf
    """
    if not PDF_AVAILABLE:
        return None, "Для распознавания PDF установите пакет: pip install pymupdf"
    if not pdf_bytes:
        return None, "Файл PDF пустой"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_index >= len(doc):
            doc.close()
            return None, f"В PDF нет страницы с индексом {page_index}"
        page = doc.load_page(page_index)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes, None
    except Exception as e:
        return None, f"Ошибка чтения PDF: {e}"


def yandex_vision_ocr(
    image_bytes: bytes,
    api_key: str | None = None,
    iam_token: str | None = None,
    folder_id: str | None = None,
    timeout: int = 30,
) -> tuple[str | None, str | None]:
    """
    Отправляет изображение в Yandex Vision API (TEXT_DETECTION), возвращает распознанный текст.
    Аутентификация: либо api_key (Api-Key), либо iam_token (Bearer). Достаточно одного.
    При использовании IAM-токена (пользователь) API требует указать folder_id (заголовок x-folder-id).
    Статический ключ доступа (S3) для Vision API не поддерживается.
    """
    if not image_bytes:
        return None, "Изображение пустое"

    auth_header = None
    if iam_token and str(iam_token).strip():
        auth_header = f"Bearer {iam_token.strip()}"
    if not auth_header and api_key and str(api_key).strip():
        auth_header = f"Api-Key {api_key.strip()}"
    if not auth_header:
        return None, "Задайте YANDEX_VISION_API_KEY или YANDEX_VISION_IAM_TOKEN в secrets.toml"

    if auth_header.startswith("Bearer") and not (folder_id and str(folder_id).strip()):
        return None, "При IAM-токене укажите YANDEX_VISION_FOLDER_ID в secrets.toml (ID каталога)"

    try:
        content_b64 = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        return None, f"Ошибка кодирования изображения: {e}"

    payload = {
        "analyze_specs": [
            {
                "content": content_b64,
                "features": [
                    {
                        "type": "TEXT_DETECTION",
                        "text_detection_config": {"language_codes": ["ru", "en"]},
                    }
                ],
            }
        ]
    }

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }
    # При аутентификации по API-ключу (Api-Key) НЕ передаём x-folder-id — ключ уже привязан к каталогу.
    # Иначе возникает ошибка "Permission to resource-manager.folder ... denied".
    # folder_id передаём только для IAM-токена (Bearer).
    folder_id_clean = (folder_id and str(folder_id).strip()) or None
    if folder_id_clean and auth_header.startswith("Bearer"):
        headers["x-folder-id"] = folder_id_clean

    url = VISION_URL
    if folder_id_clean and auth_header.startswith("Bearer"):
        url = f"{VISION_URL}?folderId={folder_id_clean}"

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        return None, "Превышено время ожидания ответа от Yandex Vision"
    except requests.exceptions.RequestException as e:
        return None, f"Ошибка запроса: {str(e)}"

    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("message", err.get("error", resp.text[:200]))
        except Exception:
            msg = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
        return None, f"Vision API: {msg}"

    try:
        data = resp.json()
        # Структура ответа Yandex Vision: results[0].results[0].textDetection.pages[].blocks[].lines[].words[].text
        # См. https://github.com/yandex-cloud/ocr
        results = data.get("results", [])
        if not results:
            return None, "В ответе нет результатов"
        first = results[0]
        inner = first.get("results", [])
        if not inner:
            return "", None
        ann = inner[0] if isinstance(inner[0], dict) else inner
        # Вариант 1: textAnnotation.text (если API вернёт в старом формате)
        text = ann.get("textAnnotation", {}).get("text") if isinstance(ann.get("textAnnotation"), dict) else None
        if text and str(text).strip():
            return str(text).strip(), None
        # Вариант 2: textDetection.pages[].blocks[].lines[].words[].text — актуальный формат Yandex Vision
        text_detection = ann.get("textDetection") or ann.get("text_detection")
        if text_detection:
            pages = text_detection.get("pages", [])
            all_lines = []
            for page in pages:
                for block in page.get("blocks", []):
                    for line in block.get("lines", []):
                        words = line.get("words", [])
                        line_text = " ".join(str(w.get("text", "")).strip() for w in words if w.get("text"))
                        if line_text:
                            all_lines.append(line_text)
            if all_lines:
                return "\n".join(all_lines), None
        # Вариант 3: blocks[].lines[].text (без words)
        blocks = ann.get("blocks", [])
        lines = []
        for block in blocks:
            for line in block.get("lines", []):
                t = line.get("text", "").strip() if isinstance(line.get("text"), str) else ""
                if t:
                    lines.append(t)
                elif line.get("words"):
                    line_str = " ".join(str(w.get("text", "")).strip() for w in line["words"] if w.get("text")).strip()
                    if line_str:
                        lines.append(line_str)
        if lines:
            return "\n".join(lines), None
        # Пустой результат: возможно, изображение пустое или нечитаемое
        return "", None
    except Exception as e:
        return None, f"Ошибка разбора ответа: {e}"


def _normalize_ocr_line(line: str) -> str:
    """Убирает типичный шум OCR: лишние пробелы, звёздочки, заменяет запятую на точку в числах."""
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"\*+", "", line)
    return line


def parse_lab_text(raw_text: str) -> list[dict]:
    """
    Извлекает из сырого текста OCR пары «название показателя — значение — единица».
    Форматы: "Глюкоза 5.4 ммоль/л", "Креатинин: 90", "АЛТ - 25", "ТТГ (2.5) мМЕ/л", "СРБ < 5".
    Возвращает список словарей: [ {"name": str, "value": float, "unit": str}, ... ]
    """
    if not raw_text or not raw_text.strip():
        return []

    out = []
    num_pattern = r"([<>]?\s*)(\d+[,.]?\d*)"
    unit_suffix = r"\s*([а-яА-Яa-zA-Z0-9/%²³°·\s\-]+)?$"

    def normalize_num(s: str) -> float:
        s = s.strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    def clean_name(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip() if s else ""

    def clean_unit(s: str) -> str:
        return s.strip() if s else ""

    # Паттерны: название + разделитель + число + единица
    # num_pattern даёт группы: (<> опционально), (число)
    patterns = [
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s*[:]\s*" + num_pattern + r"\s*" + unit_suffix, re.UNICODE),
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s+[\-–—]\s*" + num_pattern + r"\s*" + unit_suffix, re.UNICODE),
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s+" + num_pattern + r"\s*" + unit_suffix, re.UNICODE),
    ]

    seen = set()
    for line in raw_text.splitlines():
        line = _normalize_ocr_line(line)
        if not line or len(line) < 4:
            continue
        for pattern in patterns:
            m = pattern.search(line)
            if m:
                name = clean_name(m.group(1))
                val_str = m.group(3)  # число из num_pattern (вторая скобка)
                unit = clean_unit(m.group(4)) if m.lastindex >= 4 and m.group(4) else ""
                if len(name) < 2 or name.isdigit():
                    continue
                value = normalize_num(val_str)
                key = (name.lower(), round(value, 4))
                if key in seen:
                    continue
                seen.add(key)
                out.append({"name": name, "value": value, "unit": unit})
                break

    return out


def _build_synonym_map(df):
    """
    Строит словарь синонимов и возвращает пары (key, factor_id), отсортированные по убыванию длины ключа.
    Так при маппинге сначала срабатывает самое длинное совпадение (например «глюкоза натощак» до «глюкоза»).
    """
    syn = {}
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            fid = row.get("factor_id")
            fname = str(row.get("factor_name", "")).strip()
            if not fid:
                continue
            key = re.sub(r"\s+", " ", fname).lower().strip()
            if key and key not in syn:
                syn[key] = fid
            # Вариант без скобок: "Глюкоза (натощак)" -> "глюкоза натощак" и "глюкоза"
            no_brackets = re.sub(r"\s*\([^)]*\)\s*", " ", fname)
            key2 = re.sub(r"\s+", " ", no_brackets).lower().strip()
            if key2 and key2 not in syn:
                syn[key2] = fid
            for part in fname.replace(",", " ").split():
                p = part.strip().lower()
                if len(p) >= 2 and p not in syn:
                    syn[p] = fid
    # Синонимы: названия с бланков (в т.ч. Хеликс) -> factor_id
    manual = {
        "глюкоза": "M001",
        "glucose": "M001",
        "glu": "M001",
        "глюкоза натощак": "M001",
        "глюкоза (сыворотка)": "M001",
        "глюкоза сыворотка": "M001",
        "креатинин": "R001",
        "creatinine": "R001",
        "crea": "R001",
        "ттг": "H001",
        "tsh": "H001",
        "тиреотропный": "H001",
        "т4": "H002",
        "t4": "H002",
        "тироксин": "H002",
        "ат-тпо": "H003",
        "аттпо": "H003",
        "антитела тпо": "H003",
        "холестерин": "C002",
        "холестерин общий": "C002",
        "cholesterol": "C002",
        "лпвп": "C002",
        "лпнп": "C002",
        "лпвп-холестерин": "C002",
        "лпнп-холестерин": "C002",
        "hdl": "C002",
        "ldl": "C002",
        "общий белок": "H008",
        "белок общий": "H008",
        "срб": "F001",
        "с-реактивный белок": "F001",
        "c-реактивный белок": "F001",
        "crp": "F001",
        "с-реактивный": "F001",
        "триглицериды": "H010",
        "триглицериды общие": "H010",
        "алт": "HP001",
        "alt": "HP001",
        "алат": "HP001",
        "аланинаминотрансфераза": "HP001",
        "аст": "HP002",
        "ast": "HP002",
        "асат": "HP002",
        "аспартатаминотрансфераза": "HP002",
        "билирубин общий": "H003",
        "билирубин": "H003",
        "билирубин прямой": "H004",
        "ггт": "HP004",
        "ggt": "HP004",
        "гамма-гт": "HP004",
        "гамма-глутамилтрансфераза": "HP004",
        "щелочная фосфатаза": "H006",
        "щелочная фосфатаза (щф)": "H006",
        "щф": "H006",
        "алп": "H006",
        "альфа-амилаза": "H006",
        "мочевина": "R002",
        "urea": "R002",
        "мочевая кислота": "R004",
        "витамин d": "SK001",
        "витамин d (25-oh)": "SK001",
        "25-oh витамин d": "SK001",
        "ферритин": "SK002",
        "цинк": "SK003",
        "селен": "SK005",
        "пепсиноген i": "GAS001",
        "пепсиноген 1": "GAS001",
        "пепсиноген ii": "GAS002",
        "пепсиноген 2": "GAS002",
        "гастрин": "GAS003",
        "витамин b12": "GAS005",
        "в12": "GAS005",
        "вгд": "OCU001",
        "ретинол": "OCU002",
        "витамин a": "OCU002",
        "гомоцистеин": "OCU003",
        "фибриноген": "F002",
        "соэ": "F005",
        "скорость оседания": "F005",
    }
    for k, v in manual.items():
        if k not in syn:
            syn[k] = v
    # Сортируем по убыванию длины ключа — сначала длинные совпадения
    return sorted(syn.items(), key=lambda x: -len(x[0]))


def map_to_factors(parsed: list[dict], df) -> dict:
    """
    Сопоставляет распознанные показатели (name, value, unit) с factor_id по справочнику df.
    Сначала проверяются длинные совпадения (например «глюкоза натощак»), затем короткие.
    Возвращает словарь { factor_id: value } для успешно сопоставленных в допустимом диапазоне.
    """
    synonym_list = _build_synonym_map(df)
    synonym_dict = dict(synonym_list)
    factor_rows = {}
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            factor_rows[row["factor_id"]] = row

    result = {}
    for item in parsed:
        name = (item.get("name") or "").strip().lower()
        name_norm = re.sub(r"\s+", " ", name)
        value = item.get("value", 0)
        unit = (item.get("unit") or "").strip()

        fid = None
        if name_norm in synonym_dict:
            fid = synonym_dict[name_norm]
        else:
            for key, f in synonym_list:
                if len(key) >= 2 and key in name_norm:
                    fid = f
                    break
        if not fid or fid not in factor_rows:
            continue

        row = factor_rows[fid]
        min_val = float(row.get("min_val", 0))
        max_val = float(row.get("max_val", 1e9))
        if min_val >= max_val:
            max_val = min_val + 1
        value_clamped = max(min_val, min(max_val, value))
        result[fid] = value_clamped

    return result
