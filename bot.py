from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
from datetime import datetime
import re
import requests
import asyncpraw

SAVE_DIR = "/mnt/truenas-bot"
os.makedirs(SAVE_DIR, exist_ok=True)

# Configurazione AsyncPRAW (inserisci le tue credenziali Reddit)
areddit = asyncpraw.Reddit(
    client_id="zwBi1I4DMCFI0QM_meFqJQ",
    client_secret="1x-jhTKVAyGAJ79ztZwaYab-c7JJLQ",
    user_agent="telegram-bot-reddit"
)

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

async def handle_reddit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    reddit_pattern = r"https?://(www\.)?reddit\.com/r/[\w\d_]+/(comments/[\w\d]+/[\w\d_]+|s/[\w\d]+)"
    match = re.search(reddit_pattern, text)
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link Reddit valido.")
        return
    try:
        url = match.group(0)
        # Se è un link short (/s/...), risolvi il redirect
        if "/s/" in url:
            resp = requests.get(url, allow_redirects=True, timeout=10)
            url = resp.url
        submission = await areddit.submission(url=url)
        author = submission.author.name if submission.author else "unknown"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Gestione galleria immagini
        if hasattr(submission, 'is_gallery') and submission.is_gallery:
            for idx, item in enumerate(submission.gallery_data['items']):
                media_id = item['media_id']
                media_url = submission.media_metadata[media_id]['s']['u']
                ext = os.path.splitext(media_url)[1].split('?')[0]
                filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}_{idx}{ext}"
                r = requests.get(media_url, timeout=20)
                with open(filename, 'wb') as f:
                    f.write(r.content)
            await update.message.reply_text(f"{len(submission.gallery_data['items'])} immagini Reddit salvate!")
        # Gestione immagini singole
        elif hasattr(submission, 'post_hint') and submission.post_hint == 'image':
            media_url = submission.url
            ext = os.path.splitext(media_url)[1]
            filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}{ext}"
            r = requests.get(media_url, timeout=20)
            with open(filename, 'wb') as f:
                f.write(r.content)
            await update.message.reply_text(f"Immagine Reddit salvata come {os.path.basename(filename)}!")
        # Gestione video
        elif hasattr(submission, 'is_video') and submission.is_video and submission.media:
            media_url = submission.media['reddit_video']['fallback_url']
            ext = ".mp4"
            filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}{ext}"
            r = requests.get(media_url, timeout=20)
            with open(filename, 'wb') as f:
                f.write(r.content)
            await update.message.reply_text(f"Video Reddit salvato come {os.path.basename(filename)}!")
        else:
            hint = getattr(submission, 'post_hint', 'N/A')
            is_video = getattr(submission, 'is_video', 'N/A')
            await update.message.reply_text(f"Questo post Reddit non contiene immagini o video scaricabili.\npost_hint: {hint}, is_video: {is_video}")
    except Exception as e:
        await update.message.reply_text("Errore durante il download del contenuto Reddit.")

app = ApplicationBuilder().token("7564134479:AAHKqBkapm75YYJoYRBzS1NLFQskmbC-LcY").build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reddit_link))

app.run_polling()

