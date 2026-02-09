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


def pdf_get_page_count(pdf_bytes: bytes) -> tuple[int | None, str | None]:
    """
    Возвращает количество страниц в PDF.
    Возвращает (page_count, None) при успехе или (None, error_message).
    """
    if not PDF_AVAILABLE:
        return None, "Для распознавания PDF установите пакет: pip install pymupdf"
    if not pdf_bytes:
        return None, "Файл PDF пустой"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        doc.close()
        return page_count, None
    except Exception as e:
        return None, f"Ошибка чтения PDF: {e}"


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


def pdf_to_all_images(pdf_bytes: bytes, dpi: int = 150) -> tuple[list[bytes] | None, str | None]:
    """
    Конвертирует все страницы PDF в список PNG (bytes).
    Возвращает (list_of_png_bytes, None) при успехе или (None, error_message).
    """
    if not PDF_AVAILABLE:
        return None, "Для распознавания PDF установите пакет: pip install pymupdf"
    if not pdf_bytes:
        return None, "Файл PDF пустой"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            images.append(png_bytes)
        doc.close()
        return images, None
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
    # Нормализуем различные тире и дефисы
    line = re.sub(r"[\u2013\u2014\u2015]", "-", line)
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
    # Улучшенный паттерн для чисел: поддерживает запятую и точку как разделитель
    # Число: не считаем частью диапазона (не берём число, за которым сразу идёт "- число")
    num_pattern = r"([<>≤≥]?\s*)(\d+[,.]?\d*)"
    num_standalone = re.compile(r"(?<!\d)(\d+[,.]?\d*)(?=\s*(?:[а-яА-Яa-zA-Z/%]|$))")  # число перед единицей или концом
    num_in_range = re.compile(r"(\d+[,.]?\d*)\s*[\-–—]\s*\d+[,.]?\d*")  # число как начало диапазона "X-Y"
    # Более гибкий паттерн для единиц измерения
    unit_suffix = r"\s*([а-яА-Яa-zA-Z0-9/%²³°·\s\-]+)?$"

    def normalize_num(s: str) -> float:
        s = s.strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    def clean_name(s: str) -> str:
        # Убираем лишние пробелы и нормализуем
        s = re.sub(r"\s+", " ", s).strip()
        # Убираем лишние символы в начале/конце названия
        s = re.sub(r"^[^\wа-яА-Я]+|[^\wа-яА-Я]+$", "", s)
        return s

    def clean_unit(s: str) -> str:
        return s.strip() if s else ""

    def is_valid_lab_name(name: str) -> bool:
        """Проверяет, что название похоже на название лабораторного показателя"""
        if len(name) < 2:
            return False
        if name.isdigit():
            return False
        # Исключаем слишком короткие или неинформативные названия
        if len(name) < 3 and not any(c.isalpha() for c in name):
            return False
        # Исключаем названия, состоящие только из цифр и символов
        if not any(c.isalpha() for c in name):
            return False
        return True

    # Расширенный набор паттернов для различных форматов бланков
    patterns = [
        # Формат: "Название: значение единица" или "Название : значение единица"
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s*[:]\s*" + num_pattern + r"\s*" + unit_suffix, re.UNICODE | re.IGNORECASE),
        # Формат: "Название - значение единица" или "Название — значение единица"
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s+[\-–—]\s*" + num_pattern + r"\s*" + unit_suffix, re.UNICODE | re.IGNORECASE),
        # Формат: "Название значение единица" (без разделителя, но с пробелом)
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s+" + num_pattern + r"\s*" + unit_suffix, re.UNICODE | re.IGNORECASE),
        # Формат: "Название (значение) единица"
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s*\(\s*" + num_pattern + r"\s*\)\s*" + unit_suffix, re.UNICODE | re.IGNORECASE),
        # Формат: "Название значение" (без единицы, но с числом в конце строки)
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s+" + num_pattern + r"(?:\s|$)", re.UNICODE | re.IGNORECASE),
        # Формат таблицы: "Название | значение | единица" или "Название\tзначение\tединица"
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s*[|\t]\s*" + num_pattern + r"\s*[|\t]?\s*" + unit_suffix, re.UNICODE | re.IGNORECASE),
        # Формат: "Название = значение единица"
        re.compile(r"([а-яА-Яa-zA-Z0-9\s\-\(\)/]+?)\s*=\s*" + num_pattern + r"\s*" + unit_suffix, re.UNICODE | re.IGNORECASE),
    ]

    # Строка выглядит как "значение единица" (начинается с числа) — не используем как название
    def line_looks_like_value_unit(s: str) -> bool:
        return bool(re.match(r"^\s*[<>]?\s*\d+[,.]?\d*", s))

    # Строка выглядит как название (не начинается с числа)
    def line_looks_like_name(s: str) -> bool:
        return bool(s) and not re.match(r"^\s*[<>]?\s*\d", s)

    seen = set()
    lines_processed = 0
    matches_found = 0
    raw_lines = [_normalize_ocr_line(l) for l in raw_text.splitlines() if _normalize_ocr_line(l)]

    def pick_result_number(text: str, name_end_pos: int) -> str | None:
        """Из строки после названия выбираем число-результат, а не референс (не из диапазона X-Y)."""
        after_name = text[name_end_pos:].strip()
        # Все отдельные числа после названия
        candidates = num_standalone.findall(after_name)
        range_starts = num_in_range.findall(after_name)
        for c in candidates:
            if c not in range_starts:
                return c
        return candidates[0] if candidates else None

    def try_match(text: str) -> bool:
        nonlocal matches_found
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                name = clean_name(m.group(1))
                val_str = m.group(3)
                unit = clean_unit(m.group(4)) if m.lastindex >= 4 and m.group(4) else ""
                # Если после названия есть несколько чисел (результат и референс), предпочитаем не из диапазона
                name_end = m.end(1)
                alt_num = pick_result_number(text, name_end)
                if alt_num and alt_num != val_str:
                    val_str = alt_num
                if not is_valid_lab_name(name):
                    continue
                value = normalize_num(val_str)
                key = (name.lower(), round(value, 4))
                if key in seen:
                    return True
                seen.add(key)
                out.append({"name": name, "value": value, "unit": unit})
                matches_found += 1
                print(f"OCR parse: '{name}' = {val_str} -> {value} {unit}")
                return True
        return False

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if len(line) < 2:
            i += 1
            continue
        lines_processed += 1
        matched = try_match(line)

        # Объединяем только когда текущая строка — название, следующая — значение с единицей.
        # Так не привязываем значение от одного показателя к названию следующего.
        if not matched and i + 1 < len(raw_lines):
            next_line = raw_lines[i + 1]
            if line_looks_like_name(line) and line_looks_like_value_unit(next_line):
                combined = line + " " + next_line
                if try_match(combined):
                    matched = True
                    i += 1
        if not matched and len(line) > 10:
            print(f"OCR parse (не распознано): '{line[:80]}...'")
        i += 1

    print(f"OCR parse summary: обработано строк {lines_processed}, найдено показателей {matches_found}")
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
        "креатинин (сыворотка)": "R001",
        "креатинин сыворотка": "R001",
        # ТТГ (тиреотропный гормон) -> tsh_level
        "ттг": "tsh_level",
        "tsh": "tsh_level",
        "тиреотропный": "tsh_level",
        "тиреотропный гормон": "tsh_level",
        # Т4 свободный (тироксин свободный) -> t4_free
        "т4": "t4_free",
        "t4": "t4_free",
        "тироксин": "t4_free",
        "т4 свободный": "t4_free",
        "тироксин свободный": "t4_free",
        "free t4": "t4_free",
        "ft4": "t4_free",
        # АСТ (Аспартатаминотрансфераза) -> H002
        "аст": "H002",
        "ast": "H002",
        "асат": "H002",
        "аспартатаминотрансфераза": "H002",
        "аспартатаминотрансфераза (аст)": "H002",
        "аст (аспартатаминотрансфераза)": "H002",
        # АТ-ТПО -> at_tpo
        "ат-тпо": "at_tpo",
        "аттпо": "at_tpo",
        "антитела тпо": "at_tpo",
        "антитела к тиреопероксидазе": "at_tpo",
        "anti-tpo": "at_tpo",
        "atpo": "at_tpo",
        "холестерин": "C002",
        "холестерин общий": "C002",
        "липидограмма (общий холестерин)": "C002",
        "липидограмма": "C002",
        "cholesterol": "C002",
        "общий белок": "H008",
        "белок общий": "H008",
        "белок": "H008",
        "total protein": "H008",
        "protein": "H008",
        "протеин": "H008",
        "общий белок (сыворотка)": "H008",
        "белок общий (сыворотка)": "H008",
        "срб": "F001",
        "срб (с-реактивный белок)": "F001",
        "с-реактивный белок": "F001",
        "с-реактивный белок (crp)": "F001",
        "c-реактивный белок": "F001",
        "с-реативный белок": "F001",
        "crp": "F001",
        "crp высокочувствительный (hs-crp)": "F001",
        "crp высокочувствительный": "F001",
        "hs-crp": "F001",
        "с-реактивный": "F001",
        "триглицериды": "H010",
        "триглицериды общие": "H010",
        # АЛТ (Аланинаминотрансфераза) -> H001
        "алт": "H001",
        "alt": "H001",
        "алат": "H001",
        "аланинаминотрансфераза": "H001",
        "аланинаминотрансфераза (алт)": "H001",
        "алт (аланинаминотрансфераза)": "H001",
        # Билирубин общий -> H003
        "билирубин общий": "H003",
        "билирубин": "H003",
        "total bilirubin": "H003",
        "bilirubin total": "H003",
        "bilirubin": "H003",
        "tbil": "H003",
        "t-bil": "H003",
        "билирубин общий (сыворотка)": "H003",
        "билирубин прямой": "H004",
        "direct bilirubin": "H004",
        "bilirubin direct": "H004",
        "dbil": "H004",
        "d-bil": "H004",
        "прямой билирубин": "H004",
        "билирубин прямой (сыворотка)": "H004",
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
        # Калий
        "калий": "C005",
        "potassium": "C005",
        "k+": "C005",
        "k": "C005",
        "калий (сыворотка)": "C005",
        "калий сыворотка": "C005",
        # Магний
        "магний": "C006",
        "magnesium": "C006",
        "mg+": "C006",
        "mg": "C006",
        "магний (сыворотка)": "C006",
        "магний сыворотка": "C006",
        # Натрий
        "натрий": "C004",
        "sodium": "C004",
        "na+": "C004",
        "na": "C004",
        "натрий (сыворотка)": "C004",
        "натрий сыворотка": "C004",
        # Хлор
        "хлор": "C007",
        "chloride": "C007",
        "cl-": "C007",
        "cl": "C007",
        "хлор (сыворотка)": "C007",
        "хлор сыворотка": "C007",
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
        # Используем исходное значение из OCR, без изменений
        value = item.get("value", 0)
        unit = (item.get("unit") or "").strip()

        fid = None
        # Сначала проверяем точное совпадение
        if name_norm in synonym_dict:
            fid = synonym_dict[name_norm]
        else:
            # Затем проверяем частичные совпадения (от длинных к коротким)
            for key, f in synonym_list:
                if len(key) >= 2 and key in name_norm:
                    fid = f
                    break
        if not fid or fid not in factor_rows:
            # Логирование для отладки: не найден factor_id
            print(f"OCR mapping: '{name_norm}' -> не найден factor_id")
            continue

        row = factor_rows[fid]
        min_val = float(row.get("min_val", 0))
        max_val = float(row.get("max_val", 1e9))
        if min_val >= max_val:
            max_val = min_val + 1
        # Ограничиваем значение диапазоном, но сохраняем исходное значение из OCR
        value_clamped = max(min_val, min(max_val, value))
        # Логирование для отладки: успешный маппинг
        print(f"OCR mapping: '{name_norm}' -> {fid} = {value} (clamped: {value_clamped})")
        # Используем исходное значение, если оно в допустимом диапазоне
        result[fid] = value_clamped

    return result
