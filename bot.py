import os
import json
import logging
import unicodedata
from datetime import datetime, time, timedelta

def quitar_tildes(texto: str) -> str:
    if not texto: return ""
    texto = texto.lower().strip()
    return ''.join((c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn'))

import pytz

def get_now():
    return datetime.now(pytz.timezone('America/Lima'))
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
REGISTRO_NOMBRE  = 0
ELEGIR_PRODUCTO  = 1
INGRESAR_CANTIDAD= 2
CONFIRMAR        = 3
JEFA_MENU        = 4
JEFA_CONSULTA    = 5
VER_STOCK        = 6

ADMIN_MENU       = 7
ADMIN_SEDE       = 8
ADMIN_TRABAJADOR = 9

CAJA_INGRESO     = 10

JEFA_TRABAJADOR  = 11

CONSUMOS_TIPO     = 12
CONSUMOS_PERSONAL = 13
CONSUMOS_MONTO    = 14
JEFA_CATEGORIA_ELEGIR = 15

# ─── PERSISTENCIA DE USUARIOS EN GOOGLE SHEETS ────────────────────────────────
USUARIOS_FILE  = "usuarios_registrados.json"   # caché local de respaldo
USUARIOS_SHEET = "Usuarios"                     # pestaña dentro del sheet Umacollo

# Caché en memoria: se llena la primera vez y se actualiza al registrar
_usuarios_cache: dict | None = None

def _hoja_usuarios():
    """Devuelve la worksheet Usuarios (la crea si no existe)."""
    try:
        ss = get_sheet(SHEET_ID_UMACOLLO)
        try:
            return ss.worksheet(USUARIOS_SHEET)
        except Exception:
            ws = ss.add_worksheet(USUARIOS_SHEET, rows=200, cols=4)
            ws.append_row(["user_id", "nombre", "rol", "sede"])
            return ws
    except Exception as e:
        logger.error(f"Error accediendo hoja Usuarios: {e}")
        return None

def cargar_usuarios() -> dict:
    global _usuarios_cache
    if _usuarios_cache is not None:
        return _usuarios_cache
    # 1. Intentar desde Google Sheets
    ws = _hoja_usuarios()
    if ws:
        try:
            filas = ws.get_all_records()  # headers: user_id, nombre, rol, sede
            usuarios = {}
            for f in filas:
                uid = str(f.get("user_id", "")).strip()
                if uid:
                    usuarios[uid] = {
                        "nombre": f.get("nombre", ""),
                        "rol":    f.get("rol", "trabajador"),
                        "sede":   f.get("sede") or None,
                    }
            _usuarios_cache = usuarios
            # Sincronizar copia local
            with open(USUARIOS_FILE, "w", encoding="utf-8") as fp:
                json.dump(usuarios, fp, ensure_ascii=False, indent=2)
            return usuarios
        except Exception as e:
            logger.error(f"Error leyendo Usuarios de Sheets: {e}")
    # 2. Fallback: archivo local
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r", encoding="utf-8") as fp:
            _usuarios_cache = json.load(fp)
            return _usuarios_cache
    _usuarios_cache = {}
    return {}

def guardar_usuario(user_id: str, nombre: str, rol: str, sede: str = None):
    global _usuarios_cache
    uid = str(user_id)
    # Actualizar caché en memoria
    if _usuarios_cache is None:
        cargar_usuarios()
    _usuarios_cache[uid] = {"nombre": nombre, "rol": rol, "sede": sede}
    # Guardar en Google Sheets
    ws = _hoja_usuarios()
    if ws:
        try:
            celda = None
            try:
                celda = ws.find(uid, in_column=1)
            except Exception:
                pass
            fila = [uid, nombre, rol, sede or ""]
            if celda:
                ws.update(range_name=f"A{celda.row}:D{celda.row}", values=[fila])
            else:
                ws.append_row(fila)
        except Exception as e:
            logger.error(f"Error guardando usuario en Sheets: {e}")
    # Guardar copia local de respaldo
    with open(USUARIOS_FILE, "w", encoding="utf-8") as fp:
        json.dump(_usuarios_cache, fp, ensure_ascii=False, indent=2)

def buscar_usuario(user_id: str) -> dict | None:
    if str(user_id) == "1427645515":
        return {"nombre": "Admin", "rol": "admin", "sede": None}
    return cargar_usuarios().get(str(user_id))

# ─── CONFIGURACIÓN DE SEDES ───────────────────────────────────────────────────
NOMBRE_JEFA = "Adriana"

NOMBRES_UMACOLLO = ["Milagros", "Ruth", "Miguel", "Josué", "Hermes"]
NOMBRES_EU       = ["Carlos", "Flor", "Danitza", "María Vargas",
                    "Brendali", "Jimena", "Sebastian", "Ivan", "Lionel"]
NOMBRES_TRABAJADORES = NOMBRES_UMACOLLO + NOMBRES_EU

SEDE_POR_NOMBRE = {n: "Umacollo" for n in NOMBRES_UMACOLLO}
SEDE_POR_NOMBRE.update({n: "Av. Estados Unidos" for n in NOMBRES_EU})

SHEET_ID_UMACOLLO = os.environ.get("GOOGLE_SHEET_ID", "").strip()
SHEET_ID_EU       = os.environ.get("GOOGLE_SHEET_ID_EU", "").strip()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ─── DEEP LINK MAP ────────────────────────────────────────────────────────────
DEEP_LINK_MAP = {
    # Umacollo
    "milagros":    ("Milagros",     "trabajador", "Umacollo"),
    "ruth":        ("Ruth",         "trabajador", "Umacollo"),
    "miguel":      ("Miguel",       "trabajador", "Umacollo"),
    "josue":       ("Josué",        "trabajador", "Umacollo"),
    "josué":       ("Josué",        "trabajador", "Umacollo"),
    "hermes":        ("Hermes",       "trabajador", "Umacollo"),
    # Av. Estados Unidos
    "carlos":      ("Carlos",       "trabajador", "Av. Estados Unidos"),
    "flor":        ("Flor",         "trabajador", "Av. Estados Unidos"),
    "danitza":     ("Danitza",      "trabajador", "Av. Estados Unidos"),
    "mariavargas": ("María Vargas", "trabajador", "Av. Estados Unidos"),
    "brendali":    ("Brendali",     "trabajador", "Av. Estados Unidos"),
    "jimena":      ("Jimena",       "trabajador", "Av. Estados Unidos"),
    "sebastian":   ("Sebastian",    "trabajador", "Av. Estados Unidos"),
    "ivan":        ("Ivan",         "trabajador", "Av. Estados Unidos"),
    "lionel":      ("Lionel",       "trabajador", "Av. Estados Unidos"),
    # Jefa y Admin
    "adriana":     ("Adriana",      "jefa",       None),
    "admin":       ("Admin",        "admin",      None),
}

# ─── PRODUCTOS ────────────────────────────────────────────────────────────────
PRODUCTOS = {
    # ── UMACOLLO ──────────────────────────────────────────────────────────────
    "Milagros": [
        {"nombre": "Papa",               "unidad": "costales",      "distribuidor": "Acomare"},
        {"nombre": "Zanahoria",          "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Kion",               "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Rocoto",             "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Ají limo",           "unidad": "gramos",        "distribuidor": "Acomare"},
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
        {"nombre": "Fideo",              "unidad": "kg",            "distribuidor": "Alicorp / Makro"},
        {"nombre": "Sal",                "unidad": "kg",            "distribuidor": "Alicorp"},
        {"nombre": "Ajinomoto",          "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Mallas",             "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
    ],
    "Ruth": [
        {"nombre": "Grapas",             "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Mondadientes",       "unidad": "paquetes",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Trapos de mesa",     "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Poet",               "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Cloro",              "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Rollos impresora",   "unidad": "unidades",      "distribuidor": "Tienda cerca sede"},
        {"nombre": "Cartas",             "unidad": "unidades",      "distribuidor": "El Centro"},
    ],
    "Miguel": [
        {"nombre": "Aceite",             "unidad": "litros",        "distribuidor": "Alicorp"},
        {"nombre": "Mantequilla",        "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Masa de yucas",      "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Pan rústico",        "unidad": "unidades",      "distribuidor": "Mercado Incas"},
        {"nombre": "Bolsas cubiertos",   "unidad": "paquetes x200", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas Rappi",       "unidad": "paquetes x500", "distribuidor": "Aldair / Motta"},
        {"nombre": "Cucharas plástico",  "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas chismosas 19","unidad": "paquetes x100", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas tupper",      "unidad": "rollos",        "distribuidor": "Aldair / Motta"},
        {"nombre": "Inf. Té",            "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Anís",          "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Cedrón",        "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Muña",          "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Flor Jamaica",  "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Boldo",         "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Guantes blancos M",  "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Café",               "unidad": "gramos",        "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Azúcar",             "unidad": "kg",            "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Harina",             "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Polvo de hornear",   "unidad": "unidades",      "distribuidor": "Makro"},
    ],
    "Josué": [
        {"nombre": "Fórmula de caldo",        "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Tuppers litro",           "unidad": "paquetes x25",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Tuppers medio litro",     "unidad": "paquetes x25",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Tuppers anisado",         "unidad": "paquetes x100", "distribuidor": "Aldair / Motta"},
        {"nombre": "Botellas pequeñas",       "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Botellas grandes",        "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsitas toppings",       "unidad": "paquetes x200", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsitas toppings grandes","unidad": "paquetes x100","distribuidor": "Aldair / Motta"},
    ],
    "Hermes": [
        {"nombre": "Canchita",           "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Coca-Cola",          "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Inka Cola",          "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Fanta",              "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Sprite",             "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Agua San Luis",      "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Agua Cielo",         "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Pepsi",              "unidad": "unidades",      "distribuidor": "El Centro"},
        {"nombre": "Kola escocesa",      "unidad": "unidades",      "distribuidor": "El Centro"},
        {"nombre": "Emoliente",          "unidad": "litros",        "distribuidor": "El Centro"},
        {"nombre": "Chicha de jora",     "unidad": "litros",        "distribuidor": "Avelino"},
        {"nombre": "Tissues",            "unidad": "paquetes x10",  "distribuidor": "Makro"},
        {"nombre": "Guantes negros M",   "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Tocas",              "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
    ],

    # ── AV. ESTADOS UNIDOS ────────────────────────────────────────────────────
    "Carlos": [
        {"nombre": "Papa",               "unidad": "costal",        "distribuidor": "Acomare"},
        {"nombre": "Kion",               "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Fideo",              "unidad": "kg",            "distribuidor": "Alicorp / Makro"},
        {"nombre": "Zanahoria",          "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Huevos",             "unidad": "plancha",       "distribuidor": "Acomare"},
        {"nombre": "Gallinas llegada",   "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Pollos llegada",     "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Gallinas congeladas","unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Pollos congelados",  "unidad": "unidades",      "distribuidor": "Avelino"},
    ],
    "Flor": [
        {"nombre": "Apio",               "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Poro",               "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Mallas",             "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Sal",                "unidad": "kg",            "distribuidor": "Alicorp"},
        {"nombre": "Botellas litro",     "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Botellas pequeñas",  "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
    ],
    "Danitza": [
        {"nombre": "Fórmula gallinas",   "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Fórmula pollos",     "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Gallinas cierre",    "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Pollos cierre",      "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Tuppers litro",      "unidad": "paquetes x25",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Tuppers medio litro","unidad": "paquetes x25",  "distribuidor": "Aldair / Motta"},
    ],
    "María Vargas": [
        {"nombre": "Conteo papas jornada","unidad": "unidades",     "distribuidor": "—"},
        {"nombre": "Huevos jornada",     "unidad": "unidades",      "distribuidor": "—"},
        {"nombre": "Guantes blancos M",  "unidad": "pares",         "distribuidor": "Aldair / Motta"},
        {"nombre": "Tocas",              "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
    ],
    "Brendali": [
        {"nombre": "Masa de yucas",          "unidad": "kg",            "distribuidor": "Avelino"},
        {"nombre": "Pan rústico",            "unidad": "unidades",      "distribuidor": "Mercado Incas"},
        {"nombre": "Mantequilla",            "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Ajo",                    "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Cebolla",                "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Aceite",                 "unidad": "litros",        "distribuidor": "Alicorp"},
        {"nombre": "Harina",                 "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Anís",                   "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Orégano",                "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Polvo de hornear",       "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Levadura",               "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Café",                   "unidad": "kg",            "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Azúcar",                 "unidad": "kg",            "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Clavo de olor",          "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Comino molido",          "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Comino entero",          "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Canela entera",          "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Té natural",             "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Orégano seco",           "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Ají panca color",        "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Ají panca sabor",        "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Pan seco",               "unidad": "kg",            "distribuidor": "Mercado Incas"},
        {"nombre": "Inf. Té",                "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Anís",              "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Cedrón",            "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Muña",              "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Flor de Jamaica",   "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        {"nombre": "Inf. Boldo",             "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
        # Productos heredados de Tamara
        {"nombre": "Bolsitas toppings",      "unidad": "paquetes x100", "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsitas toppings grandes","unidad": "paquetes x100","distribuidor": "Aldair / Motta"},
        {"nombre": "Tuppers cebolla china",  "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Rocoto",                 "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Cebolla china",          "unidad": "mazo",          "distribuidor": "Avelino"},
        {"nombre": "Limón",                  "unidad": "cajas",         "distribuidor": "Acomare"},
        {"nombre": "Canchita",               "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Ají limo",               "unidad": "kg",            "distribuidor": "Acomare"},
        {"nombre": "Pimienta en bola",       "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Té para reposar",        "unidad": "kg",            "distribuidor": "Makro"},
        {"nombre": "Inf. hierba luisa",      "unidad": "cajas",         "distribuidor": "Mercado Incas / Makro"},
    ],
    "Jimena": [
        {"nombre": "Bolsas cubiertos",       "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas Rappi",           "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Cucharas plástico",      "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas chismosas N°19",  "unidad": "paquetes x50",  "distribuidor": "Aldair / Motta"},
        {"nombre": "Bolsas tupper",          "unidad": "rollos",        "distribuidor": "Aldair / Motta"},
        {"nombre": "Grapas",                 "unidad": "cajas",         "distribuidor": "Aldair / Motta"},
    ],
    "Sebastian": [
        {"nombre": "Trapos de mesa",         "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Poet",                   "unidad": "unidades",      "distribuidor": "Makro"},
        {"nombre": "Limpia mesas",           "unidad": "litros",        "distribuidor": "Makro"},
        {"nombre": "Cloro",                  "unidad": "litros",        "distribuidor": "Makro"},
        {"nombre": "Mondadientes",           "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Tissues",                "unidad": "paquetes x25",  "distribuidor": "Makro"},
    ],
    "Ivan": [
        {"nombre": "Coca-Cola",              "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Inka Cola",              "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Fanta",                  "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Sprite",                 "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Pepsi",                  "unidad": "unidades",      "distribuidor": "El Centro"},
        {"nombre": "Gaseosa Escocesa",       "unidad": "unidades",      "distribuidor": "Aldair / Motta"},
        {"nombre": "Agua San Luis",          "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Agua Cielo",             "unidad": "unidades",      "distribuidor": "Coca-Cola"},
        {"nombre": "Rollos impresora",       "unidad": "unidades",      "distribuidor": "Tienda cerca sede"},
        {"nombre": "Gallinas jornada",       "unidad": "unidades",      "distribuidor": "Avelino"},
        {"nombre": "Gallinas cierre",        "unidad": "unidades",      "distribuidor": "Avelino"},
    ],
    "Lionel": [
        {"nombre": "Chicha morada",          "unidad": "litros",        "distribuidor": "Avelino"},
        {"nombre": "Emoliente",              "unidad": "litros",        "distribuidor": "El Centro"},
        {"nombre": "Chicha de jora",         "unidad": "litros",        "distribuidor": "Avelino"},
        {"nombre": "Jugo de maracuyá",       "unidad": "litros",        "distribuidor": "Avelino"},
    ],
}

# ─── STOCK IDEAL ──────────────────────────────────────────────────────────────
STOCK_IDEAL = {
    # Umacollo
    "Papa": 1.5, "Zanahoria": 6, "Kion": 6, "Rocoto": 4, "Ají limo": 250,
    "Limón": 1, "Huevos": 18, "Culantro": 1, "Cebolla china": 1, "Maracuyá": 5,
    "Maíz morado": 3, "Fideo": 12, "Sal": 12, "Aceite": 20, "Mantequilla": 0.5,
    "Gallinas congeladas": 50, "Pollos congelados": 10, "Cerdo": 5, "Concho": 3,
    "Coca-Cola": 24, "Inka Cola": 24, "Fanta": 24, "Sprite": 24,
    "Agua San Luis": 12, "Agua Cielo": 12, "Pepsi": 24, "Kola escocesa": 24,
    "Tuppers litro": 20, "Tuppers medio litro": 20, "Botellas pequeñas": 100,
    "Botellas grandes": 60, "Guantes negros M": 3, "Guantes blancos M": 3,
    "Cloro": 8, "Trapos de mesa": 20, "Canchita": 9, "Harina": 10,
    "Ajinomoto": 1, "Mallas": 2, "Fórmula de caldo": 5,
    "Gallinas llegada": 50, "Pollos llegada": 10,
    "Gallinas cierre": 30, "Pollos cierre": 5,
    # EU específicos
    "Gallinas jornada": 50, "Botellas litro": 30,
    "Fórmula gallinas": 5, "Fórmula pollos": 3,
    "Conteo papas jornada": 200, "Huevos jornada": 200,
    "Masa de yucas": 20, "Pan rústico": 100,
    "Ajo": 2, "Cebolla": 10, "Anís": 0.5, "Orégano": 0.5,
    "Polvo de hornear": 0.5, "Levadura": 0.5, "Café": 1, "Azúcar": 10,
    "Clavo de olor": 0.2, "Comino molido": 0.5, "Comino entero": 0.5,
    "Canela entera": 0.3, "Té natural": 3, "Orégano seco": 0.5,
    "Ají panca color": 2, "Ají panca sabor": 2, "Pan seco": 5,
    "Inf. Té": 3, "Inf. Anís": 3, "Inf. Cedrón": 3, "Inf. Muña": 3,
    "Inf. Flor de Jamaica": 3, "Inf. Boldo": 3, "Inf. Flor Jamaica": 3,
    "Bolsas cubiertos": 5, "Bolsas Rappi": 5, "Cucharas plástico": 5,
    "Bolsas chismosas N°19": 5, "Bolsas tupper": 3, "Grapas": 2,
    "Mondadientes": 500, "Tissues": 5, "Poet": 5, "Pimienta en bola": 1,
    "Limpia mesas": 5, "Gaseosa Escocesa": 50, "Rollos impresora": 5,
    "Té para reposar": 1, "Inf. hierba luisa": 2,
    "Bolsitas toppings": 5, "Bolsitas toppings grandes": 5,
    "Tuppers cebolla china": 3, "Tuppers anisado": 3,
    "Chicha morada": 10, "Emoliente": 10, "Chicha de jora": 10,
    "Jugo de maracuyá": 10, "Tocas": 30,
}

# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
def get_sheet(sheet_id: str):
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("Falta GOOGLE_CREDENTIALS_JSON")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)

def _get_o_crear_registros(sheet_id: str):
    """Devuelve la hoja Registros; la crea si no existe."""
    ss = get_sheet(sheet_id)
    try:
        return ss.worksheet("Registros")
    except Exception:
        ws = ss.add_worksheet("Registros", rows=1000, cols=8)
        ws.append_row(["Fecha", "Hora", "Responsable", "Producto",
                       "Stock Actual", "Unidad", "Distribuidor"])
        return ws

def registrar_stock(nombre: str, producto: str, cantidad: float,
                    unidad: str, distribuidor: str, sede: str):
    sheet_id = SHEET_ID_EU if sede == "Av. Estados Unidos" else SHEET_ID_UMACOLLO
    if not sheet_id:
        msg = f"SHEET_ID vacío para sede '{sede}'"
        logger.error(msg)
        return False, msg
    try:
        hoja = _get_o_crear_registros(sheet_id)
        ahora = get_now()
        hoja.append_row([
            ahora.strftime("%d/%m/%Y"),
            ahora.strftime("%H:%M"),
            nombre, producto, cantidad, unidad, distribuidor,
        ])
        return True, None
    except Exception as e:
        tag = f"{sheet_id[:8]}..." if sheet_id else "(vacío)"
        logger.error(f"Error Sheets [{sede}|{tag}]: {e}")
        return False, f"[{tag}] {str(e)[:100]}"

def _guardar_caja(sede: str, cajero: str, tipo_cuadre: str, monto: float):
    sheet_id = SHEET_ID_EU if sede == "Av. Estados Unidos" else SHEET_ID_UMACOLLO
    if not sheet_id: return False
    ss = get_sheet(sheet_id)
    try:
        ws = ss.worksheet("Caja")
    except Exception:
        ws = ss.add_worksheet("Caja", rows=1000, cols=6)
        ws.append_row(["Fecha", "Hora", "Cajero", "Sede", "Tipo", "Monto"])
    ahora = get_now()
    ws.append_row([ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M"), cajero, sede, tipo_cuadre, monto])
    return True

def _guardar_consumo(sede: str, registrador: str, consumidor: str, tipo_consumo: str, detalle: str):
    sheet_id = SHEET_ID_EU if sede == "Av. Estados Unidos" else SHEET_ID_UMACOLLO
    if not sheet_id: return False
    ss = get_sheet(sheet_id)
    try:
        ws = ss.worksheet("Consumos Personal")
    except Exception:
        ws = ss.add_worksheet("Consumos Personal", rows=1000, cols=7)
        ws.append_row(["Fecha", "Hora", "Registrador", "Consumidor", "Sede", "Tipo Consumo", "Detalle/Monto"])
    ahora = get_now()
    ws.append_row([ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M"), registrador, consumidor, sede, tipo_consumo, detalle])
    return True

def obtener_consumos_semanales() -> str:
    msg = "🍽️ *Consumo de Personal (Esta Semana)*\n"
    ahora = get_now()
    inicio_semana = ahora - timedelta(days=ahora.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    
    msg += f"_Desde el Lunes {inicio_semana.strftime('%d/%m/%Y')} hasta hoy_\n\n"
    
    resumen_dinero = {}
    resumen_otros = {}
    
    for sede_label, sheet_id in [("Umacollo", SHEET_ID_UMACOLLO), ("Av. Estados Unidos", SHEET_ID_EU)]:
        if not sheet_id: continue
        try:
            ws = get_sheet(sheet_id).worksheet("Consumos Personal")
            datos = ws.get_all_values()
            for f in datos[1:]:
                if len(f) < 7: continue
                try:
                    fecha_f = datetime.strptime(f[0], "%d/%m/%Y").replace(tzinfo=pytz.timezone('America/Lima'))
                except Exception:
                    continue
                if fecha_f >= inicio_semana:
                    consumidor = f[3]
                    detalle = f[6]
                    try:
                        monto = float(detalle.replace("S/", "").replace(",", ".").strip())
                        resumen_dinero[consumidor] = resumen_dinero.get(consumidor, 0.0) + monto
                    except ValueError:
                        resumen_otros.setdefault(consumidor, []).append(detalle)
        except Exception as e:
            logger.error(f"Error cargando consumos de {sede_label}: {e}")
            
    if not resumen_dinero and not resumen_otros:
        return msg + "✅ No se registró ningún consumo esta semana."
        
    for c, total in sorted(resumen_dinero.items(), key=lambda x: x[1], reverse=True):
        if total > 0:
            msg += f"👤 *{c}*: S/ {total:.2f}\n"
            if c in resumen_otros:
                for o in resumen_otros[c]:
                    msg += f"   - {o}\n"
                    
    for c, items in resumen_otros.items():
        if c not in resumen_dinero or resumen_dinero[c] <= 0:
            msg += f"👤 *{c}*:\n"
            for o in items:
                msg += f"   - {o}\n"
                
    return msg

def cargar_reportados_hoy(nombre: str, sede: str) -> set:
    """Productos ya reportados hoy por este trabajador (para precargar ✓)."""
    try:
        hoy = get_now().strftime("%d/%m/%Y")
        sheet_id = SHEET_ID_EU if sede == "Av. Estados Unidos" else SHEET_ID_UMACOLLO
        if not sheet_id:
            return set()
        datos = get_sheet(sheet_id).worksheet("Registros").get_all_values()
        return {
            fila[3] for fila in datos[1:]
            if len(fila) >= 4 and fila[0] == hoy and fila[2] == nombre
        }
    except Exception as e:
        logger.error(f"Error cargando reportados hoy [{nombre}]: {e}")
        return set()

def obtener_stock_sede(sheet_id: str, sede_label: str, busqueda: str = None) -> list:
    try:
        datos = get_sheet(sheet_id).worksheet("Registros").get_all_values()
        if len(datos) < 2:
            return []
        ultimo = {}
        for fila in datos[1:]:
            if len(fila) < 5 or not fila[3]:
                continue
            prod = fila[3]
            if busqueda and quitar_tildes(busqueda) not in quitar_tildes(prod):
                continue
            ultimo[prod] = {
                "fecha": fila[0], "hora": fila[1], "persona": fila[2],
                "producto": prod, "cantidad": fila[4],
                "unidad": fila[5] if len(fila) > 5 else "",
                "distribuidor": fila[6] if len(fila) > 6 else "",
                "sede": sede_label,
            }
        return list(ultimo.values())
    except Exception as e:
        logger.error(f"Error leyendo Sheets [{sede_label}]: {e}")
        return []

def obtener_stock_combinado(busqueda: str = None) -> list:
    r1 = obtener_stock_sede(SHEET_ID_UMACOLLO, "Umacollo", busqueda) if SHEET_ID_UMACOLLO else []
    r2 = obtener_stock_sede(SHEET_ID_EU, "Av. Estados Unidos", busqueda) if SHEET_ID_EU else []
    return r1 + r2

def obtener_stock_actual(busqueda: str = None) -> list:
    """Alias para compatibilidad — devuelve stock combinado de ambas sedes."""
    return obtener_stock_combinado(busqueda)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _get_categoria(prod: str) -> str:
    p = prod.lower()
    if any(x in p for x in ["bolsa", "tupper", "vaso", "cuchara", "malla", "grapa", "rollo", "toca", "guante"]):
        return "Plásticos y Empaques"
    if any(x in p for x in ["coca", "inka", "inca", "fanta", "sprite", "escocesa", "agua", "pepsi", "chicha", "emoliente", "maracuyá"]):
        return "Bebidas"
    if any(x in p for x in ["té", "anís", "cedrón", "muña", "jamaica", "boldo", "hierba luisa"]):
        return "Infusiones"
    if any(x in p for x in ["pollo", "gallina", "cerdo", "huevos", "concho"]):
        return "Carnes / Pollos"
    if any(x in p for x in ["papa", "zanahoria", "kion", "rocoto", "limón", "limon", "cebolla", "culantro", "poro", "apio", "ajo", "ají"]):
        return "Verduras"
    return "Abarrotes y Otros"

def _estado_emoji(cant, ideal):
    if not ideal:
        return "📦", ""
    try:
        pct = float(cant) / float(ideal)
    except Exception:
        return "📦", ""
    if pct < 0.50: return "🔴", f" (ideal: {ideal})"
    if pct < 0.90: return "🟡", f" (ideal: {ideal})"
    return "✅", f" (ideal: {ideal})"

# ─── TECLADOS ─────────────────────────────────────────────────────────────────
def teclado_nombres_umacollo() -> ReplyKeyboardMarkup:
    filas = [[KeyboardButton(n)] for n in NOMBRES_UMACOLLO]
    return ReplyKeyboardMarkup(filas, resize_keyboard=True, one_time_keyboard=True)

def teclado_nombres_eu() -> ReplyKeyboardMarkup:
    filas = [[KeyboardButton(n)] for n in NOMBRES_EU]
    return ReplyKeyboardMarkup(filas, resize_keyboard=True, one_time_keyboard=True)

def teclado_sede() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 Umacollo")],
        [KeyboardButton("📍 Av. Estados Unidos")],
    ], resize_keyboard=True, one_time_keyboard=True)

def teclado_productos(nombre: str, reportados: set = None) -> ReplyKeyboardMarkup:
    """Muestra los productos del trabajador. Los ya reportados llevan ✓."""
    reportados = reportados or set()
    prods = [p["nombre"] for p in PRODUCTOS.get(nombre, [])]
    filas = []
    for i in range(0, len(prods), 2):
        fila = []
        for prod in prods[i:i+2]:
            label = f"✓ {prod}" if prod in reportados else prod
            fila.append(KeyboardButton(label))
        filas.append(fila)

    if nombre in ["Ivan", "Ruth"]:
        filas.append([KeyboardButton("💵 Monto inicial efectivo"), KeyboardButton("💵 Monto final efectivo")])

    if nombre in ["Ivan", "Josué", "Josue"]:
        filas.append([KeyboardButton("🍽️ Consumos personal")])

    filas.append([KeyboardButton("📊 Ver stock"), KeyboardButton("✅ Terminé por hoy")])
    return ReplyKeyboardMarkup(filas, resize_keyboard=True)

def teclado_confirmacion(cantidad: str, unidad: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(f"✅ Confirmar {cantidad} {unidad}")],
        [KeyboardButton("❌ Corregir")],
    ], resize_keyboard=True, one_time_keyboard=True)

def teclado_jefa() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔴 Stock crítico"),     KeyboardButton("🛒 Lista de compras")],
        [KeyboardButton("📋 Estado General"),   KeyboardButton("📂 Por Categoría")],
        [KeyboardButton("🔍 Consultar producto"), KeyboardButton("📊 Resumen del día")],
        [KeyboardButton("📍 Por distribuidor"),  KeyboardButton("👤 Por trabajador")],
        [KeyboardButton("🍽️ Histórico Consumos")],
    ], resize_keyboard=True)

# ─── FLUJO DE REGISTRO ────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    usuario = buscar_usuario(user_id)

    if usuario:
        context.user_data["nombre"] = usuario["nombre"]
        context.user_data["rol"]    = usuario["rol"]
        context.user_data["sede"]   = usuario.get("sede")
        context.user_data.setdefault("reportados", set())
        return await bienvenida(update, context)

    # Auto-registro por deep link
    if context.args:
        param  = context.args[0].lower().strip()
        datos  = DEEP_LINK_MAP.get(param)
        if datos:
            nombre, rol, sede = datos
            guardar_usuario(user_id, nombre, rol, sede)
            context.user_data["nombre"]    = nombre
            context.user_data["rol"]       = rol
            context.user_data["sede"]      = sede
            context.user_data["reportados"]= set()
            await update.message.reply_text(
                f"✅ ¡Hola *{nombre}*! Quedaste registrado.\n"
                f"Ya puedes empezar a reportar stock 👇",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            return await bienvenida(update, context)

    # Sin deep link — preguntar sede primero
    await update.message.reply_text(
        "👋 Hola, ¿de qué sede eres?",
        reply_markup=teclado_sede()
    )
    return REGISTRO_NOMBRE

async def registrar_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    # Paso 1: eligió sede
    if texto in ("📍 Umacollo", "📍 Av. Estados Unidos"):
        sede = "Umacollo" if "Umacollo" in texto else "Av. Estados Unidos"
        context.user_data["sede_pendiente"] = sede
        teclado = teclado_nombres_umacollo() if sede == "Umacollo" else teclado_nombres_eu()
        await update.message.reply_text(
            "¿Cuál es tu nombre?",
            reply_markup=teclado
        )
        return REGISTRO_NOMBRE

    # Paso 2: eligió nombre
    sede = context.user_data.get("sede_pendiente")
    nombres_validos = (NOMBRES_UMACOLLO if sede == "Umacollo" else NOMBRES_EU) + [NOMBRE_JEFA]

    if texto not in nombres_validos:
        await update.message.reply_text(
            "Toca tu nombre del teclado 👇",
            reply_markup=teclado_nombres_umacollo() if sede == "Umacollo" else teclado_nombres_eu()
        )
        return REGISTRO_NOMBRE

    rol = "jefa" if texto == NOMBRE_JEFA else "trabajador"
    guardar_usuario(user_id=str(update.effective_user.id),
                    nombre=texto, rol=rol, sede=sede)
    context.user_data["nombre"]     = texto
    context.user_data["rol"]        = rol
    context.user_data["sede"]       = sede
    context.user_data["reportados"] = set()

    await update.message.reply_text(
        f"✅ Registrado como *{texto}*. ¡Listo!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return await bienvenida(update, context)

async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = context.user_data["nombre"]
    rol    = context.user_data["rol"]

    if rol == "admin":
        await update.message.reply_text(
            f"👑 *Hola Admin*, ¿qué sistema quieres usar hoy?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("👑 Vista Jefa")],
                [KeyboardButton("👨‍🔧 Vista Trabajador")]
            ], resize_keyboard=True)
        )
        return ADMIN_MENU

    if rol == "jefa":
        await update.message.reply_text(
            f"Hola Adriana 👋\n¿Qué quieres revisar?",
            reply_markup=teclado_jefa()
        )
        return JEFA_MENU

    # Precargar productos ya reportados hoy desde Sheets (sobrevive reinicios)
    if not context.user_data.get("reportados"):
        sede = context.user_data.get("sede", "Umacollo")
        context.user_data["reportados"] = cargar_reportados_hoy(nombre, sede)

    reportados = context.user_data["reportados"]
    total   = len(PRODUCTOS.get(nombre, []))
    hechos  = len(reportados)
    progreso = f" ({hechos}/{total} ✓)" if hechos > 0 else ""

    await update.message.reply_text(
        f"Hola {nombre} 👋{progreso}\nToca un producto y escribe cuánto hay.",
        reply_markup=teclado_productos(nombre, reportados)
    )
    return ELEGIR_PRODUCTO

# ─── FLUJO TRABAJADOR ─────────────────────────────────────────────────────────
async def elegir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto   = update.message.text
    nombre  = context.user_data.get("nombre")
    reportados = context.user_data.setdefault("reportados", set())

    if texto == "✅ Terminé por hoy":
        total  = len(PRODUCTOS.get(nombre, []))
        hechos = len(reportados)
        faltantes = [p["nombre"] for p in PRODUCTOS.get(nombre, [])
                     if p["nombre"] not in reportados]
        if faltantes and hechos < total:
            lista = "\n".join(f"  • {p}" for p in faltantes)
            await update.message.reply_text(
                f"⚠️ Aún te faltan *{total - hechos}* productos:\n{lista}\n\n"
                f"¿Seguro que terminaste? Toca *✅ Terminé por hoy* otra vez para confirmar.",
                parse_mode="Markdown",
                reply_markup=teclado_productos(nombre, reportados)
            )
            # Marcar que ya se advirtió para no repetir el aviso
            context.user_data["advertido"] = True
            return ELEGIR_PRODUCTO

        await update.message.reply_text(
            f"¡Listo! Gracias 🙌 Reportaste {hechos}/{total} productos.\n"
            f"Escribe /inicio cuando quieras volver.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["reportados"] = set()
        context.user_data["advertido"]  = False
        return ConversationHandler.END

    if texto == "📊 Ver stock":
        await update.message.reply_text(
            "🔍 ¿Qué producto quieres consultar?\nEscribe el nombre (o parte de él):",
            reply_markup=ReplyKeyboardRemove()
        )
        return VER_STOCK

    if "Monto inicial" in texto or "Monto final" in texto:
        context.user_data["caja_tipo"] = "Inicial" if "inicial" in texto.lower() else "Final"
        await update.message.reply_text(
            f"💵 Has seleccionado *Cuadre {context.user_data['caja_tipo']}*.\n"
            f"Por favor, ingresa el monto en efectivo (solo números, ej. 1500.50):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return CAJA_INGRESO

    if "Consumos personal" in texto:
        teclado = ReplyKeyboardMarkup([
            [KeyboardButton("Monto/Dinero"), KeyboardButton("Gaseosa")],
            [KeyboardButton("Plato"), KeyboardButton("Otro")]
        ], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "🍽️ *Consumo Personal*\n¿Qué tipo de consumo se va a registrar?",
            parse_mode="Markdown",
            reply_markup=teclado
        )
        return CONSUMOS_TIPO

    # Limpiar prefijo ✓ si el producto ya fue reportado
    texto_limpio = texto.replace("✓ ", "").strip()
    texto_norm = quitar_tildes(texto_limpio)
    productos    = PRODUCTOS.get(nombre, [])
    prod_obj     = next((p for p in productos if quitar_tildes(p["nombre"]) == texto_norm), None)

    if not prod_obj:
        await update.message.reply_text(
            "Toca un producto del teclado 👇",
            reply_markup=teclado_productos(nombre, reportados)
        )
        return ELEGIR_PRODUCTO

    context.user_data["producto"]  = prod_obj
    context.user_data["advertido"] = False
    hint = "\n_Ej: 1.250 = 1 kg 250 g  ·  0.750 = 750 g_" if prod_obj["unidad"] == "kg" else ""
    await update.message.reply_text(
        f"*{texto_limpio}*\n¿Cuántos {prod_obj['unidad']} hay ahora?{hint}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return INGRESAR_CANTIDAD

async def ingresar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto    = update.message.text.strip().replace(",", ".")
    prod_obj = context.user_data.get("producto")

    try:
        cantidad = float(texto)
        if cantidad < 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Escribe solo el número.\nEjemplo: 3 o 2.5")
        return INGRESAR_CANTIDAD

    context.user_data["cantidad"] = cantidad
    if prod_obj.get("unidad") == "kg" and cantidad != int(cantidad):
        cant_str = f"{round(cantidad, 3):.3f}".rstrip("0")
    else:
        cant_str = str(int(cantidad) if cantidad == int(cantidad) else cantidad)
    await update.message.reply_text(
        f"¿Confirmas?\n*{prod_obj['nombre']}* → {cant_str} {prod_obj['unidad']}",
        parse_mode="Markdown",
        reply_markup=teclado_confirmacion(cant_str, prod_obj["unidad"])
    )
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto    = update.message.text
    nombre   = context.user_data.get("nombre")
    sede     = context.user_data.get("sede", "Umacollo")
    prod_obj = context.user_data.get("producto")
    cantidad = context.user_data.get("cantidad")
    reportados = context.user_data.setdefault("reportados", set())

    if "Corregir" in texto:
        await update.message.reply_text(
            f"*{prod_obj['nombre']}*\n¿Cuántos {prod_obj['unidad']} hay ahora?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return INGRESAR_CANTIDAD

    if "Confirmar" in texto:
        ok, err = registrar_stock(nombre, prod_obj["nombre"], cantidad,
                                  prod_obj["unidad"], prod_obj["distribuidor"], sede)

        # Marcar como reportado
        reportados.add(prod_obj["nombre"])
        context.user_data["reportados"] = reportados

        ideal = STOCK_IDEAL.get(prod_obj["nombre"])
        emoji, ideal_txt = _estado_emoji(cantidad, ideal)

        total  = len(PRODUCTOS.get(nombre, []))
        hechos = len(reportados)
        prog   = f"Progreso: {hechos}/{total} productos ✓"

        msg = f"Guardado ✅{ideal_txt} {emoji}\n{prog}\n\n¿Qué otro producto reportas?"
        if not ok:
            err_short = (err or "desconocido")[:120]
            msg = f"⚠️ Error al guardar:\n`{err_short}`\n\n{prog}\n\n¿Qué otro producto reportas?"

        await update.message.reply_text(
            msg, reply_markup=teclado_productos(nombre, reportados)
        )
        return ELEGIR_PRODUCTO

    await update.message.reply_text(
        "Usa los botones 👇",
        reply_markup=teclado_confirmacion(str(cantidad), prod_obj["unidad"])
    )
    return CONFIRMAR

async def ver_stock_consulta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda   = update.message.text.strip()
    nombre     = context.user_data.get("nombre")
    reportados = context.user_data.get("reportados", set())
    sede       = context.user_data.get("sede")
    if sede:
        sheet_id  = SHEET_ID_EU if sede == "Av. Estados Unidos" else SHEET_ID_UMACOLLO
        registros = obtener_stock_sede(sheet_id, sede, busqueda)
    else:
        registros = obtener_stock_combinado(busqueda)

    if registros:
        msg = f"📦 *{busqueda}:*\n\n"
        for r in registros[:6]:
            ideal = STOCK_IDEAL.get(r["producto"])
            emoji, ideal_txt = _estado_emoji(r["cantidad"], ideal)
            msg += (
                f"{emoji} *{r['sede']}*\n"
                f"  {r['cantidad']} {r['unidad']}"
                f"{ideal_txt}\n"
                f"  {r['persona']} — {r['fecha']} {r['hora']}\n\n"
            )
    else:
        msg = f"❌ No encontré *{busqueda}*.\nRevisa cómo está escrito."

    await update.message.reply_text(
        msg.strip(), parse_mode="Markdown",
        reply_markup=teclado_productos(nombre, reportados)
    )
    return ELEGIR_PRODUCTO

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
        registros = obtener_stock_combinado()
        alertas = {}
        
        for r in registros:
            ideal = STOCK_IDEAL.get(r["producto"])
            if not ideal:
                continue
            try:
                cant = float(r["cantidad"])
            except Exception:
                continue
            
            prod = r["producto"]
            unidad = r["unidad"]
            
            if cant < ideal * 0.90:
                emoji = "🔴" if cant < ideal * 0.50 else "🟡"
                if prod not in alertas: alertas[prod] = {"ideal": ideal, "sedes": []}
                alertas[prod]["sedes"].append(f"    {emoji} 📍 {r['sede']}: {cant} {unidad}")

        if not alertas:
            msg = "✅ Todo el stock está bien en ambas sedes."
        else:
            msg = "🚨 *Stock Crítico y Bajo (Todas las sedes):*\n\n"
            for prod in sorted(alertas.keys()):
                data = alertas[prod]
                msg += f"📦 *{prod}* (Ideal: {data['ideal']})\n" + "\n".join(data["sedes"]) + "\n\n"
                    
        await update.message.reply_text(
            msg.strip() or "✅ Todo bien.", parse_mode="Markdown",
            reply_markup=teclado_jefa()
        )
        return JEFA_MENU

    if texto == "🛒 Lista de compras":
        registros = obtener_stock_combinado()
        por_dist = {}
        for r in registros:
            ideal = STOCK_IDEAL.get(r["producto"])
            if not ideal: continue
            try: cant = float(r["cantidad"])
            except Exception: continue
            
            if cant < ideal * 0.90:
                dist = r["distribuidor"]
                prod = r["producto"]
                falta = round(ideal - cant, 2)
                emoji = "🔴" if cant < ideal * 0.50 else "🟡"
                
                if dist not in por_dist: por_dist[dist] = {}
                if prod not in por_dist[dist]: por_dist[dist][prod] = {"ideal": ideal, "sedes": []}
                
                por_dist[dist][prod]["sedes"].append(f"      {emoji} 📍 {r['sede']}: faltan {falta} {r['unidad']}")
                
        if not por_dist:
            msg = "✅ No hay nada urgente que comprar."
        else:
            msg = "*🛒 Lista de compras por Distribuidor:*\n"
            for dist in sorted(por_dist.keys()):
                msg += f"\n🚚 *{dist}*\n"
                for prod, data in sorted(por_dist[dist].items()):
                    msg += f"  📦 *{prod}* (Ideal: {data['ideal']})\n" + "\n".join(data["sedes"]) + "\n"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "📋 Estado General":
        hoy = get_now().strftime("%d/%m/%Y")
        registros = obtener_stock_combinado()
        hoy_reportados = { (r["persona"], r["producto"]) for r in registros if r.get("fecha") == hoy }
        
        msg = f"📋 *Auditoría de Reportes de Hoy ({hoy})*\n\n"
        for trabajador, prods in PRODUCTOS.items():
            msg += f"👤 *{trabajador}*\n"
            for p in prods:
                prod_name = p["nombre"]
                estado = "✅" if (trabajador, prod_name) in hoy_reportados else "👀"
                msg += f"  {estado} {prod_name}\n"
            msg += "\n"
            
        if len(msg) > 4000:
            partes = msg.split("\n\n")
            mitad = len(partes) // 2
            m1 = "\n\n".join(partes[:mitad])
            m2 = "\n\n".join(partes[mitad:])
            await update.message.reply_text(m1, parse_mode="Markdown")
            await update.message.reply_text(m2, parse_mode="Markdown", reply_markup=teclado_jefa())
        else:
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "📂 Por Categoría":
        teclado = ReplyKeyboardMarkup([
            [KeyboardButton("Plásticos y Empaques"), KeyboardButton("Bebidas")],
            [KeyboardButton("Infusiones"), KeyboardButton("Carnes / Pollos")],
            [KeyboardButton("Verduras"), KeyboardButton("Abarrotes y Otros")],
        ], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("📂 ¿Qué categoría quieres revisar?", reply_markup=teclado)
        return JEFA_CATEGORIA_ELEGIR

    if texto == "🍽️ Histórico Consumos":
        msg = obtener_consumos_semanales()
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "📊 Resumen del día":
        hoy = get_now().strftime("%d/%m/%Y")
        msg = f"📊 *Resumen {hoy}*\n"

        for sede_label, sheet_id in [("Umacollo", SHEET_ID_UMACOLLO),
                                      ("Av. Estados Unidos", SHEET_ID_EU)]:
            if not sheet_id:
                continue
            registros = obtener_stock_sede(sheet_id, sede_label)
            hoy_regs  = [r for r in registros if r.get("fecha") == hoy]
            personas  = {}
            for r in hoy_regs:
                personas[r["persona"]] = personas.get(r["persona"], 0) + 1
            msg += f"\n📍 *{sede_label}*\n"
            if personas:
                for p, n in sorted(personas.items()):
                    msg += f"  • {p}: {n} productos\n"
            else:
                msg += "  Sin reportes hoy\n"

        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "📍 Por distribuidor":
        registros = obtener_stock_combinado()
        por_dist = {}
        for r in registros:
            dist = r["distribuidor"]
            prod = r["producto"]
            if dist not in por_dist: por_dist[dist] = {}
            if prod not in por_dist[dist]: por_dist[dist][prod] = []
            
            ideal = STOCK_IDEAL.get(prod)
            emoji, ideal_txt = _estado_emoji(r["cantidad"], ideal)
            por_dist[dist][prod].append(f"      {emoji} 📍 {r['sede']}: {r['cantidad']} {r['unidad']} {ideal_txt}")
            
        if not por_dist:
            msg = "✅ No hay productos registrados."
        else:
            msg = "📍 *Stock general organizado por distribuidor:*\n"
            for dist in sorted(por_dist.keys()):
                msg += f"\n🚚 *{dist}*\n"
                for prod, sedes in sorted(por_dist[dist].items()):
                    msg += f"  📦 *{prod}*\n" + "\n".join(sedes) + "\n"
                    
        if len(msg) > 4000:
            await update.message.reply_text(msg[:4000], parse_mode="Markdown")
            await update.message.reply_text("...(la lista es más larga)", parse_mode="Markdown", reply_markup=teclado_jefa())
        else:
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU

    if texto == "👤 Por trabajador":
        filas = []
        nombres = sorted(NOMBRES_UMACOLLO + NOMBRES_EU)
        for i in range(0, len(nombres), 3):
            filas.append([KeyboardButton(n) for n in nombres[i:i+3]])
        await update.message.reply_text(
            "👤 Elige al trabajador del cual quieres ver los reportes de HOY:",
            reply_markup=ReplyKeyboardMarkup(filas, resize_keyboard=True)
        )
        return JEFA_TRABAJADOR

    await update.message.reply_text("Usa los botones 👇", reply_markup=teclado_jefa())
    return JEFA_MENU

async def jefa_trabajador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trabajador = update.message.text.strip()
    if trabajador not in NOMBRES_UMACOLLO and trabajador not in NOMBRES_EU:
        await update.message.reply_text("Por favor, usa los botones del teclado.")
        return JEFA_TRABAJADOR
    
    hoy = get_now().strftime("%d/%m/%Y")
    sede_label = SEDE_POR_NOMBRE.get(trabajador)
    sheet_id = SHEET_ID_UMACOLLO if sede_label == "Umacollo" else SHEET_ID_EU

    if not sheet_id:
        await update.message.reply_text("❌ No hay Sheet configurado para esa sede.", reply_markup=teclado_jefa())
        return JEFA_MENU

    registros = obtener_stock_sede(sheet_id, sede_label)
    trabajador_regs = [r for r in registros if r.get("persona") == trabajador]

    if not trabajador_regs:
        await update.message.reply_text(
            f"❌ *{trabajador}* no tiene ningún producto reportado recientemente.",
            parse_mode="Markdown", reply_markup=teclado_jefa()
        )
        return JEFA_MENU

    msg = f"👤 *Últimos reportes de {trabajador}:*\n\n"
    for r in trabajador_regs:
        ideal = STOCK_IDEAL.get(r["producto"])
        emoji, ideal_txt = _estado_emoji(r["cantidad"], ideal)
        msg += f"  {emoji} {r['producto']}: {r['cantidad']} {r['unidad']}{ideal_txt}\n    _({r['fecha']} a las {r['hora']})_\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
    return JEFA_MENU

async def jefa_consulta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda = update.message.text.strip()

    r_uma = obtener_stock_sede(SHEET_ID_UMACOLLO, "Umacollo", busqueda) if SHEET_ID_UMACOLLO else []
    r_eu  = obtener_stock_sede(SHEET_ID_EU, "Av. Estados Unidos", busqueda) if SHEET_ID_EU else []

    if not r_uma and not r_eu:
        await update.message.reply_text(
            f'❌ No encontré "{busqueda}". Revisa cómo está escrito.',
            reply_markup=teclado_jefa()
        )
        return JEFA_MENU

    # Agrupar por nombre de producto
    por_producto: dict = {}
    for r in r_uma + r_eu:
        por_producto.setdefault(r["producto"], []).append(r)

    msg = ""
    for prod, resultados in por_producto.items():
        ideal = STOCK_IDEAL.get(prod)
        msg  += f"*{prod}*\n"
        for r in resultados:
            emoji, ideal_txt = _estado_emoji(r["cantidad"], ideal)
            msg += (
                f"  {emoji} *{r['sede']}*: {r['cantidad']} {r['unidad']}"
                f"{ideal_txt}\n"
                f"     {r['persona']}, {r['fecha']} {r['hora']}\n"
            )
        msg += "\n"

    await update.message.reply_text(
        msg.strip(), parse_mode="Markdown", reply_markup=teclado_jefa()
    )
    return JEFA_MENU

async def jefa_categoria_elegir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_elegida = update.message.text
    registros = obtener_stock_combinado()
    
    agrupado = {}
    for r in registros:
        if _get_categoria(r["producto"]) == cat_elegida:
            prod = r["producto"]
            if prod not in agrupado: agrupado[prod] = {"distribuidor": r["distribuidor"], "sedes": []}
            
            ideal = STOCK_IDEAL.get(prod)
            emoji, ideal_txt = _estado_emoji(r["cantidad"], ideal)
            agrupado[prod]["sedes"].append(f"    {emoji} 📍 {r['sede']}: {r['cantidad']} {r['unidad']}")
            
    if not agrupado:
        await update.message.reply_text(f"❌ No hay productos en la categoría: *{cat_elegida}*", parse_mode="Markdown", reply_markup=teclado_jefa())
        return JEFA_MENU
        
    msg = f"📂 *Categoría: {cat_elegida}*\n\n"
    for prod in sorted(agrupado.keys()):
        data = agrupado[prod]
        msg += f"📦 *{prod}* (🚚 Pedir a: {data['distribuidor']})\n" + "\n".join(data["sedes"]) + "\n\n"
        
    if len(msg) > 4000:
        await update.message.reply_text(msg[:4000], parse_mode="Markdown")
        await update.message.reply_text("...(la lista es más larga, usa consultas específicas si necesitas más info)", reply_markup=teclado_jefa())
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado_jefa())
    return JEFA_MENU

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto == "👑 Vista Jefa":
        context.user_data["rol"] = "jefa"
        context.user_data["nombre"] = NOMBRE_JEFA
        return await bienvenida(update, context)
    if texto == "👨‍🔧 Vista Trabajador":
        await update.message.reply_text("¿De qué sede quieres ver trabajadores?", reply_markup=teclado_sede())
        return ADMIN_SEDE
    return ADMIN_MENU

async def admin_sede(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sede = update.message.text
    if "Umacollo" in sede:
        teclado = teclado_nombres_umacollo()
        context.user_data["sede_pendiente"] = "Umacollo"
    elif "Estados" in sede:
        teclado = teclado_nombres_eu()
        context.user_data["sede_pendiente"] = "Av. Estados Unidos"
    else:
        return ADMIN_SEDE
    await update.message.reply_text("¿A qué trabajador quieres suplantar?", reply_markup=teclado)
    return ADMIN_TRABAJADOR

async def admin_trabajador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trabajador = update.message.text
    context.user_data["rol"] = "trabajador"
    context.user_data["nombre"] = trabajador
    context.user_data["sede"] = context.user_data.get("sede_pendiente")
    return await bienvenida(update, context)

async def caja_ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        monto = float(texto)
    except ValueError:
        await update.message.reply_text("❌ Escribe solo el monto (números). Ej: 1500.50")
        return CAJA_INGRESO
    
    sede = context.user_data.get("sede", "Umacollo")
    cajero = context.user_data.get("nombre")
    tipo = context.user_data.get("caja_tipo")
    
    ok = _guardar_caja(sede, cajero, tipo, monto)
    if ok:
        await update.message.reply_text(f"✅ Guardado: Cuadre {tipo} por S/ {monto:.2f}.")
    else:
        await update.message.reply_text("❌ Error al guardar caja en Google Sheets.")
    return await bienvenida(update, context)

async def consumos_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = update.message.text.strip()
    context.user_data["consumo_tipo"] = tipo
    
    filas = []
    nombres = sorted(NOMBRES_TRABAJADORES)
    for i in range(0, len(nombres), 3):
        filas.append([KeyboardButton(n) for n in nombres[i:i+3]])
    
    await update.message.reply_text(
        "¿Quién consumió?",
        reply_markup=ReplyKeyboardMarkup(filas, resize_keyboard=True)
    )
    return CONSUMOS_PERSONAL

async def consumos_personal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consumidor = update.message.text.strip()
    context.user_data["consumo_persona"] = consumidor
    await update.message.reply_text(
        "Ingresa la cantidad, monto o detalle (ej. '1 Coca Cola' o '15.50'):",
        reply_markup=ReplyKeyboardRemove()
    )
    return CONSUMOS_MONTO

async def consumos_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    detalle = update.message.text.strip()
    sede = context.user_data.get("sede", "Umacollo")
    registrador = context.user_data.get("nombre")
    consumidor = context.user_data.get("consumo_persona")
    tipo = context.user_data.get("consumo_tipo")
    
    ok = _guardar_consumo(sede, registrador, consumidor, tipo, detalle)
    if ok:
        await update.message.reply_text(f"✅ Consumo guardado: {consumidor} ({tipo} - {detalle})")
    else:
        await update.message.reply_text("❌ Error al guardar el consumo en Google Sheets.")
    return await bienvenida(update, context)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Saliste. Escribe /inicio para volver.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def recordatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    hoy = get_now().strftime("%d/%m/%Y")
    registros = obtener_stock_combinado()
    hoy_reportados = { (r["persona"], r["producto"]) for r in registros if r.get("fecha") == hoy }
    
    msg_jefa = f"⏰ *Reporte de Cierre de Jornada ({hoy} - 9:00 PM)*\n\n"
    usuarios = cargar_usuarios()
    nombre_to_id = {u["nombre"]: uid for uid, u in usuarios.items() if u["rol"] == "trabajador"}
    jefa_id = "1427645515" 
    
    for trabajador, prods in PRODUCTOS.items():
        faltantes = []
        hechos = 0
        total = len(prods)
        for p in prods:
            if (trabajador, p["nombre"]) in hoy_reportados:
                hechos += 1
            else:
                faltantes.append(p["nombre"])
                
        if faltantes:
            msg_jefa += f"👤 *{trabajador}*: Llenó {hechos}/{total}.\n  ⚠️ Faltan: {', '.join(faltantes)}\n\n"
        else:
            msg_jefa += f"👤 *{trabajador}*: Completó TODO ({hechos}/{total}) ✅\n\n"
            
        if faltantes and trabajador in nombre_to_id:
            msg_worker = f"⚠️ *Recordatorio de Cierre*\nHola {trabajador}, aún te faltan {len(faltantes)} productos por reportar hoy:\n- " + "\n- ".join(faltantes) + "\n\n¡Entra a /inicio y repórtalos!"
            try:
                await context.bot.send_message(chat_id=nombre_to_id[trabajador], text=msg_worker, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error mandando recordatorio a {trabajador}: {e}")
                
    try:
        await context.bot.send_message(chat_id=jefa_id, text=msg_jefa, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error mandando resumen a la Jefa: {e}")

async def reporte_semanal_consumos(context: ContextTypes.DEFAULT_TYPE):
    msg = obtener_consumos_semanales()
    jefa_id = "1427645515" 
    try:
        await context.bot.send_message(chat_id=jefa_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error mandando reporte semanal consumos a la Jefa: {e}")

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
            REGISTRO_NOMBRE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_nombre)],
            ELEGIR_PRODUCTO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_producto)],
            INGRESAR_CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cantidad)],
            CONFIRMAR:         [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
            JEFA_MENU:         [MessageHandler(filters.TEXT & ~filters.COMMAND, jefa_menu)],
            JEFA_CONSULTA:     [MessageHandler(filters.TEXT & ~filters.COMMAND, jefa_consulta)],
            VER_STOCK:         [MessageHandler(filters.TEXT & ~filters.COMMAND, ver_stock_consulta)],
            ADMIN_MENU:        [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu)],
            ADMIN_SEDE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sede)],
            ADMIN_TRABAJADOR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_trabajador)],
            JEFA_TRABAJADOR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, jefa_trabajador)],
            CAJA_INGRESO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, caja_ingreso)],
            CONSUMOS_TIPO:     [MessageHandler(filters.TEXT & ~filters.COMMAND, consumos_tipo)],
            CONSUMOS_PERSONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, consumos_personal)],
            CONSUMOS_MONTO:    [MessageHandler(filters.TEXT & ~filters.COMMAND, consumos_monto)],
            JEFA_CATEGORIA_ELEGIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, jefa_categoria_elegir)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    
    t = time(hour=21, minute=0, tzinfo=pytz.timezone('America/Lima'))
    app.job_queue.run_daily(recordatorio_diario, t)
    
    t_domingo = time(hour=20, minute=0, tzinfo=pytz.timezone('America/Lima'))
    app.job_queue.run_daily(reporte_semanal_consumos, t_domingo, days=(6,))
    
    logger.info("Bot iniciado ✅ — Umacollo + Av. Estados Unidos (con tareas a las 9 PM)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
