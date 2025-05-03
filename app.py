from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import get_inventory_sheet_for_number, agregar_producto, obtener_productos

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
    "bolsa": "B"
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

    if estado == "esperando_datos_producto":
        try:
            partes = [x.strip() for x in incoming_msg.split(",")]
            if len(partes) != 7:
                raise ValueError("Cantidad de datos incorrecta.")

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
        except Exception as e:
            msg.body("⚠️ Error al registrar producto. Verifica el formato e intenta nuevamente.")
            user_states.pop(phone_number, None)
        return str(resp)

    elif estado == "esperando_categoria":
        cat = incoming_msg.lower()
        if cat not in CATEGORIAS:
            msg.body("❌ Categoría inválida. Usa: perecible / no perecible / limpieza")
            return str(resp)

        temp_data[phone_number]["_categoria"] = CATEGORIAS[cat]
        user_states[phone_number] = "esperando_empaque"
        msg.body("📦 ¿Cuál es el tipo de empaque? (unidad / caja / bolsa)")
        return str(resp)

    elif estado == "esperando_empaque":
        emp = incoming_msg.lower()
        if emp not in EMPAQUES:
            msg.body("❌ Tipo de empaque inválido. Usa: unidad / caja / bolsa")
            return str(resp)

        datos = temp_data.pop(phone_number)
        user_states.pop(phone_number, None)

        # Obtener código secuencial
        productos = obtener_productos(hoja_cliente)
        secuencial = str(len(productos) + 1).zfill(2)

        categoria = datos.pop("_categoria")
        marca_inicial = datos["marca"][0].upper()
        empaque = EMPAQUES[emp]

        codigo = f"{categoria}{marca_inicial}{empaque}{secuencial}"
        datos["codigo"] = codigo

        # Insertar en hoja con código al inicio
        hoja_cliente.append_row([
            datos["codigo"],
            datos["nombre"],
            datos["marca"],
            datos["fecha"],
            datos["costo"],
            datos["cantidad"],
            datos["precio"],
            datos["stock_minimo"],
            datos["ultima_compra"]
        ])

        msg.body(f"✅ Producto '{datos['nombre']}' agregado con código {codigo}.")
        return str(resp)

    # === MENÚ PRINCIPAL ===
    if incoming_msg.lower() in ["hola", "menu", "inicio"]:
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
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Por favor envía los datos del producto en este formato:\n"
                 "`Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo`")

    else:
        msg.body("Envía 'menu' para ver las opciones disponibles.")

    return str(resp)

if __name__ == "__main__":
    print("✅ Flask está listo para recibir mensajes")
    app.run(host="0.0.0.0", port=10000)
