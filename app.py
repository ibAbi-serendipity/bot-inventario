# main.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import (
    get_inventory_sheet_for_number, agregar_producto, obtener_productos,
    actualizar_producto_por_codigo, registrar_ingreso_producto,
    registrar_salida_producto, eliminar_producto_por_codigo
)

app = Flask(__name__)
user_states = {}
temp_data = {}

CATEGORIAS = {
    "perecible": "1",
    "no perecible": "2",
    "limpieza": "3"
}

EMPAQUES = {
    "unidad": "U",
    "caja": "C",
    "bolsa": "B",
    "paquete": "P",
    "saco": "S",
    "botella": "B",
    "lata": "L",
    "tetrapack": "T",
    "sobre": "S"
}

print(f"📥 Mensaje recibido: {incoming_msg}")
print(f"📱 Estado actual del número {phone_number}: {user_states.get(phone_number)}")
@app.route("/webhook", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").replace("whatsapp:", "").replace("+", "")
    hoja_cliente = get_inventory_sheet_for_number(phone_number)
    resp = MessagingResponse()
    msg = resp.message()

    if not hoja_cliente:
        msg.body("❌ Tu número no está registrado. Por favor contacta con el administrador.")
        return str(resp)

    estado = user_states.get(phone_number)

    if incoming_msg.lower() in ["hola", "menu", "inicio"]:
        user_states[phone_number] = None
        msg.body(
            "👋 ¡Bienvenido al bot de inventario!\n"
            "Elige una opción:\n"
            "1⃣ Ver productos\n"
            "2⃣ Filtrar por código\n"
            "3⃣ Agregar producto\n"
            "4⃣ Actualizar producto\n"
            "5⃣ Eliminar producto\n"
            "6⃣ Registrar entrada\n"
            "7⃣ Registrar salida\n"
            "8⃣ Reporte\n"
            "9⃣ Sugerencias de compra\n"
            "0⃣ Revisar stock mínimo / vencimiento"
        )
        return str(resp)

    if incoming_msg == "1":
        productos = obtener_productos(hoja_cliente)
        if not productos:
            msg.body("📬 No hay productos registrados.")
        else:
            respuesta = "📦 Productos en inventario:\n"
            for i, p in enumerate(productos, start=1):
                respuesta += (
                    f"{i}. {p.get('codigo', '-')}: {p['nombre']} - {p['marca']}, Vence: {p['fecha']}, "
                    f"Stock: {p['cantidad']} - Precio: S/ {p['precio']}\n"
                )
            msg.body(respuesta)
        return str(resp)

    elif incoming_msg == "2":
        user_states[phone_number] = "filtrar_por_codigo"
        msg.body("🔎 Ingresa los primeros caracteres del código para filtrar:")
        return str(resp)

    elif estado == "filtrar_por_codigo":
        productos = obtener_productos(hoja_cliente)
        filtrados = [p for p in productos if p.get("codigo", "").startswith(incoming_msg.upper())]
        if not filtrados:
            msg.body("❌ No se encontraron productos.")
        else:
            respuesta = "📦 Resultados:\n"
            for i, p in enumerate(filtrados, start=1):
                respuesta += (
                    f"{i}. {p['codigo']}: {p['nombre']} - {p['marca']}, Vence: {p['fecha']}, "
                    f"Stock: {p['cantidad']} - Precio: S/ {p['precio']}\n"
                )
            msg.body(respuesta)
        user_states.pop(phone_number, None)
        return str(resp)

    elif incoming_msg == "3":
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Envía: Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo")
        return str(resp)

    elif estado == "esperando_datos_producto":
        partes = [x.strip() for x in incoming_msg.split(",")]
        if len(partes) != 7:
            msg.body("⚠️ Formato incorrecto.")
            return str(resp)
        temp_data[phone_number] = {
            "nombre": partes[0],
            "marca": partes[1],
            "fecha": partes[2],
            "costo": partes[3],
            "cantidad": partes[4],
            "precio": partes[5],
            "stock_minimo": partes[6],
            "ultima_compra": ""
        }
        user_states[phone_number] = "esperando_categoria"
        msg.body("📦 Categoría del producto? (perecible / no perecible / limpieza)")
        return str(resp)

    elif estado == "esperando_categoria":
        cat = incoming_msg.lower()
        if cat not in CATEGORIAS:
            msg.body("❌ Categoría inválida.")
            return str(resp)
        temp_data[phone_number]["_categoria"] = CATEGORIAS[cat]
        user_states[phone_number] = "esperando_empaque"
        msg.body("📦 Tipo de empaque? (unidad / caja / bolsa / etc.)")
        return str(resp)

    elif estado == "esperando_empaque":
        emp = incoming_msg.lower()
        if emp not in EMPAQUES:
            msg.body("❌ Empaque inválido.")
            return str(resp)
        datos = temp_data.pop(phone_number)
        productos = obtener_productos(hoja_cliente)
        secuencial = str(len(productos) + 1).zfill(2)
        codigo = f"{datos.pop('_categoria')}{datos['marca'][0].upper()}{EMPAQUES[emp]}{secuencial}"
        datos["codigo"] = codigo
        agregar_producto(hoja_cliente, datos)
        user_states.pop(phone_number, None)
        msg.body(f"✅ Producto agregado con código {codigo}.")
        return str(resp)

    elif incoming_msg == "4":
        user_states[phone_number] = "actualizar_codigo"
        msg.body("✏️ Ingresa el código del producto a actualizar:")
        return str(resp)

    elif estado == "actualizar_codigo":
        temp_data[phone_number] = {"codigo": incoming_msg.upper()}
        user_states[phone_number] = "esperando_nuevos_datos"
        msg.body("📝 Ingresa nuevos datos: Nombre, Marca, Fecha, Costo, Cantidad, Precio, Stock Mínimo")
        return str(resp)

    elif estado == "esperando_nuevos_datos":
        partes = [x.strip() for x in incoming_msg.split(",")]
        if len(partes) != 7:
            msg.body("⚠️ Formato incorrecto.")
            return str(resp)
        datos = temp_data.pop(phone_number)
        nuevos = {
            "nombre": partes[0], "marca": partes[1], "fecha": partes[2],
            "costo": partes[3], "cantidad": partes[4], "precio": partes[5],
            "stock_minimo": partes[6]
        }
        exito = actualizar_producto_por_codigo(hoja_cliente, datos["codigo"], nuevos)
        user_states.pop(phone_number, None)
        msg.body("✅ Producto actualizado." if exito else "❌ Producto no encontrado.")
        return str(resp)

    elif incoming_msg == "5":
        user_states[phone_number] = "eliminar_codigo"
        msg.body("🗑️ Ingresa el código del producto a eliminar:")
        return str(resp)

    elif estado == "eliminar_codigo":
        exito = eliminar_producto_por_codigo(hoja_cliente, incoming_msg.upper())
        user_states.pop(phone_number, None)
        msg.body("✅ Producto eliminado." if exito else "❌ Producto no encontrado.")
        return str(resp)

    elif incoming_msg == "6":
        user_states[phone_number] = "ingreso_codigo"
        msg.body("📥 Código del producto para registrar ingreso:")
        return str(resp)

    elif estado == "ingreso_codigo":
        temp_data[phone_number] = {"codigo": incoming_msg.upper()}
        user_states[phone_number] = "ingreso_cantidad"
        msg.body("🔢 Ingresa la cantidad a añadir:")
        return str(resp)

    elif estado == "ingreso_cantidad":
        datos = temp_data.pop(phone_number)
        exito = registrar_ingreso_producto(hoja_cliente, datos["codigo"], incoming_msg)
        user_states.pop(phone_number, None)
        msg.body("✅ Ingreso registrado." if exito else "❌ Producto no encontrado.")
        return str(resp)

    elif incoming_msg == "7":
        user_states[phone_number] = "salida_codigo"
        msg.body("📤 Código del producto para registrar salida:")
        return str(resp)

    elif estado == "salida_codigo":
        temp_data[phone_number] = {"codigo": incoming_msg.upper()}
        user_states[phone_number] = "salida_cantidad"
        msg.body("🔢 Ingresa la cantidad a reducir:")
        return str(resp)

    elif estado == "salida_cantidad":
        datos = temp_data.pop(phone_number)
        exito = registrar_salida_producto(hoja_cliente, datos["codigo"], incoming_msg)
        user_states.pop(phone_number, None)
        msg.body("✅ Salida registrada." if exito else "❌ Producto no encontrado o stock insuficiente.")
        return str(resp)

    else:
        msg.body("❓ No entendí. Envía 'menu' para ver opciones.")
        return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
