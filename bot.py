import asyncio
print("[BOT] Avvio bot.py: processo partito, inizio import e setup...")
import os
import signal
watcher_task = None

async def _run_daily_watcher():
    while True:
        try:
            from reddit_helper import reddit_watcher_once
            await reddit_watcher_once(SAVE_DIR, deduplication_noctx, bot=app.bot)
        except Exception as e:
            print(f"Errore in watcher giornaliero: {e}")
        await asyncio.sleep(24 * 3600)

def start_daily_watcher():
    global watcher_task
    loop = asyncio.get_event_loop()
    watcher_task = loop.create_task(_run_daily_watcher())

async def stop_daily_watcher():
    global watcher_task
    if watcher_task:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass

def _on_shutdown(*_):
    loop = asyncio.get_event_loop()
    loop.create_task(stop_daily_watcher())

for s in (signal.SIGINT, signal.SIGTERM):
    try:
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(s, _on_shutdown)
    except Exception:
        pass

# Avvia watcher solo se richiesto
# (Watcher start moved to __main__ after app creation)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import os
from dotenv import load_dotenv
from datetime import datetime
import re
import asyncio
import json

# Importazione condizionale per Mega (per evitare errori se la libreria non è disponibile)
try:
    from mega_helper import download_mega_auto, is_mega_link
    MEGA_AVAILABLE = True
except ImportError as e:
    print(f"Mega helper non disponibile:  {e}")
    MEGA_AVAILABLE = False
    
    # Funzioni placeholder
    def download_mega_auto(*args, **kwargs):
        return []
    
    def is_mega_link(url):
        return False


load_dotenv()

# Lista di chat ID autorizzati (separati da virgola)
ALLOWED_CHAT_IDS = set()
ids_env = os.environ.get("ALLOWED_CHAT_IDS")
if ids_env:
    ALLOWED_CHAT_IDS = set(i.strip() for i in ids_env.split(",") if i.strip())

def is_authorized(update: Update) -> bool:
    return str(update.effective_user.id) in ALLOWED_CHAT_IDS if ALLOWED_CHAT_IDS else True

async def unauthorized_reply(update: Update):
    await update.message.reply_text("❌ Utente non autorizzato. Contatta l'amministratore del bot.")

# Directory di salvataggio (override con .env SAVE_DIR se presente)
SAVE_DIR = os.environ.get("SAVE_DIR", "/mnt/truenas-bot")
os.makedirs(SAVE_DIR, exist_ok=True)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    await update.message.reply_text('Benvenuto! Il bot è attivo.\nQuesto bot è per il mio uso personale e potrebbe non funzionare per altri utenti.')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    user = update.effective_user
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    await file.download_to_drive(filename)
    await update.message.reply_text("Foto ricevuta!")
    await duplicate_check_and_interaction(update, context)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    user = update.effective_user
    video = update.message.video
    file = await context.bot.get_file(video.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    await file.download_to_drive(filename)
    await update.message.reply_text("Video ricevuto!")
    await duplicate_check_and_interaction(update, context)

async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    user = update.effective_user
    animation = update.message.animation
    file = await context.bot.get_file(animation.file_id)
    filename = f"{SAVE_DIR}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    await file.download_to_drive(filename)
    await update.message.reply_text("GIF animata salvata come mp4!")
    await duplicate_check_and_interaction(update, context)

async def handle_reddit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    reddit_pattern = r"(reddit\.com|i\.redd\.it)"
    if not re.search(reddit_pattern, text, re.IGNORECASE):
        await update.message.reply_text("Non ho riconosciuto un link Reddit valido.")
        return
    # Se sembra un profilo utente reddit, chiedi conferma prima di scaricare l'intero account
    if re.search(r"reddit\.com/(user|u)/", text, re.IGNORECASE):
        context.user_data['pending_download'] = {
            'action': 'reddit_profile',
            'url': text,
            'user_id': update.effective_user.id,
        }
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Conferma", callback_data='confirm_pending'),
            InlineKeyboardButton("Annulla", callback_data='cancel_pending')
        ]])
        await update.message.reply_text(
            "Hai inviato un link a un profilo Reddit. Scaricare l'intero account può richiedere molto tempo. Procedo?",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text("Inizio il download dal link Reddit... (potrebbe volerci un po')")
    try:
        # import reddit helper only when needed
        from reddit_helper import download_reddit_auto
        result = await download_reddit_auto(text, SAVE_DIR, user_id=update.effective_user.id)
        if isinstance(result, list):
            if result:
                await update.message.reply_text(f"Download completato! File salvati: {len(result)}")
            else:
                await update.message.reply_text("Nessun media scaricabile trovato nel link Reddit.")
        elif isinstance(result, str):
            if result.lower().startswith("profilo"):
                await update.message.reply_text(result)
            elif result.lower().startswith("errore"):
                await update.message.reply_text(result)
            else:
                await update.message.reply_text(f"Info: {result}")
        await duplicate_check_and_interaction(update, context)
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download dal link Reddit: {str(e)}")

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text or ''
    if text.startswith("/"):
        await update.message.reply_text("Comando non riconosciuto.")
        return
    msg_type = update.message.effective_attachment or text or 'messaggio non identificato'
    await update.message.reply_text(f"Il tipo di file o messaggio che hai inviato non è supportato dal bot.\nTipo ricevuto: {type(msg_type).__name__}")

async def handle_redgifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    import re as _re
    # import heavy helper only when needed
    from redgifs_helper import download_redgifs_profile, download_redgifs_auto
    text = update.message.text.strip()
    user_pattern = r"https?://(www\\.)?redgifs\\.com/users/([\\w\\d_-]+)"
    post_pattern = r"https?://(www\\.)?redgifs\\.com/watch/[\\w\\d_-]+"
    only_video = text.lower().startswith("solo video")
    only_photo = text.lower().startswith("solo foto")
    ultimi_match = _re.match(r"ultimi (\\d+) post", text.lower())
    ultimi_n = int(ultimi_match.group(1)) if ultimi_match else None
    if (text.lower().startswith("solo ") and not (only_video or only_photo)) or (text.lower().startswith("ultimi") and not ultimi_match):
        await update.message.reply_text("Comando non riconosciuto. Usa solo video, solo foto, ultimi N post o solo il link utente Redgifs.")
        return
    user_match = _re.search(user_pattern, text)
    if user_match:
        username = user_match.group(2)
        allow_video = not only_photo
        allow_photo = not only_video
        max_posts = ultimi_n if ultimi_n else None
        # Salva l'azione pendente nello user_data e chiedi conferma
        context.user_data['pending_download'] = {
            'action': 'redgifs_profile',
            'username': username,
            'allow_video': allow_video,
            'allow_photo': allow_photo,
            'max_posts': max_posts,
        }
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Conferma", callback_data='confirm_pending'),
            InlineKeyboardButton("Annulla", callback_data='cancel_pending')
        ]])
        await update.message.reply_text(
            f"Hai chiesto di scaricare il profilo Redgifs '{username}'.\nQuesto può richiedere molto tempo e consumare spazio. Confermi?",
            reply_markup=keyboard
        )
        return

    post_match = _re.search(post_pattern, text)
    if post_match:
        await update.message.reply_text("Inizio a scaricare il post Redgifs...")
        allow_video = not only_photo
        allow_photo = not only_video
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_redgifs_auto, post_match.group(0), SAVE_DIR, None, allow_video, allow_photo)
        if file_path:
            await update.message.reply_text(f"File Redgifs scaricato e salvato come {os.path.basename(file_path)}!")
        else:
            await update.message.reply_text("Nessun file scaricabile trovato nel post Redgifs.")
        await duplicate_check_and_interaction(update, context)
        return
    await update.message.reply_text("Non ho riconosciuto un link Redgifs valido.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    chat_id = update.effective_chat.id
    help_text = (
        "🤖 *Comandi supportati dal bot:*\n\n"
        "*Comandi generali:*\n"
        "• /start — Avvia il bot e mostra informazioni iniziali\n"
        "• /hello — Saluta rapidamente\n"
        "• /help — Mostra questo messaggio di aiuto\n"
        "• /numeri — Conta foto e video salvati\n"
        "• /trovamiduplicati — Avvia controllo duplicati manuale\n"
        "• /Watched — Mostra i profili Reddit monitorati e a chi vengono inviate le notifiche\n"
        "• /tracked — Alias di /Watched (stesso comportamento)\n\n"
        "*Come inviare media e link:*\n"
        "• Invia foto, video o GIF direttamente (verranno salvati)\n"
        "• Invia link Reddit: post, immagini, video, gallerie o profili utente\n"
        "• Invia link Redgifs: singoli post o profili utente\n"
        "• Invia link Mega: file singoli o cartelle complete\n\n"
        "*Esempi:*\n"
        "• https://reddit.com/user/username\n"
        "• https://mega.nz/folder/ABC123#xyz789\n\n"
        f"*DEBUG: Il tuo chat ID è:* `{chat_id}`"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_mega_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    mega_pattern = r"https?://mega\\.nz/(file|folder)/[^#]+#.+"
    match = re.search(mega_pattern, text)
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link Mega valido.")
        return
    mega_url = match.group(0)
    await update.message.reply_text("Inizio il download dal link Mega... (potrebbe volerci un po')")
    try:
        # carga le funzioni Mega solo quando servono
        try:
            from mega_helper import download_mega_auto
            mega_available = True
        except Exception:
            mega_available = False
        if not mega_available:
            await update.message.reply_text("Mega helper non disponibile nel container.")
            return
        loop = asyncio.get_running_loop()
        downloaded_files = await loop.run_in_executor(None, download_mega_auto, mega_url, SAVE_DIR)
        if downloaded_files:
            await update.message.reply_text(f"Download Mega completato! File salvati: {len(downloaded_files)}")
        else:
            await update.message.reply_text("Nessun file scaricabile trovato o errore durante il download Mega.")
        await duplicate_check_and_interaction(update, context)
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download Mega: {str(e)}")

# Sostituisci la funzione duplicate_check_and_interaction con la nuova logica automatica
async def duplicate_check_and_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Controllo duplicati in corso... Questo potrebbe richiedere qualche secondo.")
    loop = asyncio.get_running_loop()
    def _run_find_duplicates(path):
        from find_duplicate_helper import find_duplicates as _fd
        # Non passiamo il debug_callback: niente log via Telegram
        return _fd(path)
    try:
        num_removed = await loop.run_in_executor(None, _run_find_duplicates, SAVE_DIR)
        if num_removed > 0:
            await update.message.reply_text(f"Rimossi automaticamente {num_removed} file duplicati.")
        else:
            await update.message.reply_text("Nessun duplicato trovato.")
    except Exception as e:
        await update.message.reply_text(f"Errore durante la deduplicazione: {e}")
        import traceback
        print('Errore deduplicazione:', traceback.format_exc())

# Wrapper per deduplicazione senza update/context (per watcher)
async def deduplication_noctx():
    loop = asyncio.get_running_loop()
    from find_duplicate_helper import find_duplicates as _fd
    num_removed = await loop.run_in_executor(None, _fd, SAVE_DIR)
    if num_removed > 0:
        print(f"[Watcher] Rimossi automaticamente {num_removed} file duplicati.")
    return num_removed

async def watched_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        watch_path = os.path.join(SAVE_DIR, "reddit_watch.json")
        user_file = os.path.join(SAVE_DIR, "reddit_notify_user.txt")
        watched = []
        notify_user_id = None
        notify_user_name = None
        if os.path.exists(watch_path):
            with open(watch_path, "r") as f:
                data = json.load(f)
                watched = list(data.keys())
        if os.path.exists(user_file):
            with open(user_file, "r") as f:
                notify_user_id = f.read().strip()
        # Prova a recuperare il nome utente Telegram
        if notify_user_id:
            try:
                user_obj = await context.bot.get_chat(int(notify_user_id))
                notify_user_name = user_obj.full_name or user_obj.username or notify_user_id
            except Exception:
                notify_user_name = notify_user_id
        msg = "\n".join([
            "👁️ Profili Reddit monitorati:",
            *(watched if watched else ["(Nessuno)"]),
            "",
            f"🔔 Notifiche automatiche inviate a: {notify_user_name if notify_user_name else '(Nessuno)'}"
        ])
        await update.message.reply_text(msg)
        # Se chi invoca il comando è il destinatario delle notifiche, invia conferma
        if notify_user_id and str(update.effective_user.id) == str(notify_user_id):
            await update.message.reply_text("Riceverai le notifiche dei download automatici dal watcher Reddit.")
    except Exception as e:
        await update.message.reply_text(f"Errore nel recupero dei profili monitorati: {e}")


async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'cancel_pending':
        context.user_data.pop('pending_download', None)
        try:
            await query.edit_message_text('Operazione annullata.')
        except Exception:
            await query.message.reply_text('Operazione annullata.')
        return

    if data != 'confirm_pending':
        await query.answer()
        return

    pending = context.user_data.pop('pending_download', None)
    if not pending:
        try:
            await query.edit_message_text('Nessuna azione in sospeso da confermare.')
        except Exception:
            await query.message.reply_text('Nessuna azione in sospeso da confermare.')
        return

    # Esegui l'azione richiesta in background
    await query.edit_message_text('Avvio download... Ti invierò un messaggio quando è completato.')
    loop = asyncio.get_running_loop()
    try:
        if pending['action'] == 'redgifs_profile':
            from redgifs_helper import download_redgifs_profile
            username = pending['username']
            allow_video = pending.get('allow_video', True)
            allow_photo = pending.get('allow_photo', True)
            max_posts = pending.get('max_posts')
            results = await loop.run_in_executor(None, download_redgifs_profile, username, SAVE_DIR, max_posts, allow_video, allow_photo)
            await context.bot.send_message(query.from_user.id, f"Download completato. File salvati: {len(results)}")
            await duplicate_check_and_interaction(update, context)
            return

        if pending['action'] == 'reddit_profile':
            from reddit_helper import download_reddit_auto
            url = pending.get('url')
            result = await download_reddit_auto(url, SAVE_DIR, user_id=pending.get('user_id'))
            if isinstance(result, list):
                if result:
                    await context.bot.send_message(query.from_user.id, f"Download completato! File salvati: {len(result)}")
                else:
                    await context.bot.send_message(query.from_user.id, "Nessun media scaricabile trovato nel link Reddit.")
            elif isinstance(result, str):
                await context.bot.send_message(query.from_user.id, result)
            await duplicate_check_and_interaction(update, context)
            return

        await context.bot.send_message(query.from_user.id, 'Tipo di download non riconosciuto.')
    except Exception as e:
        await context.bot.send_message(query.from_user.id, f'Errore durante il download: {e}')

import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN non impostato nelle variabili d'ambiente")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Optional startup notification
STARTUP_NOTIFY = os.environ.get("STARTUP_NOTIFY", "false").lower() in ("1", "true", "yes")
STARTUP_CHAT_ID = os.environ.get("STARTUP_CHAT_ID")
if STARTUP_NOTIFY and STARTUP_CHAT_ID:
    try:
        # invia un messaggio di avvio al chat id configurato
        async def _notify_startup():
            await app.bot.send_message(int(STARTUP_CHAT_ID), "Bot avviato e operativo.")
        # schedule notification shortly after start
        asyncio.get_event_loop().create_task(_notify_startup())
    except Exception as e:
        print(f"Impossibile inviare notifica di avvio: {e}")
        
# Comando /numeri: conta foto e video dal db
async def numeri_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    await update.message.reply_text("Sto contando le foto e i video...")
    try:
        from db_helper import count_media_by_type
        counts = count_media_by_type(SAVE_DIR)
        await update.message.reply_text(f"Foto: {counts['foto']}\nVideo: {counts['video']}")
    except Exception as e:
        await update.message.reply_text(f"Errore nel conteggio: {e}")



app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("Watched", watched_command))
app.add_handler(CommandHandler("tracked", watched_command))
app.add_handler(CommandHandler("numeri", numeri_command))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.ANIMATION, handle_animation))
app.add_handler(CommandHandler("trovamiduplicati", duplicate_check_and_interaction))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://mega\\.nz/(file|folder)/"), handle_mega_link))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://(www\\.)?redgifs\\.com/(users|watch)/"), handle_redgifs))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://[^\\s]*reddit[^\\s]*"), handle_reddit_link))




app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))
app.add_handler(CallbackQueryHandler(handle_confirm_callback))

if __name__ == "__main__":
    # Avvia il bot in polling. Il watcher Reddit non parte automaticamente
    # Per eseguire il watcher una sola volta usare lo script run_watcher.py
    # Start watcher only after the Application and app.bot have been constructed
    try:
        if os.environ.get("WATCHER_ENABLED", "false").lower() in ("1", "true", "yes"):
            # ensure we don't start watcher before app.bot exists
            start_daily_watcher()
    except Exception as e:
        print(f"Impossibile avviare il watcher: {e}")

    app.run_polling()




