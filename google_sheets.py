import os
import json
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials

# Configurar logging
logging.basicConfig(level=logging.INFO)

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

creds_json = os.environ.get("GOOGLE_CREDS")

if not creds_json:
    logging.error("❌ No se encontró la variable de entorno GOOGLE_CREDS")

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def get_inventory_sheet_for_number(phone_number):
    logging.info(f"🔍 Buscando número de cliente: {phone_number}")
    
    try:
        clientes_sheet = gc.open("Clientes").sheet1
    except Exception as e:
        logging.error(f"❌ Error al abrir hoja 'Clientes': {e}")
        return None

    try:
        rows = clientes_sheet.get_all_records()
        logging.info(f"📄 {len(rows)} filas leídas de hoja 'Clientes'")
    except Exception as e:
        logging.error(f"❌ Error al leer filas: {e}")
        return None

    for row in rows:
        numero_hoja = str(row.get("Número", "")).strip()
        logging.info(f"🆚 Comparando con: {numero_hoja}")
        if numero_hoja == phone_number.strip():
            logging.info("✅ Número encontrado")
            try:
                url = row.get("URL de hoja")
                cliente_sheet = gc.open_by_url(url)
                return cliente_sheet.sheet1
            except Exception as e:
                logging.error(f"❌ Error al abrir hoja del cliente: {e}")
                return None

    logging.warning("⚠️ Número no encontrado")
    return None

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

    logging.info(f"✅ Producto agregado: {producto['nombre']}")