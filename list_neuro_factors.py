#!/usr/bin/env python3
"""Выводит все факторы группы Neuro из knowledge_db."""
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1kvlW3ko5yvhE6yInw-xER-NEKXT2UNze7BIR-I-yOfQ"
CREDENTIALS_FILE = "credentials.json"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet("knowledge_db")
all_values = sheet.get_all_values()
headers = all_values[0]
data = all_values[1:]
rg_idx = headers.index("Risk_Group")
fn_idx = headers.index("factor_name")
fid_idx = headers.index("factor_id")
print("Факторы в группе Neuro:")
for i, row in enumerate(data):
    if len(row) <= rg_idx: continue
    if row[rg_idx].strip() != "Neuro": continue
    fid = row[fid_idx].strip() if fid_idx < len(row) else ""
    fn = row[fn_idx].strip() if fn_idx < len(row) else ""
    print(f"  {fid}: {fn}")
