---
name: gallina-contexto
description: >
  Use when working on the La Gallina de Lucio stock bot project.
  Provides project context, architecture, and constraints.
  Do not use for generic Python or Telegram questions.
---

# Gallina de Lucio — Contexto del Proyecto

## Stack
- Python 3.11.9 + python-telegram-bot + gspread
- Deploy: Railway (auto-deploy desde git push)
- Bot: @Stock_gallina_bot

## Trabajadores → Nombres en el bot
- Milagros (link: ?start=milagros)
- Ruth / Helfert (link: ?start=ruth)
- Miguel / Feller (link: ?start=miguel)
- Josué / Diego (link: ?start=josue)
- Adriana — jefa, ID: 7234166162 (link: ?start=adriana)

## Google Sheets
Hoja "Registros": Fecha | Hora | Responsable | Producto | Cantidad | Unidad | Distribuidor | Días repos.

## Reglas de negocio
- Crítico = < 30% del stock ideal → 🔴
- Bajo = 30–70% → 🟡
- OK = > 70% → ✅
- Días reposición: 0=HOY (aves) | 1=mañana (verduras) | 2=bebidas/secos | 3=empaques/limpieza
