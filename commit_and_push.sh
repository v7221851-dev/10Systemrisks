#!/bin/bash
# Закоммитить и запушить последние правки (Tesseract удалён, Yandex Vision исправлен)
set -e
cd "$(dirname "$0")"
git add app.py ocr_vision.py
git status
git commit -m "Remove Tesseract; fix Yandex Vision API (no folder_id when using API key)"
git push origin main
echo "Done."
