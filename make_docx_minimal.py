# -*- coding: utf-8 -*-
"""Создание .docx с описанием алгоритма (только стандартная библиотека)."""
import zipfile
import xml.sax.saxutils as sax

def escape(s):
    return sax.escape(str(s)) if s else ""

def w_p(text, bold=False):
    b = " <w:b/>" if bold else ""
    return f'<w:p><w:r><w:rPr>{b}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def w_heading(text, level=1):
    return f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def w_title(text):
    return f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

body = []
body.append(w_title("Как работает алгоритм: средневзвешенные формулы"))
body.append(w_p("В расчёте три уровня: балл по фактору (1–5), балл по группе рисков (средневзвешенный), итоговый индекс (тоже средневзвешенный по группам)."))
body.append(w_heading("1. Балл по одному фактору (1–5)", 1))
body.append(w_p("Каждый показатель сначала переводится в балл по шкале 1–5 (5 = норма, 1 = плохо)."))
body.append(w_p("• Числовой показатель (range): используется функция calculate_risk — значение в пределах нормы [norm_min, norm_max] даёт 5.0; за пределами нормы балл линейно снижается до 1.0."))
body.append(w_p("• Категориальный (select): выбор пользователя маппится в балл 1–5 (например, «Норма» → 5, «Высокий риск» → 1)."))
body.append(w_p("Пример (числовой): артериальное давление 120/80, норма 110–130 → значение в норме → балл 5.0. Давление 150 → за нормой → балл, например, 2.2."))
body.append(w_p("В расчётах дальше везде используются уже эти баллы 1–5."))
body.append(w_heading("2. Балл группы рисков — средневзвешенный по факторам", 1))
body.append(w_p("По каждой группе (Neuro, Cardio, Hormone и т.д.) считается один балл — средневзвешенное баллов факторов с учётом весов из базы (Weight_Coefficient). В каждой группе веса факторов в сумме дают 1.0."))
body.append(w_p("Формула в коде (по сути классическая средневзвешенная):"))
body.append(w_p("raw_score = Σ (балл_фактора × вес_фактора)"))
body.append(w_p("total_w   = Σ вес_фактора   (только по факторам, для которых есть ответ)"))
body.append(w_p("group_score = raw_score / total_w"))
body.append(w_p("То есть: group_score = (Σ (балл_i × w_i)) / (Σ w_i)"))
body.append(w_p("Пример для группы Cardio (упрощённо, 4 фактора, веса в сумме 1.0):", True))
body.append(w_p("Фактор: Давление — Вес (w_i): 0.35 — Балл пользователя: 5.0"))
body.append(w_p("Фактор: Холестерин — Вес: 0.30 — Балл: 3.0"))
body.append(w_p("Фактор: ЧСС покоя — Вес: 0.20 — Балл: 4.0"))
body.append(w_p("Фактор: С-реактивный белок — Вес: 0.15 — Балл: 5.0"))
body.append(w_p("raw_score = 5×0.35 + 3×0.30 + 4×0.20 + 5×0.15 = 1.75 + 0.90 + 0.80 + 0.75 = 4.20"))
body.append(w_p("total_w = 0.35 + 0.30 + 0.20 + 0.15 = 1.00"))
body.append(w_p("group_score(Cardio) = 4.20 / 1.00 = 4.20", True))
body.append(w_heading("3. Итоговый индекс — средневзвешенное по группам (с учётом «худшей»)", 1))
body.append(w_p("Итоговый балл считается не как простое среднее по группам, а как взвешенная комбинация среднего и минимума по группам (чтобы сильнее учитывать самую слабую систему)."))
body.append(w_p("В коде:"))
body.append(w_p("• Если групп с данными меньше порога (например, 5): final_score = 0.7 × avg_score + 0.3 × min_score"))
body.append(w_p("• Если групп достаточно: final_score = 0.6 × avg_score + 0.4 × min_score"))
body.append(w_p("avg_score — среднее арифметическое баллов по всем учтённым группам; min_score — минимальный балл среди этих групп (самая проблемная система)."))
body.append(w_p("Пример. Допустим по группам: Neuro 4.5, Cardio 4.2, Hormone 3.8, Metabolic 4.0, Immune 4.1 (достаточно групп)."))
body.append(w_p("avg_score = (4.5 + 4.2 + 3.8 + 4.0 + 4.1) / 5 = 4.12"))
body.append(w_p("min_score = 3.8 (Hormone)"))
body.append(w_p("final_score = 0.6 × 4.12 + 0.4 × 3.8 = 2.472 + 1.52 = 3.99 (округлённо 4.0)"))
body.append(w_p("Итоговый балл тоже в шкале 1–5."))
body.append(w_heading("4. Перевод в проценты для интерфейса", 1))
body.append(w_p("Итоговый балл 1–5 переводится в проценты линейно: percent = final_score × 20 (1 → 20%, 5 → 100%). В коде это делает score_to_percent."))
body.append(w_p("Пример: final_score = 3.99 → percent = 3.99 × 20 ≈ 80% (зелёная зона)."))
body.append(w_heading("Кратко по формулам", 1))
body.append(w_p("Уровень «Фактор»: балл 1–5 из значения/выбора — calculate_risk или маппинг опций."))
body.append(w_p("Уровень «Группа рисков»: балл группы (1–5) — (Σ балл_i × w_i) / Σ w_i"))
body.append(w_p("Уровень «Итог»: итоговый балл (1–5) — 0.6×avg(group_scores) + 0.4×min(group_scores) (при достаточном числе групп)."))
body.append(w_p("Интерфейс: процент — final_score × 20"))
body.append(w_p("Итого: средневзвешенная используется явно на уровне группы рисков (по факторам), а на уровне итога — взвешенная комбинация среднего и минимума по группам."))

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

RELS_ROOT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

RELS_DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
""" + "\n".join(body) + """
<w:p><w:r></w:r></w:p>
</w:body>
</w:document>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:lang w:val="ru-RU"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:styleId="Title" w:default="1"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
</w:styles>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"><dc:title>Алгоритм оценки рисков</dc:title></cp:coreProperties>"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Health Risk Advisor</Application></Properties>"""

out_path = "Алгоритм_средневзвешенная_формула.docx"
with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CONTENT_TYPES)
    z.writestr("_rels/.rels", RELS_ROOT)
    z.writestr("word/_rels/document.xml.rels", RELS_DOC)
    z.writestr("word/document.xml", DOCUMENT_XML)
    z.writestr("word/styles.xml", STYLES)
    z.writestr("docProps/core.xml", CORE)
    z.writestr("docProps/app.xml", APP)

print("Сохранено:", out_path)
