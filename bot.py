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
                    import re as _re
                    import json as _json
                    redgifs_url = submission.url
                    page = requests.get(redgifs_url, timeout=20).text
                    # Cerca blocco JSON window.__INITIAL_STATE__
                    state_match = _re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', page, _re.DOTALL)
                    video_url = None
                    if state_match:
                        try:
                            state_json = _json.loads(state_match.group(1))
                            # Cerca la chiave mp4 nel JSON
                            for v in _re.findall(r'https://[^"]+\.mp4', _json.dumps(state_json)):
                                video_url = v
                                break
                        except Exception as e:
                            pass
                    # Se non trovato nel JSON, prova regex classiche
                    if not video_url:
                        match = _re.search(r'source src="(https://[^"]+\.mp4)"', page)
                        if not match:
                            match = _re.search(r'"mp4Source":"(https://[^"]+\.mp4)"', page)
                        if not match:
                            match = _re.search(r'"hdSrc":"(https://[^"]+\.mp4)"', page)
                        if not match:
                            match = _re.search(r'"urls":\{"hd":"(https://[^"]+\.mp4)"', page)
                        if not match:
                            match = _re.search(r'"mp4":"(https://[^"]+\.mp4)"', page)
                        if match:
                            video_url = match.group(1).replace('\\u0026', '&')
                    if video_url:
                        ext = ".mp4"
                        filename = f"{SAVE_DIR}/{author}_{submission.id}_{timestamp}_redgifs{ext}"
                        r = requests.get(video_url, timeout=20)
                        with open(filename, 'wb') as f:
                            f.write(r.content)
                        await update.message.reply_text(f"Video Redgifs salvato come {os.path.basename(filename)}!\nURL: {video_url}")
                        return
                    else:
                        await update.message.reply_text(f"Non sono riuscito a trovare il video Redgifs diretto (anche nel JSON della pagina).\nLink Redgifs: {redgifs_url}")
                        return
                except Exception as e:
                    await update.message.reply_text(f"Errore durante il download del video Redgifs: {e}")
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

app = ApplicationBuilder().token("7564134479:AAHKqBkapm75YYJoYRBzS1NLFQskmbC-LcY").build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.ANIMATION, handle_animation))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://i\.redd\.it/"), handle_direct_reddit_image))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reddit_link))
app.add_handler(MessageHandler(~(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.TEXT & ~filters.COMMAND), handle_unknown))

app.run_polling()

