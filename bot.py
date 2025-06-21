from telegram.ext import Updater, MessageHandler, Filters
import os
from datetime import datetime

# === CONFIGURA QUI ===
TOKEN = 'inserisci_il_tuo_token_telegram'  # Sostituisci con il token del tuo bot
SAVE_DIR = '/mnt/truenas_share'  # Punto di mount della condivisione TrueNAS

def handle_message(update, context):
    text = update.message.text
    user = update.message.from_user.username or update.message.from_user.id
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    filename = f"{user}_{timestamp}.txt"
    filepath = os.path.join(SAVE_DIR, filename)

    with open(filepath, 'w') as f:
        f.write(text)

    update.message.reply_text("Messaggio salvato.")

updater = Updater(TOKEN)
dp = updater.dispatcher
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
updater.start_polling()
updater.idle()
