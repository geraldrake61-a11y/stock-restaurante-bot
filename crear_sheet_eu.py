"""
crear_sheet_eu.py
=================
Crea y formatea el Google Sheet para la sede Av. Estados Unidos.
Al terminar imprime el SHEET_ID que hay que agregar en Railway.
"""
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

try:
    from gspread_formatting import set_frozen, set_column_width
    HAS_FORMATTING = True
except ImportError:
    HAS_FORMATTING = False

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TRABAJADORES_EU = [
    "Carlos", "Flor", "Danitza", "María Vargas",
    "Brendali", "Jimena", "Sebastian", "Ivan", "Lionel",
]

STOCK_IDEAL_EU = {
    "Papa": 2, "Kion": 6, "Fideo": 12, "Zanahoria": 6, "Huevos": 18,
    "Gallinas llegada": 50, "Pollos llegada": 10,
    "Gallinas congeladas": 50, "Pollos congelados": 10,
    "Apio": 5, "Poro": 5, "Mallas": 2, "Sal": 12,
    "Botellas litro": 30, "Botellas pequeñas": 100,
    "Fórmula gallinas": 5, "Fórmula pollos": 3,
    "Gallinas cierre": 30, "Pollos cierre": 5,
    "Tuppers litro": 3, "Tuppers medio litro": 3,
    "Conteo papas jornada": 200, "Huevos jornada": 200,
    "Guantes blancos M": 3, "Tocas": 30,
    "Masa de yucas": 20, "Pan rústico": 100, "Mantequilla": 0.5,
    "Ajo": 2, "Cebolla": 10, "Aceite": 20, "Harina": 10,
    "Anís": 0.5, "Orégano": 0.5, "Polvo de hornear": 0.5,
    "Levadura": 0.5, "Café": 1, "Azúcar": 10,
    "Clavo de olor": 0.2, "Comino molido": 0.5, "Comino entero": 0.5,
    "Canela entera": 0.3, "Té natural": 3, "Orégano seco": 0.5,
    "Ají panca color": 2, "Ají panca sabor": 2, "Pan seco": 5,
    "Inf. Té": 3, "Inf. Anís": 3, "Inf. Cedrón": 3, "Inf. Muña": 3,
    "Inf. Flor de Jamaica": 3, "Inf. Boldo": 3,
    "Bolsitas toppings": 5, "Bolsitas toppings grandes": 5,
    "Tuppers cebolla china": 3, "Rocoto": 4, "Cebolla china": 1,
    "Limón": 1, "Canchita": 9, "Ají limo": 0.5,
    "Bolsas cubiertos": 5, "Bolsas Rappi": 5, "Cucharas plástico": 5,
    "Bolsas chismosas N°19": 5, "Bolsas tupper": 3, "Grapas": 2,
    "Trapos de mesa": 20, "Poet": 5, "Limpia mesas": 5,
    "Cloro": 5, "Mondadientes": 500, "Tissues": 5,
    "Coca-Cola": 24, "Inca-Cola": 24, "Fanta": 24, "Sprite": 24,
    "Pepsi": 24, "Bolsas escocesas": 50, "Agua San Luis": 12,
    "Agua Cielo": 12, "Rollos impresora": 5,
    "Gallinas jornada": 50,
    "Chicha morada": 10, "Emoliente": 10,
    "Chicha de jora": 10, "Jugo de maracuyá": 10,
}

def get_client():
    with open("credentials.json") as f:
        info = json.load(f)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def setup_registros(ss):
    print("  📄 Configurando hoja Registros...")
    hoja = ss.worksheet("Registros")
    hoja.clear()
    hoy = datetime.now().strftime("%d/%m/%Y")

    cabecera = [
        ["🐔  LA GALLINA DE LUCIO — AV. ESTADOS UNIDOS — REGISTRO DE STOCK"],
        [f"Actualizado automáticamente vía bot de Telegram  |  {hoy}"],
        [],
        ["Fecha", "Hora", "Responsable", "Producto",
         "Stock Actual", "Unidad", "Distribuidor", "Stock Ideal"],
    ]
    hoja.update(values=cabecera, range_name="A1")

    if HAS_FORMATTING:
        set_frozen(hoja, rows=4, cols=1)
        set_column_width(hoja, "A", 100)
        set_column_width(hoja, "B", 60)
        set_column_width(hoja, "C", 110)
        set_column_width(hoja, "D", 180)
        set_column_width(hoja, "E", 90)
        set_column_width(hoja, "F", 90)
        set_column_width(hoja, "G", 140)
        set_column_width(hoja, "H", 90)

def setup_dashboard(ss):
    print("  📊 Configurando Dashboard...")
    try:
        hoja = ss.worksheet("📊 Dashboard")
    except Exception:
        hoja = ss.add_worksheet("📊 Dashboard", rows=200, cols=9)
    hoja.clear()
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    titulo = [
        ["🐔  DASHBOARD — LA GALLINA DE LUCIO — AV. ESTADOS UNIDOS"],
        [f"Vista en tiempo real — {hoy}"],
        [],
        ["LEYENDA:", "🔴 CRÍTICO (< 50%)", "🟡 BAJO (50–90%)", "✅ OK (≥ 90%)", "", "", "", ""],
        [],
        ["Responsable", "Producto", "Unidad", "Stock Actual",
         "Stock Ideal", "% Stock", "Estado", "Última actualización"],
    ]
    hoja.update(values=titulo, range_name="A1")

    if HAS_FORMATTING:
        set_frozen(hoja, rows=6, cols=1)
        set_column_width(hoja, "A", 110)
        set_column_width(hoja, "B", 180)
        set_column_width(hoja, "C", 90)
        set_column_width(hoja, "D", 90)
        set_column_width(hoja, "E", 90)
        set_column_width(hoja, "F", 70)
        set_column_width(hoja, "G", 100)
        set_column_width(hoja, "H", 160)

def setup_worker_sheet(ss, nombre):
    try:
        hoja = ss.worksheet(nombre)
    except Exception:
        hoja = ss.add_worksheet(nombre, rows=100, cols=2)
    hoja.clear()
    hoja.update(values=[
        [f"🐔 {nombre.upper()} — Mis productos"],
        ["Cuando reporten, sus datos aparecerán en la hoja Registros."],
    ], range_name="A1")

def main():
    print("=" * 55)
    print("  🏗️  CREAR SHEET — AV. ESTADOS UNIDOS")
    print("=" * 55)

    client = get_client()
    sheet_id = "1vTj9mR4y1zfjyhbjA7M4OBHlUQ_8lK3TjXLR7T-Ptd0"

    print(f"\n📡 Conectando al Sheet existente ({sheet_id})...")
    ss = client.open_by_key(sheet_id)
    print(f"  ✅ Conectado: {ss.title}")

    # Renombrar hoja por defecto
    default = ss.sheet1
    default.update_title("Registros")

    setup_registros(ss)

    # Crear hojas por trabajador
    print("  👥 Creando hojas por trabajador...")
    for nombre in TRABAJADORES_EU:
        setup_worker_sheet(ss, nombre)
        print(f"    ✓ {nombre}")

    setup_dashboard(ss)

    print(f"""
{'='*55}
✅ ¡Sheet creado exitosamente!

🔗 URL: https://docs.google.com/spreadsheets/d/{sheet_id}

⚙️  PRÓXIMO PASO — Agrega esta variable en Railway:
    GOOGLE_SHEET_ID_EU = {sheet_id}

Railway → tu proyecto → Variables → Nueva variable
{'='*55}
""")

if __name__ == "__main__":
    main()
