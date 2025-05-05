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
        producto["codigo"],
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

def obtener_productos(hoja):
    data = hoja.get_all_values()[1:]  # Ignora la fila de encabezado
    productos = []
    for row in data:
        if len(row) >= 9:
            producto = {
                "codigo": row[0].strip(),
                "nombre": row[1],
                "marca": row[2],
                "fecha": row[3],
                "costo": row[4],
                "cantidad": row[5],
                "precio": row[6],
                "stock_minimo": row[7],
                "ultima_compra": row[8]
            }
            productos.append(producto)
    return productos

def actualizar_producto_por_codigo(hoja, codigo, nuevos_datos):
    datos = hoja.get_all_records()
    for idx, producto in enumerate(datos, start=2):  # +2 para saltar encabezado (1) y empezar desde fila 2
        if str(producto.get("codigo", "")).strip().upper() == codigo.upper():
            for key, valor in nuevos_datos.items():
                if key in producto:
                    col_idx = list(producto.keys()).index(key) + 1
                    hoja.update_cell(idx, col_idx, valor)
            return True
    return False
