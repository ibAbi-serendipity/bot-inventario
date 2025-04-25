import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# Leer el JSON desde la variable de entorno GOOGLE_CREDS
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)

def get_inventory_sheet_for_number(phone_number):
    # Abrimos la hoja que contiene los datos de los clientes
    clientes_sheet = gc.open("Clientes").sheet1  # Asegúrate que se llama así en tu Google Sheets

    # Obtenemos todas las filas
    rows = clientes_sheet.get_all_records()

    # Buscamos la hoja del número
    for row in rows:
        if row["Número"] == phone_number:
            sheet_url = row["URL de hoja"]
            cliente_sheet = gc.open_by_url(sheet_url)
            return cliente_sheet.sheet1  # Asumimos que la primera hoja es la de inventario

    # Si no lo encontramos
    raise ValueError("Este número no está registrado como cliente.")

def agregar_producto(hoja, nombre, marca, fecha, cantidad, precio):
    hoja.append_row([nombre, marca, fecha, cantidad, precio])

def obtener_productos(hoja):
    data = hoja.get_all_values()[1:]  # Ignora la fila de encabezados
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