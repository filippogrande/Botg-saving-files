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

async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    animation = update.message.animation
    file = await context.bot.get_file(animation.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    await file.download_to_drive(filename)
    await update.message.reply_text("GIF animata salvata come mp4!")

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
            if hasattr(submission, 'gallery_data') and hasattr(submission, 'media_metadata'):
                for idx, item in enumerate(submission.gallery_data['items']):
                    media_id = item['media_id']
                    media_url = submission.media_metadata[media_id]['s']['u']
                    ext = os.path.splitext(media_url)[1].split('?')[0]
                    filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}_{idx}{ext}"
                    r = requests.get(media_url, timeout=20)
                    with open(filename, 'wb') as f:
                        f.write(r.content)
                await update.message.reply_text(f"{len(submission.gallery_data['items'])} immagini Reddit salvate!")
            else:
                await update.message.reply_text("Il post sembra una galleria ma non sono riuscito a recuperare i dati delle immagini (gallery_data o media_metadata mancanti).")
                return
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
        # Gestione gif/gifv/webm/mp4 diretti
        elif any(submission.url.endswith(ext) for ext in ['.gif', '.gifv', '.webm', '.mp4']):
            media_url = submission.url
            ext = ".mp4"
            filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}{ext}"
            r = requests.get(media_url, timeout=20)
            with open(filename, 'wb') as f:
                f.write(r.content)
            await update.message.reply_text(f"GIF/Video Reddit salvato come {os.path.basename(filename)}!")
        else:
            hint = getattr(submission, 'post_hint', 'N/A')
            is_video = getattr(submission, 'is_video', 'N/A')
            provider = submission.media['oembed']['provider_name'] if submission.media and 'oembed' in submission.media and 'provider_name' in submission.media['oembed'] else 'N/A'
            # Gestione Redgifs
            if provider.lower() == 'redgifs':
                try:
                    import yt_dlp
                    redgifs_url = submission.url
                    filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}_redgifs.mp4"
                    ydl_opts = {
                        'outtmpl': filename,
                        'format': 'mp4/bestvideo+bestaudio/best',
                        'quiet': True,
                        'merge_output_format': 'mp4',
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([redgifs_url])
                    await update.message.reply_text(f"Video Redgifs scaricato e salvato come {os.path.basename(filename)}!")
                    return
                except Exception as e:
                    await update.message.reply_text(f"Errore durante il download del video Redgifs con yt-dlp: {e}")
                    return
            await update.message.reply_text(f"Questo post Reddit non contiene immagini o video scaricabili.\npost_hint: {hint}, is_video: {is_video}, provider: {provider}")
    except Exception as e:
        await update.message.reply_text("Errore durante il download del contenuto Reddit.")

async def handle_direct_reddit_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    img_pattern = r"https?://i\.redd\.it/[\w\d]+\.[a-zA-Z0-9]+"
    match = re.search(img_pattern, text)
    if match:
        img_url = match.group(0)
        ext = os.path.splitext(img_url)[1].split('?')[0]
        filename = f"{SAVE_DIR}/reddit_direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        r = requests.get(img_url, timeout=20)
        with open(filename, 'wb') as f:
            f.write(r.content)
        await update.message.reply_text(f"Immagine Reddit diretta salvata come {os.path.basename(filename)}!")

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_type = update.message.effective_attachment or update.message.text or 'messaggio non identificato'
    await update.message.reply_text(f"Il tipo di file o messaggio che hai inviato non è supportato dal bot.\nTipo ricevuto: {type(msg_type).__name__}")

async def handle_redgifs_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import yt_dlp
    import re as _re
    import asyncio
    import time
    text = update.message.text
    user_pattern = r"https?://(www\.)?redgifs\.com/users/([\w\d_-]+)"
    match = _re.search(user_pattern, text)
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link utente Redgifs valido.")
        return
    username = match.group(2)
    await update.message.reply_text(f"Inizio a scaricare i video pubblici di: {username}. Potrebbe volerci molto tempo...")
    user_url = f"https://www.redgifs.com/users/{username}/creations"
    ydl_opts = {
        'outtmpl': f"{SAVE_DIR}/redgifs_{username}_%(title)s.%(ext)s",
        'format': 'mp4/bestvideo+bestaudio/best',
        'quiet': True,
        'merge_output_format': 'mp4',
        'ignoreerrors': True,
        'extract_flat': True,
        'force_generic_extractor': True,
    }
    try:
        last_update = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(user_url, download=False)
            entries = info.get('entries', [])
            for idx, entry in enumerate(entries):
                video_url = entry.get('url')
                if video_url:
                    ydl.download([video_url])
                    await asyncio.sleep(2)  # Attendi 2 secondi tra un download e l'altro
                # Ogni 30 minuti invia un messaggio di stato
                if time.time() - last_update > 1800:
                    await update.message.reply_text(f"Sto ancora scaricando i video di {username} in background...")
                    last_update = time.time()
        await update.message.reply_text(f"Download dei video di {username} completato.")
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download dei video Redgifs dell'utente {username}: {e}")

async def handle_redgifs_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import yt_dlp
    import re as _re
    text = update.message.text
    video_pattern = r"https?://(www\.)?redgifs\.com/watch/[\w\d_-]+"
    match = _re.search(video_pattern, text)
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link video Redgifs valido.")
        return
    video_url = match.group(0)
    await update.message.reply_text(f"Scarico il video Redgifs: {video_url}")
    filename = f"{SAVE_DIR}/redgifs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    ydl_opts = {
        'outtmpl': filename,
        'format': 'mp4/bestvideo+bestaudio/best',
        'quiet': True,
        'merge_output_format': 'mp4',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        await update.message.reply_text(f"Video Redgifs scaricato e salvato come {os.path.basename(filename)}!")
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download del video Redgifs: {e}")

app = ApplicationBuilder().token("7564134479:AAHKqBkapm75YYJoYRBzS1NLFQskmbC-LcY").build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.ANIMATION, handle_animation))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://(www\.)?redgifs\.com/users/"), handle_redgifs_user))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://(www\.)?redgifs\.com/watch/"), handle_redgifs_video))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://i\.redd\.it/"), handle_direct_reddit_image))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reddit_link))
app.add_handler(MessageHandler(~(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.TEXT & ~filters.COMMAND), handle_unknown))

app.run_polling()

