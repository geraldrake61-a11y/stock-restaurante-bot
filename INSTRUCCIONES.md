# Sistema de Stock — Instrucciones de instalación

## Paso 1 — Crear el bot en Telegram (5 min)
1. Abre Telegram y busca @BotFather
2. Escribe /newbot
3. Ponle nombre: "Stock Restaurante"
4. Ponle usuario: cualquier nombre que termine en _bot
5. Copia el TOKEN que te da

## Paso 2 — Crear Google Service Account (10 min)
1. Ve a https://console.cloud.google.com
2. Crea un proyecto nuevo (ej: "stock-restaurante")
3. Activa "Google Sheets API" y "Google Drive API"
4. Ve a Credenciales → Crear credencial → Cuenta de servicio
5. Descarga el archivo JSON
6. Abre tu Google Sheet → Compartir → pega el email de la cuenta de servicio (editor)

## Paso 3 — Obtener los IDs de Telegram de cada persona
1. Cada persona escribe /start al bot @userinfobot en Telegram
2. El bot les responde con su ID numérico
3. Rellena los IDs en bot.py en la sección USUARIOS

## Paso 4 — Deploy en Railway (gratis, 5 min)
1. Ve a https://railway.app y crea cuenta con GitHub
2. New Project → Deploy from GitHub repo
3. En Variables agrega:
   - TELEGRAM_BOT_TOKEN = (el token del paso 1)
   - GOOGLE_SHEET_ID = (el ID de tu sheet)
   - GOOGLE_CREDENTIALS_JSON = (el contenido del JSON del paso 2)
4. Deploy — Railway lo arranca solo

## Paso 5 — Primer uso
1. Cada trabajador busca el bot por su nombre en Telegram
2. Toca START o escribe /inicio
3. Ven sus productos con botones — solo tocan y escriben el número

## Comandos del bot
- /inicio — Empieza a reportar
- /cancelar — Sale del bot

## ¿Algo no funciona?
Escríbele a quien configuró el bot con una captura de pantalla del error.
