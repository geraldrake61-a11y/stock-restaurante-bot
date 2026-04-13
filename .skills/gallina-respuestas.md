---
name: gallina-respuestas
description: >
  Use for ALL responses in this project. Controls response format and token usage.
  Always active. Do not skip.
---

# Reglas de Respuesta — Proyecto Gallina

## Formato
- Respuestas cortas. Sin relleno.
- Si es código: muestra solo el bloque modificado, no el archivo entero
- Si son instrucciones: máximo 5 pasos numerados
- Sin frases como "¡Claro!", "Por supuesto", "Excelente pregunta"
- Sin repetir lo que el usuario ya dijo

## Al mostrar código
- Solo el fragmento relevante + comentario de dónde va
- Si el cambio es < 10 líneas, no regeneres el archivo completo
- Usa `# ... resto igual ...` para omitir partes sin cambios

## Confirmaciones
- Después de hacer un cambio: 1 línea confirmando qué hiciste
- Sin explicar lo obvio

## Errores
- Si algo falla: causa probable + solución en 2 líneas máximo
