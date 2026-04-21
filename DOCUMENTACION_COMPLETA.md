# Documentación Completa del Bot de Stock - La Gallina de Lucio 🐔

Este archivo contiene toda la información necesaria para entender, administrar y desplegar el Bot de Stock sin tener que revisar todo el código.

---

## 🏗️ 1. Arquitectura y Archivos Clave

El proyecto está diseñado para recibir reportes de los trabajadores por Telegram y escribirlos automáticamente en Google Sheets (uno por cada sede).

- **`bot.py`**: Es el cerebro del bot. Aquí están todos los flujos de conversación, teclados, productos, listas de stock ideal y conexión a Telegram y Sheets.
- **`credentials.json`**: Contiene la llave privada de la "Cuenta de Servicio" de Google. Es el pase de entrada para que el código pueda modificar los archivos de Google Sheets de manera invisible.
- **`usuarios_registrados.json`**: Copia de seguridad local de la gente registrada. *(Nota: La fuente oficial y persistente de usuarios ahora vive dentro del propio Google Sheet, en la pestaña "Usuarios").*

---

## 🔑 2. Credenciales y Variables de Entorno

Estas tres variables deben existir sí o sí en el servidor (Railway) para que el bot funcione. Si cambias de cuenta o de hojas, deberás actualizarlas en el panel de **Variables** de tu proyecto en `railway.app`.

### A. Telegram Bot Token (`TELEGRAM_BOT_TOKEN`)
*Lo consigues hablando con @BotFather en Telegram.*
Reemplázalo en Railway cada vez que cambies de bot.

### B. IDs de Google Sheets (`GOOGLE_SHEET_ID` y `GOOGLE_SHEET_ID_EU`)
*Cada sede tiene su propia hoja de cálculo.* El ID es la cadena larga que aparece en la barra de direcciones (URL) cuando abres la hoja de cálculo.
- **Sede Umacollo (`GOOGLE_SHEET_ID`)**: Es el ID de la hoja principal manejada por Adriana.
- **Sede Estados Unidos (`GOOGLE_SHEET_ID_EU`)**: `1vTj9mR4y1zfjyhbjA7M4OBHlUQ_8lK3TjXLR7T-Ptd0`

### C. Pasaporte de Google Sheets (`GOOGLE_CREDENTIALS_JSON`)
Es el archivo que permite escribir en tus hojas. **OJO: Es crítico que el correo `bot-restaurante3@restaurante-bot-3.iam.gserviceaccount.com` esté agregado como "Editor" en todos los Google Sheets que uses.**

Aquí tienes la credencial exacta que está funcionando hoy. *(Para ponerlo en Railway, copia todo este bloque tal cual está, desde la primera `{` hasta la última `}`)*:

El archivo original que descargaste. No lo subas a internet para que nadie pueda borrar tus reportes. Si deseas obtenerlo de nuevo consiguelo en la zona Segura de la Jefa.

---

## 👩‍💻 3. Acceso Especial de Administrador Supremo

El dueño o supervisor tiene acceso total gracias a la integración en el código.
Tu ID de Telegram personal (`1427645515`) está configurado como *"Modo Dios"*. 

**Para usarlo:**
1. Abre tu bot en Telegram.
2. Escribe directamente el comando `/inicio`.
3. Automáticamente aparecerán dos opciones:
    - **[👑 Vista Jefa]**: Actúas como Adriana. Ves la lista de compras, el stock crítico, consultas de productos y puedes filtrar `"👤 Por trabajador"`.
    - **[👨‍🔧 Vista Trabajador]**: Suplantas a cualquier trabajador. Eliges la sede, luego su nombre, y verás sus productos para poder hacer modificaciones o reportes a nombre suyo, incluso Cuadres de Caja (si haces clic en Iván/Ruth) o Consumos (si haces clic en Josué/Iván).

Toda la base de datos se guarda en la nube para que, una vez registrado alguien y reportado un stock, la información **jamás** se pierda tras implementar código nuevo.

---

## ✏️ 4. ¿Cómo agregar un Producto o Trabajador nuevo?

Todo se gestiona directamente abriendo el archivo `bot.py` desde VSCode:

- **Para nuevos trabajadores:**
  Busca las variables `NOMBRES_UMACOLLO` o `NOMBRES_EU` y añade el nombre en comillas. Luego asegúrate de crearle un bloque con sus productos en el diccionario principal llamado `PRODUCTOS = { ... }`.
  
- **Para nuevos productos:**
  Busca al trabajador responsable en el diccionario de `PRODUCTOS = { ... }` en el archivo `bot.py` y agrega su línea. Ejemplo:
  `{"nombre": "Sal", "unidad": "kg", "distribuidor": "Alicorp"}`

- **Stock Ideal (¡Muy Importante!):**
  En `bot.py` existe un diccionario enorme llamado `STOCK_IDEAL`. Si creas un nuevo producto, o quieres que el bot le diga a Adriana que debe comprar más, **debes añadirle un valor numérico aquí**. Si no está en `STOCK_IDEAL`, el bot lo registrará pero nunca mandará "alertas críticas" por él.

---

## 🚀 5. ¿Cómo actualizar el Bot en Internet (Deploy)?

El código no se sube a internet usando comandos de servidor complejos. Sólo necesitas hacer lo siguiente desde tu terminal de VScode (`MacBook`):

1. Haces los cambios en el archivo que necesites (usualmente `bot.py`).
2. Vas a tu consola y digitas los comandos clásicos de GitHub:
   ```bash
   git add .
   git commit -m "Descripción de lo que arreglé o agregué"
   git push origin main
   ```
3. Apenas haces el `push`, el sistema en la nube (Railway) detecta el cambio, apaga el bot un momento, y en 30 segundos despliega tu nuevo código de manera 100% automática y transparente. No tienes que tocar ni entrar a nada más.

¡Listo! Con esto manejas todo el ecosistema de la Gallina de Lucio. 🐔📈
