from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
from datetime import datetime

SAVE_DIR = "/mnt/truenas-bot"
os.makedirs(SAVE_DIR, exist_ok=True)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Benvenuto! Il bot è attivo.\nQuesto bot è per il mio uso personale e potrebbe non funzionare per altri utenti.')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    await file.download_to_drive(filename)
    await update.message.reply_text("Foto ricevuta!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video = update.message.video
    file = await context.bot.get_file(video.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    await file.download_to_drive(filename)
    await update.message.reply_text("Video ricevuto!")

app = ApplicationBuilder().token("7564134479:AAHKqBkapm75YYJoYRBzS1NLFQskmbC-LcY").build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))

app.run_polling()

