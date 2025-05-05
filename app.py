from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import get_inventory_sheet_for_number, agregar_producto, obtener_productos

app = Flask(__name__)
user_states = {}

@app.route("/webhook", methods=["POST"])
def whatsapp_bot():
    print("📩 Se recibió una solicitud en el webhook")
    incoming_msg = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").replace("whatsapp:", "").replace("+", "")
    print(f"📱 Número recibido: {phone_number}")
    print(f"📝 Mensaje recibido: {incoming_msg}")
    
    hoja_cliente = get_inventory_sheet_for_number(phone_number)
    resp = MessagingResponse()
    msg = resp.message()

    if not hoja_cliente:
        msg.body("❌ Tu número no está registrado. Por favor contacta con el administrador.")
        return str(resp)

    # === VERIFICAR ESTADO ===
    if user_states.get(phone_number) == "esperando_datos_producto":
        print("🔁 Estado: esperando_datos_producto")
        print(f"📝 Texto recibido: {incoming_msg}")

        try:
            partes = [x.strip() for x in incoming_msg.split(",")]
            if len(partes) != 8:
                raise ValueError("Cantidad de datos incorrecta.")

            producto = {
                "codigo": partes[0],
                "nombre": partes[1],
                "marca": partes[2],
                "fecha": partes[3],
                "costo": partes[4],
                "cantidad": partes[5],
                "precio": partes[6],
                "stock_minimo": partes[7],
                "ultima_compra": ""
            }

            agregar_producto(hoja_cliente, producto)
            msg.body(f"✅ Producto '{producto['nombre']}' agregado correctamente.")
        except Exception as e:
            print(f"❌ Error procesando producto: {e}")
            msg.body("⚠️ Error al registrar producto. Verifica el formato e intenta nuevamente.")
        finally:
            user_states.pop(phone_number, None)

    # === MENÚ PRINCIPAL ===
    print(f"📝 Mensaje recibido: {incoming_msg}")
    if incoming_msg.lower() in ["hola", "menu", "inicio"]:
        user_states.pop(phone_number, None) 
        menu = (
            "👋 ¡Bienvenido al bot de inventario!\n"
            "Elige una opción:\n"
            "1️⃣ Ver productos\n"
            "2️⃣ Filtrar por código\n"
            "3️⃣ Agregar producto\n"
            "4️⃣ Actualizar producto\n"
            "5️⃣ Eliminar producto\n"
            "6️⃣ Registrar entrada\n"
            "7️⃣ Registrar salida\n"
            "8️⃣ Reporte\n"
            "9️⃣ Sugerencias de compra\n"
            "0️⃣ Revisar stock mínimo / vencimiento"
        )
        msg.body(menu)
        return str(resp)

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

    elif incoming_msg == "3":
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Por favor envía los datos del producto en este formato:\n"
                "`Código, Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo`")

    else:
        msg.body("Envía 'menu' para ver las opciones disponibles.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)