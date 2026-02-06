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
        # Структура ответа: results[].results[] с textAnnotation или blocks
        results = data.get("results", [])
        if not results:
            return None, "В ответе нет результатов"
        first = results[0]
        inner = first.get("results", [])
        if not inner:
            return "", None  # пустая страница
        ann = inner[0]
        text = ann.get("textAnnotation", {}).get("text")
        if text is not None:
            return text.strip() or "", None
        # Альтернатива: blocks -> lines -> text
        blocks = ann.get("blocks", [])
        lines = []
        for block in blocks:
            for line in block.get("lines", []):
                t = line.get("text", "").strip()
                if t:
                    lines.append(t)
        return "\n".join(lines), None
    except Exception as e:
        return None, f"Ошибка разбора ответа: {e}"


def parse_lab_text(raw_text: str) -> list[dict]:
    """
    Извлекает из сырого текста OCR пары «название показателя — значение — единица».
    Поддерживает форматы: "Глюкоза 5.4 ммоль/л", "Креатинин: 90", "ТТГ 2.5 мМЕ/л".
    Возвращает список словарей: [ {"name": str, "value": float, "unit": str}, ... ]
    """
    if not raw_text or not raw_text.strip():
        return []

    out = []
    # Число: целое или с точкой/запятой (для лабораторных значений)
    num_pattern = r"(\d+[,.]?\d*)"
    # Единицы измерения (типичные окончания)
    unit_suffix = r"\s*([а-яА-Яa-zA-Z/%²³°·\s\-]+)?$"
    # Строка вида: название (буквы, пробелы, дефис, скобки) затем число и опционально единица
    # Вариант 1: "Название 5.4 ммоль/л" или "Название: 5.4"
    line_pattern = re.compile(
        r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s*[:]\s*" + num_pattern + r"\s*" + unit_suffix,
        re.UNICODE,
    )
    # Вариант 2: "Название 5.4 ммоль/л" без двоеточия (число после пробелов)
    line_pattern2 = re.compile(
        r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s+" + num_pattern + r"\s*" + unit_suffix,
        re.UNICODE,
    )

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

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = line_pattern.search(line) or line_pattern2.search(line)
        if m:
            name = clean_name(m.group(1))
            val_str = m.group(2)
            unit = clean_unit(m.group(3)) if m.lastindex >= 3 and m.group(3) else ""
            # Отсекаем слишком короткие «названия» (могут быть артефакты)
            if len(name) >= 2:
                out.append({"name": name, "value": normalize_num(val_str), "unit": unit})

    return out


def _build_synonym_map(df) -> dict:
    """Строит словарь: нормализованное название/синоним -> factor_id."""
    import pandas as pd

    syn = {}
    if df is None or df.empty:
        return syn
    for _, row in df.iterrows():
        fid = row.get("factor_id")
        fname = str(row.get("factor_name", "")).strip()
        uname = str(row.get("unit_name", "")).strip()
        if not fid:
            continue
        # Ключ: название в нижнем регистре без лишних пробелов
        key = re.sub(r"\s+", " ", fname).lower().strip()
        if key:
            syn[key] = fid
        # Короткие варианты (первые слова)
        for part in fname.replace(",", " ").split():
            p = part.strip().lower()
            if len(p) >= 2 and p not in syn:
                syn[p] = fid
    # Ручные синонимы для частых названий в бланках
    manual = {
        "глюкоза": "M001",
        "glucose": "M001",
        "glu": "M001",
        "креатинин": "R001",
        "creatinine": "R001",
        "crea": "R001",
        "ттг": "H001",
        "tsh": "H001",
        "t4": "H002",
        "т4": "H002",
        "ат-тпо": "H003",
        "аттпо": "H003",
        "холестерин": "C002",
        "cholesterol": "C002",
        "алт": "HP001",
        "alt": "HP001",
        "аст": "HP002",
        "ast": "HP002",
        "ггт": "HP004",
        "ggt": "HP004",
        "мочевина": "R002",
        "urea": "R002",
        "мочевая кислота": "R004",
        "витамин d": "SK001",
        "витамин d (25-oh)": "SK001",
        "ферритин": "SK002",
        "ферритин,": "SK002",
        "цинк": "SK003",
        "селен": "SK005",
        "пепсиноген i": "GAS001",
        "пепсиноген ii": "GAS002",
        "гастрин": "GAS003",
        "витамин b12": "GAS005",
        "вгд": "OCU001",
        "ретинол": "OCU002",
        "витамин a": "OCU002",
        "гомоцистеин": "OCU003",
        "crp": "F001",
        "с-реактивный": "F001",
        "фибриноген": "F002",
        "соэ": "F005",
    }
    for k, v in manual.items():
        if k not in syn:
            syn[k] = v
    return syn


def map_to_factors(parsed: list[dict], df) -> dict:
    """
    Сопоставляет распознанные показатели (name, value, unit) с factor_id по справочнику df.
    Возвращает словарь { factor_id: value } только для успешно сопоставленных и в допустимом диапазоне.
    """
    import pandas as pd

    synonym_map = _build_synonym_map(df)
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
        # Точное совпадение
        if name_norm in synonym_map:
            fid = synonym_map[name_norm]
        else:
            # Поиск по вхождению ключа в название
            for key, f in synonym_map.items():
                if len(key) >= 3 and key in name_norm:
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
