#!/bin/bash
# Деплой правок: коммит и пуш в origin (Streamlit Cloud / Vercel подхватят из GitHub)
set -e
cd "$(dirname "$0")"

echo "Добавляем изменённые файлы..."
git add app.py RESULT_SUMMARY.md 2>/dev/null || true

if git diff --cached --quiet; then
  echo "Нет изменений для коммита."
  exit 0
fi

echo "Коммит..."
git commit -m "Ocular: расчёт при 1 факторе; AI рекомендации GigaChat по умолчанию"

echo "Пуш в origin/main..."
git push origin main

echo "Готово. Деплой на Streamlit Cloud / Vercel обновится автоматически."
