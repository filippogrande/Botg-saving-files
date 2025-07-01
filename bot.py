from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
from datetime import datetime
import re
import requests
import asyncpraw
from redgifs_helper import download_redgifs_profile, download_redgifs_auto
import reddit_helper  # <--- aggiunto per gestire i profili Reddit

# Importazione condizionale per Mega (per evitare errori se la libreria non è disponibile)
try:
    from mega_helper import download_mega_auto, is_mega_link
    MEGA_AVAILABLE = True
except ImportError as e:
    print(f"Mega helper non disponibile: {e}")
    MEGA_AVAILABLE = False
    
    # Funzioni placeholder
    def download_mega_auto(*args, **kwargs):
        return []
    
    def is_mega_link(url):
        return False

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

async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    animation = update.message.animation
    file = await context.bot.get_file(animation.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    await file.download_to_drive(filename)
    await update.message.reply_text("GIF animata salvata come mp4!")

async def handle_reddit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Regex molto permissiva: basta che ci sia reddit.com o i.redd.it ovunque nel testo
    reddit_pattern = r"(reddit\.com|i\.redd\.it)"
    if not re.search(reddit_pattern, text, re.IGNORECASE):
        await update.message.reply_text("Non ho riconosciuto un link Reddit valido.")
        return
    await update.message.reply_text("Inizio il download dal link Reddit... (potrebbe volerci un po')")
    try:
        result = await reddit_helper.download_reddit_auto(text, SAVE_DIR)
        if isinstance(result, list):
            if result:
                await update.message.reply_text(f"Download completato! File salvati: {len(result)}")
            else:
                await update.message.reply_text("Nessun media scaricabile trovato nel link Reddit.")
        else:
            await update.message.reply_text(f"Errore durante il download dal link Reddit: {result}")
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download dal link Reddit: {str(e)}")

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_type = update.message.effective_attachment or update.message.text or 'messaggio non identificato'
    await update.message.reply_text(f"Il tipo di file o messaggio che hai inviato non è supportato dal bot.\nTipo ricevuto: {type(msg_type).__name__}")

async def handle_redgifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re as _re
    text = update.message.text.strip()
    user_pattern = r"https?://(www\.)?redgifs\.com/users/([\w\d_-]+)"
    post_pattern = r"https?://(www\.)?redgifs\.com/watch/[\w\d_-]+"
    # Opzioni personalizzate
    only_video = text.lower().startswith("solo video")
    only_photo = text.lower().startswith("solo foto")
    ultimi_match = _re.match(r"ultimi (\d+) post", text.lower())
    ultimi_n = int(ultimi_match.group(1)) if ultimi_match else None
    # Controllo comando valido
    if (text.lower().startswith("solo ") and not (only_video or only_photo)) or (text.lower().startswith("ultimi") and not ultimi_match):
        await update.message.reply_text("Comando non riconosciuto. Usa solo video, solo foto, ultimi N post o solo il link utente Redgifs.")
        return
    # Gestione profilo utente
    user_match = _re.search(user_pattern, text)
    if user_match:
        username = user_match.group(2)
        await update.message.reply_text(f"Inizio a scaricare dal profilo {username}. Potrebbe volerci molto tempo...")
        allow_video = not only_photo
        allow_photo = not only_video
        max_posts = ultimi_n if ultimi_n else None
        results = download_redgifs_profile(username, SAVE_DIR, max_posts=max_posts, allow_video=allow_video, allow_photo=allow_photo)
        await update.message.reply_text(f"Download completato. File salvati: {len(results)}")
        return
    # Gestione singolo post
    post_match = _re.search(post_pattern, text)
    if post_match:
        await update.message.reply_text("Inizio a scaricare il post Redgifs...")
        allow_video = not only_photo
        allow_photo = not only_video
        file_path = download_redgifs_auto(post_match.group(0), SAVE_DIR, allow_video=allow_video, allow_photo=allow_photo)
        if file_path:
            await update.message.reply_text(f"File Redgifs scaricato e salvato come {os.path.basename(file_path)}!")
        else:
            await update.message.reply_text("Nessun file scaricabile trovato nel post Redgifs.")
        return
    await update.message.reply_text("Non ho riconosciuto un link Redgifs valido.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 *Comandi supportati dal bot:*\n\n"
        "📷 *Media diretti:* Invia foto, video, GIF e verranno salvati automaticamente\n\n"
        "🔗 *Link supportati:*\n"
        "• *Reddit:* Link a post, immagini, video, gallerie, profili utente\n"
        "• *Redgifs:* Link a singoli post o profili utente\n"
        "• *Mega:* Link a file singoli o cartelle complete\n\n"
        "📝 *Esempi:*\n"
        "• https://reddit.com/user/username\n"
        "• https://mega.nz/folder/ABC123#xyz789\n"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_mega_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    mega_pattern = r"https?://mega\.nz/(file|folder)/[^#]+#.+"
    match = re.search(mega_pattern, text)
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link Mega valido.")
        return
    mega_url = match.group(0)
    await update.message.reply_text("Inizio il download dal link Mega... (potrebbe volerci un po')")
    try:
        downloaded_files = download_mega_auto(mega_url, SAVE_DIR)
        if downloaded_files:
            await update.message.reply_text(f"Download Mega completato! File salvati: {len(downloaded_files)}")
        else:
            await update.message.reply_text("Nessun file scaricabile trovato o errore durante il download Mega.")
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download Mega: {str(e)}")

app = ApplicationBuilder().token("7564134479:AAHKqBkapm75YYJoYRBzS1NLFQskmbC-LcY").build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.ANIMATION, handle_animation))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://mega\.nz/(file|folder)/"), handle_mega_link))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://(www\.)?redgifs\.com/(users|watch)/"), handle_redgifs))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://[^\s]*reddit[^\s]*"), handle_reddit_link))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

# Sposta questo handler SOPRA quello dei post reddit (handle_reddit_link) per priorità

app.run_polling()

