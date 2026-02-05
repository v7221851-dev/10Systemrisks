# Vercel serverless handler.
# Полноценное Streamlit-приложение на Vercel не запускается (серверные функции с таймаутом).
# Для работы приложения используйте Streamlit Community Cloud — см. DEPLOY.md

from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Health Risk Advisor 10.0</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:2rem auto;padding:1rem;">
  <h1>🛡️ Health Risk Advisor 10.0</h1>
  <p>Этот проект — Streamlit-приложение. На Vercel развёрнут только информационный endpoint.</p>
  <p><strong>Чтобы запустить приложение:</strong></p>
  <ol>
    <li>Откройте <a href="https://share.streamlit.io">Streamlit Community Cloud</a>.</li>
    <li>Подключите репозиторий с этим проектом.</li>
    <li>Укажите главный файл: <code>app.py</code>.</li>
    <li>Добавьте секреты (GigaChat, Google Sheets, при необходимости Vision) в настройках приложения.</li>
  </ol>
  <p>Подробная инструкция — в файле <code>DEPLOY.md</code> в репозитории.</p>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
