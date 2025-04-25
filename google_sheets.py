import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# Leer el JSON desde la variable de entorno GOOGLE_CREDS
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def get_inventory_sheet_for_number(phone_number):
    clientes_sheet = gc.open("Clientes").sheet1  # Asegúrate que se llame exactamente "Clientes"
    rows = clientes_sheet.get_all_records()
    print("📋 Revisando números registrados:")
    for row in rows:
        print(f"📞 Registrado: {row['Número']}")
        if row["Número"] == phone_number:
            print("✅ ¡Número encontrado!")
            sheet_url = row["URL de hoja"]
            cliente_sheet = gc.open_by_url(sheet_url)
            return cliente_sheet.sheet1

    return None  # No arroja error, solo indica que no está registrado

def agregar_producto(hoja, producto):
    hoja.append_row([
        producto["nombre"],
        producto["marca"],
        producto["fecha"],
        producto["costo"],
        producto["cantidad"],
        producto["precio"],
        producto["stock_minimo"],
        producto["ultima_compra"]
    ])

def obtener_productos(hoja):
    data = hoja.get_all_values()[1:]  # Ignora la fila de encabezado
    productos = []
    for row in data:
        if len(row) >= 8:
            producto = {
                "nombre": row[0],
                "marca": row[1],
                "fecha": row[2],
                "costo": row[3],
                "cantidad": row[4],
                "precio": row[5],
                "stock_minimo": row[6],
                "ultima_compra": row[7]
            }
            productos.append(producto)
    return productos
