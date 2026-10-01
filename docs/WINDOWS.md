# Correr el bot en Windows (todo desde la PC)

Una sola vez:

1. Instalar Python desde https://www.python.org/downloads/ (tildar **Add python.exe to PATH**).
2. Descomprimir el proyecto en una carpeta (por ejemplo `E:\BotMudanza`).
3. Doble clic en `instalar.bat`. Crea el entorno, instala todo y copia `config.example.yaml` a `config.yaml`.
4. Abrir `config.yaml` con el Bloc de notas y completar `bot_token` y `chat_room` (ver `docs/TELEGRAM.md`). `config.yaml` queda solo en tu PC: no se sube a GitHub.

Cada vez que quieras buscar: doble clic en `correr.bat`.

- Hasta `live_from` (2026-10-13) corre en **dry run**: busca y muestra los mensajes en pantalla, pero no manda nada a Telegram.
- Para empezar de verdad: poné `dry_run: false` en `config.yaml`. Primera vez: `pages: 15` (trae todo lo que hay; son cientos de mensajes). Después `pages: 3`.
- La base de avisos ya enviados es `scrapdep.db` en esa carpeta: no la borres, o se vuelven a mandar todos.
- El mapa se genera como `mapa.html` en la misma carpeta (doble clic para abrirlo).
