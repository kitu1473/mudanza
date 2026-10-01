# Bot de Telegram

1. En Telegram, hablar con **@BotFather** → `/newbot` → elegir nombre y usuario. Guarda el **token**.
2. Crear un grupo (o usar el chat directo con el bot), agregar el bot y mandar cualquier mensaje.
3. Obtener el chat id:
   ```bash
   python scripts/telegram_setup.py <TOKEN>
   ```
   Imprime `chat_room: -100123...`. (Los grupos tienen id negativo.)
4. Probar el envío:
   ```bash
   python scripts/telegram_setup.py <TOKEN> --test <CHAT_ID>
   ```
5. Guardar en GitHub: *Settings → Secrets and variables → Actions* → `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
   Para uso local: `export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...` (nunca en archivos commiteados).

# Mapa

Cada corrida geocodifica los avisos nuevos (Nominatim/OpenStreetMap, ~1 por segundo, máx. `geocode_limit` por corrida) y regenera `mapa.html` (Leaflet). Se baja como artifact `mapa` de la corrida de Actions y también queda en la rama `bot-state`.

- Naranja = aviso con ⭐ (aire / cochera / dueño directo). Círculo punteado = ubicación aproximada (solo barrio).
- Sale del mapa un aviso no visto hace más de `map_max_age_days` días, o cuya URL esté en `descartados.txt`.
- Limitación: con `pages: 3` solo se ven los avisos más nuevos, así que uno viejo pero vigente sale del mapa tras ese plazo. Subir `map_max_age_days` si pasa.
