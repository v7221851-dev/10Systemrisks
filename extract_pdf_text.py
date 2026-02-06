#!/usr/bin/env python3
"""Извлекает текст из PDF бланка в текстовый файл."""
import sys
try:
    import fitz
except ImportError:
    print("pip install pymupdf")
    sys.exit(1)

path = "Анализы крови_1770106181003.pdf"
out_path = "Анализы_крови_текст.txt"
doc = fitz.open(path)
lines = []
for i in range(len(doc)):
    page = doc.load_page(i)
    text = page.get_text()
    lines.append(f"--- Страница {i+1} ---\n{text}")
doc.close()
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n\n".join(lines))
print(f"Текст записан в {out_path}")
