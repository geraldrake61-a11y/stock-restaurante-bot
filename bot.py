import os
import json
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── ESTADOS ──────────────────────────────────────────────────────────────────
REGISTRO_NOMBRE = 0
ELEGIR_PRODUCTO  = 1
INGRESAR_CANTIDAD = 2
CONFIRMAR        = 3
JEFA_MENU        = 4
JEFA_CONSULTA    = 5

# ─── ARCHIVO LOCAL DE USUARIOS REGISTRADOS ────────────────────────────────────
USUARIOS_FILE = "usuarios_registrados.json"

def cargar_usuarios() -> dict:
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_usuario(user_id: str, nombre: str, rol: str):
    usuarios = cargar_usuarios()
    usuarios[user_id] = {"nombre": nombre, "rol": rol}
    with open(USUARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)
    logger.info(f"Usuario registrado: {nombre} (ID: {user_id})")

def buscar_usuario(user_id: str) -> dict | None:
    return cargar_usuarios().get(str(user_id))

# ─── NOMBRES DISPONIBLES ──────────────────────────────────────────────────────
NOMBRES_TRABAJADORES = ["Milagros", "Ruth", "Miguel", "Josué", "Mozo 1"]
NOMBRE_JEFA = "Adriana"

# ─── PRODUCTOS POR PERSONA ────────────────────────────────────────────────────
PRODUCTOS = {
    "Milagros": [
        {"nombre": "Papa",               "unidad": "costales",      "distribuidor": "Acomare"},
        {"nombre": "Zanahoria",          "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Kion",               "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Rocoto",             "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Ají limo",           "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Limón",              "unidad": "cajas",         "distribuidor": "Acomare"},
        {"nombre": "Huevos",             "unidad": "planchas",      "distribuidor": "Acomare"},
        {"nombre": "Maracuyá",           "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Maíz morado",        "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Culantro",           "unidad": "atados",        "distribuidor": "Avelino"},
        {"nombre": "Cebolla china",      "unidad": "mazos",         "distribuidor": "Avelino"},
        {"nombre": "Poro",               "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Apio",               "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Gallinas llegada",   "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Pollos llegada",     "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Gallinas congeladas","unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Pollos congelados",  "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Gallinas cierre",    "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Pollos cierre",      "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Cerdo",              "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Concho",             "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Fórmula de caldo",   "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Fideo",              "unidad": "kg",            "distribuidor": "Alicorp / Makro"},
        {"nombre": "Sal",                "unidad": "kg",            "distribuidor": "Alicorp"},
        {"nombre": "Café",               "unidad": "sobres",        "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Azúcar",             "unidad": "kg",            "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Té",            "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Anís",          "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Cedrón",        "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Muña",          "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Flor Jamaica",  "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Boldo",         "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Guantes blancos M",  "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Mallas",             "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
    ],
    "Ruth": [
        {"nombre": "Coca-Cola",          "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Inca-Cola",          "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Fanta",              "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Sprite",             "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Agua San Luis",      "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Agua Cielo",         "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Pepsi",              "unidad": "unidades",      "distribuidor": "El Centro"},
        {"nombre": "Kola escocesa",      "unidad": "unidades",      "distribuidor": "El Centro"},
        {"nombre": "Emoliente",          "unidad": "porciones",     "distribuidor": "El Centro"},
        {"nombre": "Chicha de jora",     "unidad": "litros",        "distribuidor": "Avelino"},
        {"nombre": "Aceite",             "unidad": "litros",        "distribuidor": "Alicorp"},
        {"nombre": "Mantequilla",        "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Masa de yucas",      "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Pan rústico",        "unidad": "unidades",      "distribuidor": "Mercado Incas"},
        {"nombre": "Tissues",            "unidad": "paquetes x10",  "distribuidor": "Makro"},
        {"nombre": "Bolsas cubiertos",   "unidad": "paquetes x200", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas Rappi",       "unidad": "paquetes x500", "distribuidor": "Aldair / Motta"},
        {"nombre": "Cucharas plástico",  "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas chismosas 19","unidad": "paquetes x100", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas tupper",      "unidad": "rollos",        "distribuidor": "Aldair / Motta"},
    ],
    "Miguel": [
        {"nombre": "Guantes negros M",   "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Tocas",              "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Grapas",             "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Mondadientes",       "unidad": "paquetes",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Trapos de mesa",     "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Poet",               "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Cloro",              "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Canchita",           "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Harina",             "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Polvo de hornear",   "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Ajinomoto",          "unidad": "bolsas",        "distribuidor": "Makro"},
        {"nombre": "Rollos impresora",   "unidad": "unidades",      "distribuidor": "Tienda cerca sede"},
    ],
    "Josué": [
        {"nombre": "Tuppers litro",           "unidad": "paquetes x25",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Tuppers medio litro",     "unidad": "paquetes x25",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Tuppers anisado",         "unidad": "paquetes x100", "distribuidor": "Aldair / Motta"},
        {"nombre": "Botellas pequeñas",       "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Botellas grandes",        "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsitas toppings",       "unidad": "paquetes x200", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsitas toppings grandes","unidad": "paquetes x100","distribuidor": "Aldair / Motta"},
    ],
    "Mozo 1": [
        {"nombre": "Pendiente de asignar", "unidad": "—", "distribuidor": "—"},
    ],
}

STOCK_IDEAL = {
    "Papa": 1.5, "Zanahoria": 6, "Kion": 6, "Rocoto": 4, "Ají limo": 0.5,
    "Limón": 1, "Huevos": 18, "Culantro": 1, "Cebolla china": 1, "Maracuyá": 5,
    "Maíz morado": 3, "Fideo": 12, "Sal": 12, "Aceite": 20, "Mantequilla": 0.5,
    "Gallinas congeladas": 50, "Pollos congelados": 10, "Cerdo": 5, "Concho": 3,
    "Coca-Cola": 24, "Inca-Cola": 24, "Fanta": 24, "Sprite": 24,
    "Agua San Luis": 12, "Agua Cielo": 12, "Pepsi": 24, "Kola escocesa": 24,
    "Tuppers litro": 20, "Tuppers medio litro": 20, "Botellas pequeñas": 100,
    "Botellas grandes": 60, "Guantes negros M": 3, "Guantes blancos M": 3,
    "Cloro": 8, "Trapos de mesa": 20, "Canchita": 9, "Harina": 10,
}

# ─── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("Falta GOOGLE_CREDENTIALS_JSON")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(os.environ.get("GOOGLE_SHEET_ID"))

def registrar_stock(nombre: str, producto: str, cantidad: float, unidad: str, distribuidor: str):
    try:
        hoja = get_sheet().worksheet("Registros")
        ahora = datetime.now()
        hoja.append_row([
            ahora.strftime("%d/%m/%Y"),
            ahora.strftime("%H:%M"),
            nombre, producto, cantidad, unidad, distribuidor,
        ])
        return True
    except Exception as e:
        logger.error(f"Error Sheets: {e}")
        return False

def obtener_stock_actual(busqueda: str = None) -> list:
    try:
        datos = get_sheet().worksheet("Registros").get_all_values()
        if len(datos) < 2:
            return []
        ultimo = {}
        for fila in datos[1:]:
            if len(fila) < 5:
                continue
            prod = fila[3]
            if busqueda and busqueda.lower() not in prod.lower():
                continue
            ultimo[prod] = {
                "fecha": fila[0], "hora": fila[1], "persona": fila[2],
                "producto": prod, "cantidad": fila[4],
                "unidad": fila[5] if len(fila) > 5 else "",
                "distribuidor": fila[6] if len(fila) > 6 else "",
            }
        return list(ultimo.values())
    except Exception as e:
        logger.error(f"Error leyendo Sheets: {e}")
        return []

# ─── TECLADOS ─────────────────────────────────────────────────────────────────
def teclado_nombres() -> ReplyKeyboardMarkup:
    nombres = NOMBRES_TRABAJADORES + [NOMBRE_JEFA]
    filas = [[KeyboardButton(n)] for n in nombres]
    return ReplyKeyboardMarkup(filas, resize_keyboard=True, one_time_keyboard=True)

def teclado_productos(nombre: str) -> ReplyKeyboardMarkup:
    prods = [p["nombre"] for p in PRODUCTOS.get(nombre, [])]
    prods.append("✅ Terminé por hoy")
    filas = []
    for i in range(0, len(prods), 2):
        filas.append([KeyboardButton(b) for b in prods[i:i+2]])
    return ReplyKeyboardMarkup(filas, resize_keyboard=True)

def teclado_confirmacion(cantidad: str, unidad: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(f"✅ Confirmar {cantidad} {unidad}")],
        [KeyboardButton("❌ Corregir")],
    ], resize_keyboard=True, one_time_keyboard=True)

def teclado_jefa() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔴 Stock crítico"),    KeyboardButton("🛒 Lista de compras")],
        [KeyboardButton("🔍 Consultar producto"),KeyboardButton("📊 Resumen del día")],
        [KeyboardButton("📍 Por distribuidor")],
    ], resize_keyboard=True)

# ─── FLUJO DE REGISTRO ────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    usuario = buscar_usuario(user_id)

    if usuario:
        # Ya registrado — ir directo al flujo correcto
        context.user_data["nombre"] = usuario["nombre"]
        context.user_data["rol"]    = usuario["rol"]
        return await bienvenida(update, context)

    # ── Auto-registro por deep link (/start milagros, /start mozo, etc.) ──
    DEEP_LINK_MAP = {
        "milagros": "Milagros",
        "ruth":     "Ruth",
        "miguel":   "Miguel",
        "josue":    "Josué",
        "josué":    "Josué",
        "mozo":     "Mozo 1",
        "adriana":  "Adriana",
    }
    if context.args:
        param = context.args[0].lower().strip()
        nombre = DEEP_LINK_MAP.get(param)
        if nombre:
            rol = "jefa" if nombre == NOMBRE_JEFA else "trabajador"
            guardar_usuario(user_id, nombre, rol)
            context.user_data["nombre"] = nombre
            context.user_data["rol"]    = rol
            await update.message.reply_text(
                f"✅ ¡Hola *{nombre}*! Quedaste registrado automáticamente.\n"
                f"Ya puedes empezar a reportar stock 👇",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            return await bienvenida(update, context)

    # Primera vez sin deep link — mostrar teclado de nombres
    await update.message.reply_text(
        "👋 Hola, ¿cuál es tu nombre?",
        reply_markup=teclado_nombres()
    )
    return REGISTRO_NOMBRE


async def registrar_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    nombres_validos = NOMBRES_TRABAJADORES + [NOMBRE_JEFA]

    if nombre not in nombres_validos:
        await update.message.reply_text(
            "Toca tu nombre del teclado 👇",
            reply_markup=teclado_nombres()
        )
        return REGISTRO_NOMBRE

    rol = "jefa" if nombre == NOMBRE_JEFA else "trabajador"
    user_id = str(update.effective_user.id)
    guardar_usuario(user_id, nombre, rol)

    context.user_data["nombre"] = nombre
    context.user_data["rol"]    = rol

    await update.message.reply_text(
        f"✅ Registrado como *{nombre}*.\n¡Ya puedes usar el bot!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return await bienvenida(update, context)


async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = context.user_data["nombre"]
    rol    = context.user_data["rol"]

    if rol == "jefa":
        await update.message.reply_text(
            f"Hola Adriana 👋\n¿Qué quieres revisar?",
            reply_markup=teclado_jefa()
        )
        return JEFA_MENU

    await update.message.reply_text(
        f"Hola {nombre} 👋\nToca un producto y escribe cuánto hay.",
        reply_markup=teclado_productos(nombre)
    )
    return ELEGIR_PRODUCTO

# ─── FLUJO TRABAJADOR ─────────────────────────────────────────────────────────
async def elegir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto  = update.message.text
    nombre = context.user_data.get("nombre")

    if texto == "✅ Terminé por hoy":
        await update.message.reply_text(
            "¡Listo! Gracias 🙌\nEscribe /inicio cuando quieras volver.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    productos = PRODUCTOS.get(nombre, [])
    prod_obj  = next((p for p in productos if p["nombre"] == texto), None)

    if not prod_obj:
        await update.message.reply_text(
            "Toca un producto del teclado 👇",
            reply_markup=teclado_productos(nombre)
        )
        return ELEGIR_PRODUCTO

    context.user_data["producto"] = prod_obj
    await update.message.reply_text(
        f"*{texto}*\n¿Cuántos {prod_obj['unidad']} hay ahora?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return INGRESAR_CANTIDAD


async def ingresar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().replace(",", ".")
    prod_obj = context.user_data.get("producto")

    try:
        cantidad = float(texto)
        if cantidad < 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Escribe solo el número.\nEjemplo: 3 o 2.5")
        return INGRESAR_CANTIDAD

    context.user_data["cantidad"] = cantidad
    await update.message.reply_text(
        f"¿Confirmas?\n*{prod_obj['nombre']}* → {cantidad} {prod_obj['unidad']}",
        parse_mode="Markdown",
        reply_markup=teclado_confirmacion(
            str(int(cantidad) if cantidad == int(cantidad) else cantidad),
            prod_obj["unidad"]
        )
    )
    return CONFIRMAR


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto    = update.message.text
    nombre   = context.user_data.get("nombre")
    prod_obj = context.user_data.get("producto")
    cantidad = context.user_data.get("cantidad")

    if "Corregir" in texto:
        await update.message.reply_text(
            f"*{prod_obj['nombre']}*\n¿Cuántos {prod_obj['unidad']} hay ahora?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return INGRESAR_CANTIDAD

    if "Confirmar" in texto:
        ok = registrar_stock(nombre, prod_obj["nombre"], cantidad,
                             prod_obj["unidad"], prod_obj["distribuidor"])

        ideal = STOCK_IDEAL.get(prod_obj["nombre"])
        if ideal:
            if cantidad < ideal * 0.5:
                estado = f"\n🔴 Stock muy bajo (ideal: {ideal} {prod_obj['unidad']})"
            elif cantidad < ideal * 0.9:
                estado = f"\n🟡 Stock bajo (ideal: {ideal} {prod_obj['unidad']})"
            else:
                estado = "\n✅ Stock OK"
        else:
            estado = ""

        msg = f"Guardado ✅{estado}\n\n¿Qué otro producto reportas?"
        if not ok:
            msg = f"⚠️ Error al guardar, avísale a Adriana.{estado}\n\n¿Qué otro producto reportas?"

        await update.message.reply_text(msg, reply_markup=teclado_productos(nombre))
        return ELEGIR_PRODUCTO

    await update.message.reply_text(
        "Usa los botones 👇",
        reply_markup=teclado_confirmacion(str(cantidad), prod_obj["unidad"])
    )
    return CONFIRMAR

# ─── FLUJO JEFA ───────────────────────────────────────────────────────────────
async def jefa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text

    if texto == "🔍 Consultar producto":
        await update.message.reply_text(
            "¿Qué producto quieres ver?\nEscribe el nombre:",
            reply_markup=ReplyKeyboardRemove()
        )
        return JEFA_CONSULTA

    if texto == "🔴 Stock crítico":
        registros = obtener_stock_actual()
        criticos, bajos = [], []
        for r in registros:
            ideal = STOCK_IDEAL.get(r["producto"])
            if not ideal:
                continue
            try:
                cant = float(r["cantidad"])
            except Exception:
                continue
            if cant < ideal * 0.5:
                criticos.append(f"🔴 {r['producto']}: {cant} {r['unidad']} (ideal: {ideal})")
            elif cant < ideal * 0.9:
                bajos.append(f"🟡 {r['producto']}: {cant} {r['unidad']} (ideal: {ideal})")

        if not criticos and not bajos:
            msg = "✅ Todo el stock está bien."
        else:
            msg = ""
            if criticos:
                msg += "*Crítico — comprar hoy:*\n" + "\n".join(criticos) + "\n\n"
            if bajos:
                msg += "*Bajo — comprar esta semana:*\n" + "\n".join(bajos)
        await update.message.reply_text(msg.strip() or "✅ Todo bien.", parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "🛒 Lista de compras":
        registros = obtener_stock_actual()
        por_dist  = {}
        for r in registros:
            ideal = STOCK_IDEAL.get(r["producto"])
            if not ideal:
                continue
            try:
                cant = float(r["cantidad"])
            except Exception:
                continue
            if cant < ideal * 0.9:
                dist = r["distribuidor"]
                falta = round(ideal - cant, 1)
                por_dist.setdefault(dist, []).append(
                    f"  • {r['producto']}: {falta} {r['unidad']}"
                )
        if not por_dist:
            msg = "✅ No hay nada urgente que comprar."
        else:
            msg = "*Lista de compras por lugar:*\n"
            for dist in sorted(por_dist):
                msg += f"\n📍 *{dist}*\n" + "\n".join(por_dist[dist])
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "📊 Resumen del día":
        registros = obtener_stock_actual()
        hoy = datetime.now().strftime("%d/%m/%Y")
        hoy_regs  = [r for r in registros if r.get("fecha") == hoy]
        personas  = {}
        for r in hoy_regs:
            personas[r["persona"]] = personas.get(r["persona"], 0) + 1
        msg = f"📊 *Resumen {hoy}*\n\n"
        if personas:
            for p, n in sorted(personas.items()):
                msg += f"• {p}: {n} productos\n"
            msg += f"\nTotal reportado: {len(hoy_regs)} productos"
        else:
            msg += "Aún no hay reportes hoy."
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "📍 Por distribuidor":
        registros = obtener_stock_actual()
        por_dist  = {}
        for r in registros:
            ideal = STOCK_IDEAL.get(r["producto"])
            if not ideal:
                continue
            try:
                cant = float(r["cantidad"])
            except Exception:
                continue
            if cant < ideal * 0.9:
                dist = r["distribuidor"]
                emoji = "🔴" if cant < ideal * 0.5 else "🟡"
                por_dist.setdefault(dist, []).append(
                    f"  {emoji} {r['producto']}: {cant}/{ideal} {r['unidad']}"
                )
        if not por_dist:
            msg = "✅ Nada urgente por distribuidor."
        else:
            msg = "*Por distribuidor:*\n"
            for dist in sorted(por_dist):
                msg += f"\n📍 *{dist}*\n" + "\n".join(por_dist[dist])
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    await update.message.reply_text("Usa los botones 👇", reply_markup=teclado_jefa())
    return JEFA_MENU


async def jefa_consulta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda  = update.message.text.strip()
    registros = obtener_stock_actual(busqueda)

    if registros:
        msg = ""
        for r in registros:
            ideal = STOCK_IDEAL.get(r["producto"])
            try:
                cant = float(r["cantidad"])
                if ideal:
                    emoji = "🔴" if cant < ideal * 0.5 else ("🟡" if cant < ideal * 0.9 else "✅")
                else:
                    emoji = "📦"
            except Exception:
                emoji = "📦"
            msg += (
                f"{emoji} *{r['producto']}*\n"
                f"Stock: {r['cantidad']} {r['unidad']}\n"
                f"Reportado: {r['fecha']} {r['hora']} — {r['persona']}\n"
                f"Comprar en: {r['distribuidor']}\n\n"
            )
    else:
        msg = f"No encontré \"{busqueda}\".\nRevisa cómo está escrito."

    await update.message.reply_text(msg.strip(), parse_mode="Markdown", reply_markup=teclado_jefa())
    return JEFA_MENU


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Saliste. Escribe /inicio para volver.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Falta TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start",  start),
            CommandHandler("inicio", start),
        ],
        states={
            REGISTRO_NOMBRE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_nombre)],
            ELEGIR_PRODUCTO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_producto)],
            INGRESAR_CANTIDAD:[MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cantidad)],
            CONFIRMAR:        [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
            JEFA_MENU:        [MessageHandler(filters.TEXT & ~filters.COMMAND, jefa_menu)],
            JEFA_CONSULTA:    [MessageHandler(filters.TEXT & ~filters.COMMAND, jefa_consulta)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    logger.info("Bot iniciado ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
