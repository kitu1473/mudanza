'''
Ayuda para configurar el bot de Telegram.

  python scripts/telegram_setup.py <TOKEN>          # verifica el token y lista los chats
  python scripts/telegram_setup.py <TOKEN> --test <CHAT_ID>   # manda un mensaje de prueba

Antes: crear el bot con @BotFather (/newbot), agregarlo al grupo (o escribirle
al bot) y mandar un mensaje cualquiera, para que aparezca el chat.
'''
import sys

import requests

API = 'https://api.telegram.org/bot{}/{}'


def call(token, method, **params):
    res = requests.post(API.format(token, method), data=params, timeout=15)
    data = res.json()
    if not data.get('ok'):
        sys.exit(f'Error de Telegram: {data.get("description")}')
    return data['result']


def main(argv):
    if not argv:
        sys.exit(__doc__)
    token = argv[0]
    me = call(token, 'getMe')
    print(f'Token OK: @{me["username"]}')

    if '--test' in argv:
        chat_id = argv[argv.index('--test') + 1]
        call(token, 'sendMessage', chat_id=chat_id, text='Mudanza bot: mensaje de prueba ✅')
        print('Mensaje de prueba enviado.')
        return

    chats = {}
    for update in call(token, 'getUpdates'):
        msg = update.get('message') or update.get('channel_post') or {}
        chat = msg.get('chat')
        if chat:
            chats[chat['id']] = chat.get('title') or chat.get('username') or chat.get('first_name')
    if not chats:
        print('No hay chats todavía: mandale un mensaje al bot (o al grupo) y reintentá.')
    for chat_id, name in chats.items():
        print(f'chat_room: {chat_id}   ({name})')


if __name__ == '__main__':
    main(sys.argv[1:])
