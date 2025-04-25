from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import get_inventory_sheet_for_number

app = Flask(__name__)
user_states = {}

@app.route("/webhook", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").replace("whatsapp:", "")
    
    hoja_cliente = get_inventory_sheet_for_number(phone_number)
    resp = MessagingResponse()
    msg = resp.message()

    if not hoja_cliente:
        msg.body("❌ Tu número no está registrado. Por favor contacta con el administrador.")
        return str(resp)

     # Verifica si el usuario está en estado de espera de datos
    if user_states.get(phone_number) == "awaiting_product_data":
        try:
            nombre, marca, fecha, cantidad, precio = [x.strip() for x in incoming_msg.split(",")]
            # Guardar en Google Sheets
            agregar_producto(hoja_cliente, nombre, marca, fecha, int(cantidad), float(precio))
            msg.body("✅ Producto agregado correctamente.")
        except Exception as e:
            msg.body("⚠️ Error en el formato. Intenta de nuevo con:\n`nombre, marca, fecha, cantidad, precio`")
        user_states.pop(phone_number, None)
        return str(resp)

    # Mostrar menú CRUD si está registrado
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

    elif incoming_msg == "2":
        msg.body("✍️ Ingresa los datos del producto como:\n`nombre, marca, fecha (DD/MM/AAAA), cantidad, precio`")
        user_states[phone_number] = "awaiting_product_data"
    
    else:
        msg.body("Envía 'menu' para ver las opciones disponibles.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
