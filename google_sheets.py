import os
import json
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials

# Configurar logging
logging.basicConfig(level=logging.INFO)

# === AUTENTICACIÓN CON GOOGLE SHEETS ===
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_json = os.environ.get("GOOGLE_CREDS")

if not creds_json:
    logging.error("❌ No se encontró la variable de entorno GOOGLE_CREDS")
    raise ValueError("Faltan credenciales de Google")

try:
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)
    logging.info("✅ Autenticación con Google completada")
except Exception as e:
    logging.error(f"❌ Error al autorizar con Google Sheets: {e}")
    raise

# === OBTENER HOJA DE INVENTARIO POR NÚMERO ===
def get_inventory_sheet_for_number(phone_number):
    logging.info(f"🔍 Buscando número de cliente: {phone_number}")
    try:
        clientes_sheet = gc.open("Clientes").sheet1
        rows = clientes_sheet.get_all_records()
        for row in rows:
            numero_hoja = str(row.get("Número", "")).strip()
            if numero_hoja == phone_number.strip():
                logging.info("✅ Número encontrado en hoja 'Clientes'")
                url = row.get("URL de hoja")
                cliente_sheet = gc.open_by_url(url)
                return cliente_sheet.sheet1
        logging.warning("⚠️ Número no encontrado")
    except Exception as e:
        logging.error(f"❌ Error al buscar hoja del cliente: {e}")
    return None

# === AGREGAR PRODUCTO ===
def agregar_producto(sheet, producto):
    try:
        fila = [
            producto["codigo"],
            producto["nombre"],
            producto["marca"],
            producto["fecha"],
            producto["costo"],
            producto["cantidad"],
            producto["precio"],
            producto["stock_minimo"],
            producto.get("ultima_compra", "")
        ]
        sheet.append_row(fila, value_input_option="USER_ENTERED")
        logging.info(f"✅ Producto '{producto['nombre']}' agregado")
    except Exception as e:
        logging.error(f"❌ Error al agregar producto: {e}")
        raise

# === OBTENER TODOS LOS PRODUCTOS ===
def obtener_productos(sheet):
    try:
        records = sheet.get_all_records()
        logging.info(f"📄 Se obtuvieron {len(records)} productos")
        return records
    except Exception as e:
        logging.error(f"❌ Error al obtener productos: {e}")
        return []
