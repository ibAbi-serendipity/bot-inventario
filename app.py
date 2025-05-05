from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

app = Flask(__name__)

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(creds)

# Diccionario para mantener el estado de cada usuario
user_states = {}
user_data = {}

# === Funciones auxiliares ===
def obtener_hoja_cliente(phone_number):
    try:
        sheet = client.open_by_url(os.getenv("SHEET_URL"))
        return sheet.worksheet(phone_number)
    except:
        return None

def obtener_productos(hoja):
    data = hoja.get_all_records()
    return data

def actualizar_producto_por_codigo(hoja, codigo, columna, nuevo_valor):
    codigos = hoja.col_values(1)  # Asume que la columna A tiene los códigos
    for i, cod in enumerate(codigos):
        if cod.strip().upper() == codigo.strip().upper():
            hoja.update_cell(i + 1, columna, nuevo_valor)
            return True
    return False

def registrar_movimiento_stock(hoja, codigo, cantidad, tipo="ingreso"):
    productos = hoja.get_all_records()
    for i, producto in enumerate(productos):
        if producto.get("codigo", "").strip().upper() == codigo.strip().upper():
            stock_actual = int(producto["cantidad"])
            nueva_cantidad = stock_actual + cantidad if tipo == "ingreso" else stock_actual - cantidad
            hoja.update_cell(i + 2, 6, nueva_cantidad)  # Columna F (cantidad)
            return True
    return False

# === Ruta principal ===
@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").split(":")[-1]
    msg = MessagingResponse().message()

    hoja_cliente = obtener_hoja_cliente(phone_number)
    if hoja_cliente is None:
        msg.body("❌ No estás registrado como cliente. Contacta al administrador.")
        return str(msg)

    estado = user_states.get(phone_number)

    if estado == "esperando_datos_producto":
        datos = incoming_msg.split(",")
        if len(datos) == 7:
            nombre, marca, fecha, costo, cantidad, precio, stock_minimo = [d.strip() for d in datos]
            codigo = f"{nombre[:2]}-{marca[:2]}-{cantidad}"
            hoja_cliente.append_row([codigo, nombre, marca, fecha, costo, cantidad, precio, stock_minimo])
            msg.body(f"✅ Producto agregado con código: {codigo}")
        else:
            msg.body("❌ Formato incorrecto. Intenta de nuevo.")
        user_states.pop(phone_number, None)

    elif estado == "esperando_categoria":
        msg.body("(Lógica de categoría aún no implementada)")

    elif estado == "esperando_empaque":
        msg.body("(Lógica de empaque aún no implementada)")

    elif estado == "ver_productos_opcion":
        if incoming_msg == "1":
            productos = obtener_productos(hoja_cliente)
            if not productos:
                msg.body("📬 No hay productos registrados.\n\nEnvía 'menu' para volver.")
            else:
                respuesta = "📦 Productos en inventario:\n"
                for i, p in enumerate(productos, start=1):
                    respuesta += (
                        f"{i}. {p.get('codigo', '-')}: {p['nombre']} - {p['marca']}, Vence: {p['fecha']}, "
                        f"Stock: {p['cantidad']} - Precio: S/ {p['precio']}\n"
                    )
                respuesta += "\n👉 ¿Deseas ver otra opción?\n1. Ver todos\n2. Filtrar por código\n0. Volver al menú principal"
                msg.body(respuesta)

        elif incoming_msg == "2":
            user_states[phone_number] = "filtrar_por_codigo"
            msg.body("🔎 Ingresa los primeros caracteres del código para filtrar o envía '0' para volver.")

        elif incoming_msg == "0":
            user_states.pop(phone_number, None)
            msg.body(
                "👋 ¡Has vuelto al menú principal!\n"
                "1⃣ Ver productos\n"
                "2⃣ Agregar producto\n"
                "3⃣ Actualizar producto\n"
                "4⃣ Eliminar producto\n"
                "5⃣ Reporte\n"
                "6⃣ Sugerencias de compra\n"
                "7⃣ Revisar stock mínimo / vencimiento"
            )
        else:
            msg.body("❌ Opción inválida. Responde con 1, 2 o 0.")

    elif estado == "filtrar_por_codigo":
        if incoming_msg == "0":
            user_states[phone_number] = "ver_productos_opcion"
            msg.body("👀 ¿Qué deseas hacer?\n1. Ver todos\n2. Filtrar por código\n0. Volver al menú principal")
        else:
            codigo_busqueda = incoming_msg.upper().strip()
            productos = obtener_productos(hoja_cliente)
            filtrados = [p for p in productos if p.get("codigo", "").strip().startswith(codigo_busqueda)]
            if not filtrados:
                msg.body("🔍 No se encontraron productos con ese código.\n\nEnvía otro código o '0' para volver.")
            else:
                respuesta = "📦 Resultados:\n"
                for i, p in enumerate(filtrados, start=1):
                    respuesta += (
                        f"{i}. {p['codigo']}: {p['nombre']} - {p['marca']}, Vence: {p['fecha']}, "
                        f"Stock: {p['cantidad']} - Precio: S/ {p['precio']}\n"
                    )
                respuesta += "\n🔁 Puedes ingresar otro código o enviar '0' para volver."
                msg.body(respuesta)

    elif estado == "opcion_actualizar":
        if incoming_msg == "1":
            user_states[phone_number] = "editar_codigo_producto"
            msg.body("✏️ Ingresa el código del producto que deseas editar:")
        elif incoming_msg == "2":
            user_states[phone_number] = "registrar_ingreso"
            msg.body("📥 Ingresa el código del producto al que deseas registrar ingreso:")
        elif incoming_msg == "3":
            user_states[phone_number] = "registrar_salida"
            msg.body("📤 Ingresa el código del producto al que deseas registrar salida:")
        else:
            msg.body("❌ Opción inválida. Envía 1, 2 o 3.")

    elif estado == "editar_codigo_producto":
        partes = incoming_msg.split(",")
        if len(partes) == 3:
            codigo, campo, nuevo_valor = [p.strip() for p in partes]
            campos_columnas = {
                "nombre": 2, "marca": 3, "fecha": 4,
                "costo": 5, "cantidad": 6, "precio": 7, "stock mínimo": 8
            }
            col = campos_columnas.get(campo.lower())
            if col:
                exito = actualizar_producto_por_codigo(hoja_cliente, codigo, col, nuevo_valor)
                if exito:
                    msg.body("✅ Producto actualizado con éxito.")
                else:
                    msg.body("❌ No se encontró un producto con ese código.")
            else:
                msg.body("❌ Campo no válido. Usa: nombre, marca, fecha, costo, cantidad, precio, stock mínimo")
        else:
            msg.body("❌ Formato incorrecto. Usa: código, campo, nuevo valor")
        user_states.pop(phone_number, None)

    elif estado == "registrar_ingreso":
        partes = incoming_msg.split(",")
        if len(partes) == 2:
            codigo, cantidad = partes[0].strip(), int(partes[1].strip())
            exito = registrar_movimiento_stock(hoja_cliente, codigo, cantidad, tipo="ingreso")
            msg.body("✅ Ingreso registrado correctamente." if exito else "❌ Producto no encontrado.")
        else:
            msg.body("❌ Formato incorrecto. Usa: código, cantidad")
        user_states.pop(phone_number, None)

    elif estado == "registrar_salida":
        partes = incoming_msg.split(",")
        if len(partes) == 2:
            codigo, cantidad = partes[0].strip(), int(partes[1].strip())
            exito = registrar_movimiento_stock(hoja_cliente, codigo, cantidad, tipo="salida")
            msg.body("✅ Salida registrada correctamente." if exito else "❌ Producto no encontrado.")
        else:
            msg.body("❌ Formato incorrecto. Usa: código, cantidad")
        user_states.pop(phone_number, None)

    elif incoming_msg.lower() in ["hola", "menu", "inicio"]:
        menu = (
            "👋 ¡Bienvenido al bot de inventario!\n"
            "Elige una opción:\n"
            "1⃣ Ver productos\n"
            "2⃣ Agregar producto\n"
            "3⃣ Actualizar producto\n"
            "4⃣ Eliminar producto\n"
            "5⃣ Reporte\n"
            "6⃣ Sugerencias de compra\n"
            "7⃣ Revisar stock mínimo / vencimiento"
        )
        msg.body(menu)

    elif incoming_msg == "1":
        user_states[phone_number] = "ver_productos_opcion"
        msg.body("👀 ¿Qué deseas hacer?\n1. Ver todos\n2. Filtrar por código\n0. Volver al menú principal")

    elif incoming_msg == "2":
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Por favor envía los datos del producto en este formato:\n"
                 "`Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo`")

    elif incoming_msg == "3":
        user_states[phone_number] = "opcion_actualizar"
        msg.body("🔧 ¿Qué deseas hacer?\n1. Editar producto\n2. Registrar ingreso\n3. Registrar salida")

    else:
        msg.body("Envía 'menu' para ver las opciones disponibles.")

    return str(msg)

if __name__ == "__main__":
    app.run(debug=True)
