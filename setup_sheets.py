"""
Ejecuta este script UNA SOLA VEZ para crear las hojas del Google Sheet.
"""
import os, json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def setup():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    client = gspread.authorize(creds)
    wb = client.open_by_key(os.environ.get("GOOGLE_SHEET_ID"))

    # Hoja principal de registros
    try:
        hoja = wb.worksheet("Registros")
        print("Hoja 'Registros' ya existe")
    except gspread.WorksheetNotFound:
        hoja = wb.add_worksheet("Registros", rows=5000, cols=8)
        hoja.append_row(["Fecha", "Hora", "Persona", "Producto", "Cantidad", "Unidad", "Distribuidor"])
        print("Hoja 'Registros' creada")

    # Hojas individuales por persona
    personas = ["Milagros", "Ruth", "Miguel", "Josué", "Mozo 1", "Dashboard"]
    for nombre in personas:
        try:
            wb.worksheet(nombre)
            print(f"Hoja '{nombre}' ya existe")
        except gspread.WorksheetNotFound:
            wb.add_worksheet(nombre, rows=100, cols=5)
            print(f"Hoja '{nombre}' creada")

    print("\n✅ Google Sheet listo.")

if __name__ == "__main__":
    setup()
