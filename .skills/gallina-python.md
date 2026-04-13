---
name: gallina-python
description: >
  Use when writing or editing Python code for the Gallina de Lucio bot.
  Applies coding standards for bot.py, gspread scripts, and Railway deploys.
  Do not use for frontend, JS, or non-Python tasks.
---

# Python Standards — Gallina Bot

## Estilo
- Funciones cortas, sin comentarios obvios
- Variables en español (igual que el código existente)
- Sin prints de debug en producción

## Patrones del proyecto
- get_sheet() → siempre envuelto en try/except
- urgencia_reposicion(producto, cantidad, ideal) → retorna dict con nivel/emoji/cuando
- DIAS_REPOSICION dict → fuente de verdad para urgencia
- Registrar siempre 8 columnas en Sheets (incluye días_reposicion)

## Railway deploy
- git push origin main → deploy automático
- Variables de entorno: TELEGRAM_BOT_TOKEN, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID
