from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import (
    get_inventory_sheet_for_number,
    agregar_producto,
    obtener_productos,
    actualizar_producto_por_codigo
)

app = Flask(__name__)
user_states = {}
temp_data = {}

# Diccionarios para el código de producto
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

@app.route("/webhook", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").replace("whatsapp:", "").replace("+", "")
    print(f"📱 Número recibido: {phone_number}")

    hoja_cliente = get_inventory_sheet_for_number(phone_number)
    resp = MessagingResponse()
    msg = resp.message()

    if not hoja_cliente:
        msg.body("❌ Tu número no está registrado. Por favor contacta con el administrador.")
        return str(resp)

    estado = user_states.get(phone_number)

    if incoming_msg.lower() in ["hola", "menu", "inicio"]:
        user_states.pop(phone_number, None)
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

    elif incoming_msg == "2":
        user_states[phone_number] = "filtrar_por_codigo"
        msg.body("🔎 Ingresa los primeros caracteres del código para filtrar:")

    elif estado == "filtrar_por_codigo":
        codigo = incoming_msg.upper()
        productos = obtener_productos(hoja_cliente)
        filtrados = [p for p in productos if p.get("codigo", "").startswith(codigo)]
        if not filtrados:
            msg.body("❌ No se encontraron productos con ese código. Intenta nuevamente o escribe 'menu'.")
        else:
            respuesta = "📦 Resultados:\n"
            for i, p in enumerate(filtrados, start=1):
                respuesta += (
                    f"{i}. {p['codigo']}: {p['nombre']} - {p['marca']}, Vence: {p['fecha']}, "
                    f"Stock: {p['cantidad']} - Precio: S/ {p['precio']}\n"
                )
            msg.body(respuesta)

    elif incoming_msg == "3":
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Envía los datos en este formato:\n"
                 "Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo")

    elif estado == "esperando_datos_producto":
        partes = [x.strip() for x in incoming_msg.split(",")]
        if len(partes) != 7:
            msg.body("❌ Formato incorrecto. Intenta nuevamente o escribe 'menu'.")
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
        msg.body("📦 ¿Cuál es la categoría del producto? (perecible / no perecible / limpieza)")

    elif estado == "esperando_categoria":
        cat = incoming_msg.lower()
        if cat not in CATEGORIAS:
            msg.body("❌ Categoría inválida. Usa: perecible / no perecible / limpieza")
            return str(resp)
        temp_data[phone_number]["_categoria"] = CATEGORIAS[cat]
        user_states[phone_number] = "esperando_empaque"
        msg.body("📦 ¿Cuál es el tipo de empaque? (unidad / caja / bolsa / paquete / saco / botella / lata / tetrapack / sobre)")

    elif estado == "esperando_empaque":
        emp = incoming_msg.lower()
        if emp not in EMPAQUES:
            msg.body("❌ Tipo de empaque inválido. Intenta nuevamente.")
            return str(resp)

        datos = temp_data.pop(phone_number)
        productos = obtener_productos(hoja_cliente)
        secuencial = str(len(productos) + 1).zfill(2)
        categoria = datos.pop("_categoria")
        marca_inicial = datos["marca"][0].upper()
        empaque = EMPAQUES[emp]
        codigo = f"{categoria}{marca_inicial}{empaque}{secuencial}"
        datos["codigo"] = codigo

        hoja_cliente.append_row([
            datos["codigo"], datos["nombre"], datos["marca"], datos["fecha"], datos["costo"],
            datos["cantidad"], datos["precio"], datos["stock_minimo"], datos["ultima_compra"]
        ])

        user_states.pop(phone_number, None)
        msg.body(f"✅ Producto '{datos['nombre']}' agregado con código {codigo}.")

    elif incoming_msg == "4":
        user_states[phone_number] = "editar_codigo_producto"
        msg.body("✏️ Ingresa el código del producto que deseas editar:")

    elif estado == "editar_codigo_producto":
        user_states[phone_number] = "esperando_nuevos_datos"
        temp_data[phone_number] = {"codigo": incoming_msg.strip().upper()}
        msg.body("📝 Ingresa los nuevos datos en este formato:\n"
                 "Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo")

    elif estado == "esperando_nuevos_datos":
        partes = [x.strip() for x in incoming_msg.split(",")]
        if len(partes) != 7:
            msg.body("❌ Formato incorrecto. Intenta nuevamente o escribe 'menu'.")
            return str(resp)
        datos = temp_data.pop(phone_number)
        actualizado = actualizar_producto_por_codigo(hoja_cliente, datos["codigo"], partes)
        user_states.pop(phone_number, None)
        if actualizado:
            msg.body("✅ Producto actualizado correctamente.")
        else:
            msg.body("❌ No se encontró el producto con ese código.")

    elif incoming_msg == "6":
        user_states[phone_number] = "registrar_ingreso"
        msg.body("📥 Ingresa el código del producto y la cantidad a ingresar (ej. ABCD01, 10):")

    elif estado == "registrar_ingreso":
        try:
            codigo, cantidad = [x.strip() for x in incoming_msg.split(",")]
            actualizado = actualizar_producto_por_codigo(hoja_cliente, codigo.upper(), cantidad, tipo="ingreso")
            msg.body("✅ Ingreso registrado." if actualizado else "❌ Producto no encontrado.")
        except:
            msg.body("❌ Formato incorrecto. Usa: código, cantidad")
        user_states.pop(phone_number, None)

    elif incoming_msg == "7":
        user_states[phone_number] = "registrar_salida"
        msg.body("📤 Ingresa el código del producto y la cantidad a retirar (ej. ABCD01, 5):")

    elif estado == "registrar_salida":
        try:
            codigo, cantidad = [x.strip() for x in incoming_msg.split(",")]
            actualizado = actualizar_producto_por_codigo(hoja_cliente, codigo.upper(), cantidad, tipo="salida")
            msg.body("✅ Salida registrada." if actualizado else "❌ Producto no encontrado o stock insuficiente.")
        except:
            msg.body("❌ Formato incorrecto. Usa: código, cantidad")
        user_states.pop(phone_number, None)

    else:
        msg.body("❓ No entendí eso. Escribe 'menu' para ver las opciones disponibles.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
