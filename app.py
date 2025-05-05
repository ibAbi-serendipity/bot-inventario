from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import get_inventory_sheet_for_number, agregar_producto, obtener_productos

app = Flask(__name__)
user_states = {}
temp_data = {}

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

    # === VERIFICAR ESTADO ===
    if user_states.get(phone_number) == "esperando_datos_producto":
        try:
            partes = [x.strip() for x in incoming_msg.split(",")]
            if len(partes) != 7:
                raise ValueError("Cantidad de datos incorrecta.")

            producto = {
                "nombre": partes[0],
                "marca": partes[1],
                "fecha": partes[2],
                "costo": partes[3],
                "cantidad": partes[4],
                "precio": partes[5],
                "stock_minimo": partes[6],
                "ultima_compra": ""
            }

            agregar_producto(hoja_cliente, producto)
            msg.body(f"✅ Producto '{producto['nombre']}' agregado correctamente.")
        except Exception as e:
            msg.body("⚠️ Error al registrar producto. Verifica el formato e intenta nuevamente.")
        finally:
            user_states.pop(phone_number, None)
        return str(resp)

    # === MENÚ PRINCIPAL ===
    if incoming_msg.lower() in ["hola", "menu", "inicio"]:
        menu = (
            "👋 ¡Bienvenido al bot de inventario!\n"
            "Elige una opción:\n"
            "1️⃣ Ver productos\n"
            "2️⃣ Agregar producto\n"
            "3️⃣ Actualizar producto\n"
            "4️⃣ Eliminar producto\n"
            "5️⃣ Reporte\n"
            "6️⃣ Sugerencias de compra\n"
            "7️⃣ Revisar stock mínimo / vencimiento"
        )
        msg.body(menu)

    elif incoming_msg == "1":
        productos = obtener_productos(hoja_cliente)
        if not productos:
            msg.body("📭 No hay productos registrados.")
        else:
            respuesta = "📦 Productos en inventario:\n"
            for i, p in enumerate(productos, start=1):
                respuesta += (
                    f"{i}. {p['nombre']} - {p['marca']}, Vence: {p['fecha']}, "
                    f"Stock: {p['cantidad']} - Precio: S/ {p['precio']}\n"
                )
            msg.body(respuesta)

    elif incoming_msg == "2":
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Por favor envía los datos del producto en este formato:\n"
                 "Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo")

    else:
        msg.body("Envía 'menu' para ver las opciones disponibles.")

    return str(resp)

if __name__ == "__main__":
     print("✅ Flask está listo para recibir mensajes")
    app.run(host="0.0.0.0", port=10000)