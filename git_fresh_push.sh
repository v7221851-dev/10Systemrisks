#!/bin/bash
# Заново завести git и запушить проект (без .md, без конфликтов)
# Запускать из корня проекта: cd /Users/vladimir_a/Desktop/10SystemRisks && ./git_fresh_push.sh

set -e
cd "$(dirname "$0")"

echo "=== 1. Удаляю старый .git (если есть) ==="
rm -rf .git

echo ""
echo "=== 2. Инициализация репозитория ==="
git init
git branch -M main

echo ""
echo "=== 3. Настройка автора (только для этого репо) ==="
git config user.email "v7221851@gmail.com"
git config user.name "Vladimir Afanasev"

echo ""
echo "=== 4. Подключение remote ==="
# Замените URL на свой, если репозиторий называется иначе (регистр важен: 10SystemRisks ≠ 10Systemrisks)
GITHUB_REPO_URL="https://github.com/v7221851-dev/10SystemRisks.git"
git remote add origin "$GITHUB_REPO_URL"
echo "   URL: $GITHUB_REPO_URL"

echo ""
echo "=== 5. Добавление файлов (без .md, .venv, secrets — по .gitignore) ==="
git add -A
# Явно снять с индекса все .md, чтобы они точно не попали в коммит
staged_md=$(git diff --cached --name-only 2>/dev/null | grep '\.md$' || true)
if [ -n "$staged_md" ]; then
  echo "Снимаю с индекса .md файлы:"
  echo "$staged_md" | xargs git reset HEAD --
fi
echo "Состав коммита:"
git status --short

echo ""
echo "=== 6. Коммит ==="
git commit -m "Health Risk Advisor 10.0: проект без .md документации"

echo ""
echo "=== 7. Пуш (перезапись ветки main на GitHub) ==="
if ! git push -u origin main --force; then
  echo ""
  echo "❌ Ошибка push. Частые причины:"
  echo "   • Репозиторий не создан на GitHub. Создайте пустой репо: https://github.com/new"
  echo "   • Неверный URL. Откройте git_fresh_push.sh и исправьте GITHUB_REPO_URL в начале шага 4"
  echo "   • Имя репо с большой R: 10SystemRisks → https://github.com/v7221851-dev/10SystemRisks.git"
  exit 1
fi

echo ""
echo "Готово. Репозиторий: $GITHUB_REPO_URL"
