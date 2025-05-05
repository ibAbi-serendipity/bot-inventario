from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google_sheets import get_inventory_sheet_for_number, agregar_producto, obtener_productos
from datetime import datetime

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
        msg.body("📦 ¿Cuál es el tipo de empaque? (unidad / caja / bolsa / paquete / saco / botella / lata / tetrapack / sobre)")
        return str(resp)

    elif estado == "esperando_empaque":
        emp = incoming_msg.lower()
        if emp not in EMPAQUES:
            msg.body("❌ Tipo de empaque inválido. Usa: unidad / caja / bolsa / paquete / saco / botella / lata / tetrapack / sobre")
            return str(resp)

        datos = temp_data.pop(phone_number)
        user_states.pop(phone_number, None)

        productos = obtener_productos(hoja_cliente)
        secuencial = str(len(productos) + 1).zfill(2)

        categoria = datos.pop("_categoria")
        marca_inicial = datos["marca"][0].upper()
        empaque = EMPAQUES[emp]

        codigo = f"{categoria}{marca_inicial}{empaque}{secuencial}"
        datos["codigo"] = codigo

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
        user_states[phone_number] = "ver_productos_opcion"
        msg.body("👀 ¿Qué deseas hacer?\n1. Ver todos\n2. Filtrar por código\n0. Volver al menú principal")

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
        user_states.pop(phone_number, None)

    elif incoming_msg == "2":
        user_states[phone_number] = "esperando_datos_producto"
        msg.body("📝 Por favor envía los datos del producto en este formato:\n"
                 "`Nombre, Marca, Fecha (AAAA-MM-DD), Costo, Cantidad, Precio, Stock Mínimo`")

    elif incoming_msg == "3":
        user_states[phone_number] = "opcion_actualizar"
        msg.body("🔧 ¿Qué deseas hacer?\n1. Editar producto\n2. Registrar ingreso\n3. Registrar salida")

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
        codigo_edit = incoming_msg.upper().strip()
        productos = obtener_productos(hoja_cliente)
        encontrado = next((i for i, p in enumerate(productos) if p.get("codigo") == codigo_edit), None)
        if encontrado is None:
            msg.body("❌ Código no encontrado. Intenta de nuevo o envía 'menu' para salir.")
        else:
            temp_data[phone_number] = {"indice": encontrado}
            user_states[phone_number] = "editar_dato"
            msg.body("🛠 ¿Qué deseas editar?\n1. Nombre\n2. Marca\n3. Fecha vencimiento\n4. Costo\n5. Cantidad\n6. Precio\n7. Stock mínimo\n0. Cancelar")

    elif estado == "editar_dato":
        opciones = {"1": "fecha", "2": "costo", "3": "precio", "4": "stock_minimo"}
        if incoming_msg == "0":
            user_states.pop(phone_number, None)
            temp_data.pop(phone_number, None)
            msg.body("✅ Edición cancelada. Envía 'menu' para ver opciones.")
        elif incoming_msg in opciones:
            temp_data[phone_number]["campo"] = opciones[incoming_msg]
            user_states[phone_number] = "editar_valor"
            msg.body(f"✏️ Ingresa el nuevo valor para {opciones[incoming_msg].replace('_', ' ')}:")
        else:
            msg.body("❌ Opción inválida. Elige un número del 1 al 4 o 0 para cancelar.")

    elif estado == "editar_valor":
        datos = temp_data.pop(phone_number)
        productos = obtener_productos(hoja_cliente)
        productos[datos["indice"]][datos["campo"]] = incoming_msg.strip()
        hoja_cliente.update(f"A{datos['indice'] + 2}:I{datos['indice'] + 2}", [[
            productos[datos["indice"]]["fecha"],
            productos[datos["indice"]]["costo"],
            productos[datos["indice"]]["precio"],
            productos[datos["indice"]]["stock_minimo"]
        ]])
        user_states.pop(phone_number, None)
        msg.body("✅ Producto actualizado correctamente.")

    elif estado == "registrar_ingreso":
        codigo = incoming_msg.upper().strip()
        productos = obtener_productos(hoja_cliente)
        encontrado = next((i for i, p in enumerate(productos) if p.get("codigo") == codigo), None)
        if encontrado is None:
            msg.body("❌ Código no encontrado. Intenta de nuevo o envía 'menu'.")
        else:
            temp_data[phone_number] = {"indice": encontrado}
            user_states[phone_number] = "registrar_ingreso_valor"
            msg.body("📦 ¿Cuántas unidades deseas agregar?")

    elif estado == "registrar_ingreso_valor":
        try:
            cantidad = int(incoming_msg)
            datos = temp_data.pop(phone_number)
            productos = obtener_productos(hoja_cliente)
            actual = int(productos[datos["indice"]]["cantidad"])
            productos[datos["indice"]]["cantidad"] = str(actual + cantidad)
            productos[datos["indice"]]["ultima_compra"] = datetime.now().strftime("%Y-%m-%d")

            hoja_cliente.update(f"A{datos['indice'] + 2}:I{datos['indice'] + 2}", [[
                productos[datos["indice"]]["cantidad"],
                productos[datos["indice"]]["ultima_compra"]
            ]])
            user_states.pop(phone_number, None)
            msg.body(f"✅ Ingreso registrado. Nuevo stock: {productos[datos['indice']]['cantidad']}")
        except ValueError:
            msg.body("❌ Ingresa una cantidad válida.")

    elif estado == "registrar_salida":
        codigo = incoming_msg.upper().strip()
        productos = obtener_productos(hoja_cliente)
        encontrado = next((i for i, p in enumerate(productos) if p.get("codigo") == codigo), None)
        if encontrado is None:
            msg.body("❌ Código no encontrado. Intenta de nuevo o envía 'menu'.")
        else:
            temp_data[phone_number] = {"indice": encontrado}
            user_states[phone_number] = "registrar_salida_valor"
            msg.body("📤 ¿Cuántas unidades deseas retirar?")

    elif estado == "registrar_salida_valor":
        try:
            cantidad = int(incoming_msg)
            datos = temp_data.pop(phone_number)
            productos = obtener_productos(hoja_cliente)
            actual = int(productos[datos["indice"]]["cantidad"])
            nuevo_stock = max(0, actual - cantidad)
            productos[datos["indice"]]["cantidad"] = str(nuevo_stock)

            hoja_cliente.update(f"A{datos['indice'] + 2}:I{datos['indice'] + 2}", [[
                productos[datos["indice"]]["cantidad"],
                productos[datos["indice"]]["ultima_compra"]
            ]])
            user_states.pop(phone_number, None)
            msg.body(f"✅ Salida registrada. Nuevo stock: {productos[datos['indice']]['cantidad']}")
        except ValueError:
            msg.body("❌ Ingresa una cantidad válida.")

    else:
        msg.body("Envía 'menu' para ver las opciones disponibles.")

    return str(resp)

if __name__ == "__main__":
    print("✅ Flask está listo para recibir mensajes")
    app.run(host="0.0.0.0", port=10000)
