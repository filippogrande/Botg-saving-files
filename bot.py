from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
from datetime import datetime
import re
import requests
import asyncpraw
from redgifs_helper import download_redgifs_profile, download_redgifs_auto

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
                file_path = download_redgifs_auto(submission.url, SAVE_DIR)
                if file_path:
                    await update.message.reply_text(f"Media Redgifs scaricato e salvato come {os.path.basename(file_path)}!")
                else:
                    await update.message.reply_text("Errore durante il download del media Redgifs.")
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

async def handle_mega_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestisce i link Mega scaricando file o cartelle complete mantenendo la struttura.
    """
    if not MEGA_AVAILABLE:
        await update.message.reply_text(
            "❌ Funzionalità Mega temporaneamente non disponibile.\n"
            "Per attivarla, sul server esegui: bash install_megatools.sh"
        )
        return
        
    text = update.message.text.strip()
    
    # Estrai il link Mega dal messaggio
    mega_pattern = r"https?://mega\.nz/(file|folder)/[^#]+#[^\s]+"
    match = re.search(mega_pattern, text)
    
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link Mega valido.")
        return
    
    mega_url = match.group(0)
    
    try:
        # Verifica se il link è di un file o cartella
        from mega_helper import extract_mega_info, check_megatools_installed
        link_type, _, _ = extract_mega_info(mega_url)
        
        if not check_megatools_installed():
            await update.message.reply_text(
                "❌ Tool 'megatools' non installato sul server.\n"
                f"Tipo link: {link_type or 'sconosciuto'}\n"
                "Per installarlo: bash install_megatools.sh"
            )
            return
        
        # Determina se preservare la struttura delle cartelle
        preserve_structure = True
        custom_prefix = None
        
        # Controlla se l'utente ha specificato opzioni particolari
        if "struttura piatta" in text.lower() or "flat" in text.lower():
            preserve_structure = False
            
        # Controlla se l'utente ha specificato un prefisso personalizzato
        prefix_match = re.search(r"prefisso:?\s*([^\s]+)", text.lower())
        if prefix_match:
            custom_prefix = prefix_match.group(1)
        
        # Messaggio diverso per file vs cartelle
        if link_type == "file":
            await update.message.reply_text("🔄 Inizio il download del file da Mega...")
        elif link_type == "folder":
            await update.message.reply_text("🔄 Inizio il download della cartella da Mega... Questo potrebbe richiedere molto tempo.")
        else:
            await update.message.reply_text("🔄 Inizio il download da Mega...")
        
        # Esegui il download
        downloaded_files = download_mega_auto(
            mega_url, 
            SAVE_DIR, 
            custom_prefix=custom_prefix,
            preserve_structure=preserve_structure
        )
        
        if downloaded_files:
            file_count = len(downloaded_files)
            if file_count == 1:
                filename = os.path.basename(downloaded_files[0])
                await update.message.reply_text(f"✅ Download completato! File salvato: {filename}")
            else:
                await update.message.reply_text(
                    f"✅ Download completato! Scaricati {file_count} file "
                    f"{'mantenendo la struttura delle cartelle' if preserve_structure else 'in struttura piatta'}."
                )
        else:
            await update.message.reply_text(
                "❌ Errore durante il download da Mega.\n"
                "Possibili cause:\n"
                "• Link Mega non valido o scaduto\n"
                "• File/cartella troppo grande\n" 
                "• megatools non installato (esegui: sudo apt install megatools)\n"
                "• Problema di connessione"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Errore durante il download da Mega: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
🤖 **Comandi supportati dal bot:**

📷 **Media diretti:** Invia foto, video, GIF e verranno salvati automaticamente

🔗 **Link supportati:**
• **Reddit:** Link a post, immagini, video, gallerie
• **Redgifs:** Link a singoli post o profili utente
• **Mega:** Link a file singoli o cartelle complete

📁 **Mega - Opzioni speciali:**
• Invia solo il link per mantenere la struttura delle cartelle
• Aggiungi "struttura piatta" per scaricare tutto in una cartella
• Aggiungi "prefisso: nome" per personalizzare il nome dei file

🎯 **Redgifs - Opzioni speciali:**
• "solo video [link]" - scarica solo i video
• "solo foto [link]" - scarica solo le immagini  
• "ultimi N post [link]" - scarica solo gli ultimi N post

📝 **Esempi:**
• `https://mega.nz/folder/ABC123#xyz789`
• `struttura piatta https://mega.nz/folder/ABC123#xyz789`
• `prefisso: miacartella https://mega.nz/folder/ABC123#xyz789`
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

app = ApplicationBuilder().token("7564134479:AAHKqBkapm75YYJoYRBzS1NLFQskmbC-LcY").build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.ANIMATION, handle_animation))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://mega\.nz/(file|folder)/"), handle_mega_link))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://(www\.)?redgifs\.com/(users|watch)/"), handle_redgifs))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://i\.redd\.it/"), handle_direct_reddit_image))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reddit_link))
app.add_handler(MessageHandler(~(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.TEXT & ~filters.COMMAND), handle_unknown))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://mega\.nz/(file|folder)/"), handle_mega_link))
app.add_handler(CommandHandler("help", help_command))

app.run_polling()

