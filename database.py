import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

class DatabaseManager:
    def __init__(self, credentials_json, sheet_name):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_json, self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet_name = sheet_name
        self.spreadsheet = self.client.open(sheet_name)

    def get_knowledge_base(self):
        """Загружает базу знаний и проверяет веса."""
        worksheet = self.spreadsheet.worksheet("Knowledge_db")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Проверка: есть ли нужные колонки
        required_columns = ['factor_id', 'weight']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"В таблице отсутствуют обязательные колонки: {required_columns}")

        # Валидация весов
        total_weight = df['weight'].sum()
        if total_weight > 1.001:  # Небольшой допуск на погрешность float
            print(f"⚠️ Внимание: Сумма весов ({total_weight}) превышает 1.0! Проверьте Knowledge_db.")
        
        return df

    def log_user_session(self, session_data):
        """
        Записывает результат сессии во вкладку User_sessions.
        session_data: список значений [Timestamp, User_ID, Input_Data, Score, Status, Recommendations]
        """
        try:
            worksheet = self.spreadsheet.worksheet("User_sessions")
            worksheet.append_row(session_data)
            return True
        except Exception as e:
            print(f"❌ Ошибка при записи сессии: {e}")
            return False