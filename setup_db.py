import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Конфигурация доступа
SERVICE_ACCOUNT_EMAIL = "systemrisks10@indigo-gecko-481914-g0.iam.gserviceaccount.com"
# ID вашей таблицы (вы присылали его ранее в Unique ID)
SPREADSHEET_ID = "107932296812603389533" 

def setup_google_connection():
    """Устанавливает соединение с Google Sheets через сервисный аккаунт."""
    
    # Определяем область доступа (Scope)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Файл credentials.json — это скачанный ключ вашего сервисного аккаунта
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        
        # Открываем таблицу
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet("knowledge_db")
        
        print(f"✅ Успешное подключение!")
        print(f"Аккаунт: {SERVICE_ACCOUNT_EMAIL}")
        print(f"Таблица: {spreadsheet.title}")
        
        # Пробное чтение заголовков
        headers = sheet.row_values(1)
        print(f"Колонки в базе: {headers}")
        
        return sheet

    except FileNotFoundError:
        print("❌ Ошибка: Файл 'credentials.json' не найден в папке с проектом.")
    except gspread.exceptions.PermissionDenied:
        print(f"❌ Ошибка: У аккаунта {SERVICE_ACCOUNT_EMAIL} нет прав на эту таблицу.")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")

if __name__ == "__main__":
    setup_google_connection()