import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "credentials.json"  # Asegúrate que el nombre sea igual al tuyo

# Conexión con Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
client = gspread.authorize(creds)

# Hoja que contiene la lista de clientes registrados
CLIENTS_SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA_DE_CLIENTES/edit"

def get_inventory_sheet_for_number(phone_number: str):
    # Abre la hoja de clientes
    sheet = client.open_by_url(CLIENTS_SHEET_URL)
    worksheet = sheet.sheet1  # Primera pestaña

    records = worksheet.get_all_records()
    for row in records:
        if row["Número WhatsApp"].strip() == phone_number.strip():
            inventory_url = row["URL de su Google Sheet"]
            return client.open_by_url(inventory_url)

    return None  # Si no se encuentra el número
