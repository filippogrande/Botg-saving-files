import asyncio
print("[BOT] Avvio bot.py: processo partito, inizio import e setup...")
import os
import signal
watcher_task = None

from report_helper import format_download_report
from deduplica import deduplica_file
from actor_report import format_actor_report_from_paths
from log_helper import setup_logging

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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from datetime import datetime
import re
import asyncio
import json

try:
    from mega_helper import download_mega_auto, is_mega_link
    MEGA_AVAILABLE = True
except ImportError as e:
    print(f"Mega helper non disponibile:  {e}")
    MEGA_AVAILABLE = False
    def download_mega_auto(*args, **kwargs):
        return []
    def is_mega_link(url):
        return False

load_dotenv()

ALLOWED_CHAT_IDS = set()
ids_env = os.environ.get("ALLOWED_CHAT_IDS")
if ids_env:
    ALLOWED_CHAT_IDS = set(i.strip() for i in ids_env.split(",") if i.strip())

def is_authorized(update: Update) -> bool:
    return str(update.effective_user.id) in ALLOWED_CHAT_IDS if ALLOWED_CHAT_IDS else True

async def unauthorized_reply(update: Update):
    await update.message.reply_text("❌ Utente non autorizzato. Contatta l'amministratore del bot.")

SAVE_DIR = os.environ.get("SAVE_DIR", "/mnt/truenas-bot")
os.makedirs(SAVE_DIR, exist_ok=True)
setup_logging(SAVE_DIR)

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

# ---- Forward Telegram: isolati in Telegram/ + deduplica + report ----
async def _save_telegram(update, context, file_id, ext, msg_ok):
    user = update.effective_user
    file = await context.bot.get_file(file_id)
    telegram_dir = os.path.join(SAVE_DIR, "Telegram")
    os.makedirs(telegram_dir, exist_ok=True)
    filename = f"{telegram_dir}/{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    await file.download_to_drive(filename)
    kept = deduplica_file(filename, SAVE_DIR)
    await update.message.reply_text(msg_ok if kept else "File ricevuto (duplicato, scartato).")
    await post_download_report(update, context, [filename] if kept else [], label="Telegram")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    await _save_telegram(update, context, update.message.photo[-1].file_id, ".jpg", "Foto ricevuta!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    await _save_telegram(update, context, update.message.video.file_id, ".mp4", "Video ricevuto!")

async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    await _save_telegram(update, context, update.message.animation.file_id, ".mp4", "GIF animata salvata come mp4!")

async def handle_reddit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    reddit_pattern = r"(reddit\.com|i\.redd\.it)"
    if not re.search(reddit_pattern, text, re.IGNORECASE):
        await update.message.reply_text("Non ho riconosciuto un link Reddit valido.")
        return
    is_profile = False
    try:
        from reddit_helper import classify_reddit_url
        if classify_reddit_url(text) == 'profile':
            is_profile = True
        
    except Exception:
        if re.search(r"https?://(www\.)?reddit\.com/(user|u)/[\w\d_-]+(/)?$", text, re.IGNORECASE):
            is_profile = True

    if is_profile:
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
        from reddit_helper import download_reddit_auto
        stats = {}
        result = await download_reddit_auto(text, SAVE_DIR, user_id=update.effective_user.id, stats=stats)
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
        await post_download_report(update, context, result, stats=stats, label="Reddit")
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
    from redgifs_helper import download_redgifs_profile, download_redgifs_auto
    text = update.message.text.strip()
    user_pattern = r"https?://(www\.)?redgifs\.com/users/([\w\d_-]+)"
    post_pattern = r"https?://(www\.)?redgifs\.com/watch/[\w\d_-]+"
    only_video = text.lower().startswith("solo video")
    only_photo = text.lower().startswith("solo foto")
    ultimi_match = _re.match(r"ultimi (\d+) post", text.lower())
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
        stats = {}
        file_path = await loop.run_in_executor(None, download_redgifs_auto, post_match.group(0), SAVE_DIR, None, allow_video, allow_photo, stats)
        if file_path:
            await update.message.reply_text(f"File Redgifs scaricato e salvato come {os.path.basename(file_path)}!")
        else:
            await update.message.reply_text("Nessun file scaricabile trovato nel post Redgifs.")
        await post_download_report(update, context, [file_path] if file_path else [], stats=stats, label="Redgifs")
        return
    await update.message.reply_text("Non ho riconosciuto un link Redgifs valido.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    help_text = (
        "🤖 *Comandi supportati dal bot:*\n\n"
        "*Comandi generali:*\n"
        "• /start — Avvia il bot e mostra informazioni iniziali\n"
        "• /hello — Saluta rapidamente\n"
        "• /help — Mostra questo messaggio di aiuto\n"
        "• /numeri — Conta foto e video salvati\n"
        "• /trovamiduplicati — Controllo duplicati manuale (con conferma)\n"
        "• /recalculate — Ricalcola gli hash di tutti i file\n"
        "• /mapactor — Mappa username → nome attore (merge se esiste già)\n"
        "• /listmap — Mostra le mappature attore (con indice)\n"
        "• /editactor — Modifica una mappatura esistente (es: /editactor 1 redgifs:user)\n"
        "• /delactor — Rimuove una mappatura (es: /delactor 1)\n"
        "• /Watched — Profili Reddit monitorati e destinatario notifiche\n"
        "• /tracked — Alias di /Watched\n\n"
        "*Come inviare media e link:*\n"
        "• Invia foto, video o GIF direttamente (salvati e deduplicati)\n"
        "• Invia link Reddit: post, immagini, video, gallerie o profili\n"
        "• Invia link Redgifs: singoli post o profili\n"
        "• Invia link Mega: file singoli o cartelle\n\n"
        "*Esempi:*\n"
        "• https://reddit.com/user/username\n"
        "• https://mega.nz/folder/ABC123#xyz789"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_mega_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    mega_pattern = r"https?://mega\.nz/(file|folder)/[^#]+#.+"
    match = re.search(mega_pattern, text)
    if not match:
        await update.message.reply_text("Non ho riconosciuto un link Mega valido.")
        return
    mega_url = match.group(0)
    await update.message.reply_text("Inizio il download dal link Mega... (potrebbe volerci un po')")
    try:
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
        await post_download_report(update, context, downloaded_files or [], label="Mega")
    except Exception as e:
        await update.message.reply_text(f"Errore durante il download Mega: {str(e)}")

# Report automatico post-download (niente conferma all'utente)
async def post_download_report(update, context, result, stats=None, label="Download"):
    if not is_authorized(update):
        return
    scaricati = 0
    if isinstance(result, list):
        scaricati = len(result)
    elif isinstance(result, str):
        if result.lower().startswith(("profilo", "errore")):
            await update.message.reply_text(result)
        else:
            await update.message.reply_text(f"Info: {result}")
        return
    dup = (stats or {}).get('duplicates', 0)
    await update.message.reply_text(format_download_report(label, scaricati, dup))
    line = format_actor_report_from_paths(result)
    if line:
        await update.message.reply_text(line)

# Deduplica manuale con conferma (usata da /trovamiduplicati)
async def duplicate_check_and_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Rimuovi duplicati ora", callback_data='confirm_dedupe'),
        InlineKeyboardButton("Annulla", callback_data='cancel_dedupe')
    ]])
    context.user_data['pending_action'] = {'action': 'run_dedupe'}
    await update.message.reply_text(
        "Vuoi procedere con la rimozione dei duplicati ora?",
        reply_markup=keyboard
    )

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
    if data in ('cancel_rehash', 'cancel_dedupe'):
        context.user_data.pop('pending_action', None)
        try:
            await query.edit_message_text('Operazione annullata.')
        except Exception:
            await query.message.reply_text('Operazione annullata.')
        return
    if data == 'confirm_rehash':
        pending = context.user_data.pop('pending_action', None)
        if not pending or not str(pending.get('action', '')).startswith('rehash'):
            try:
                await query.edit_message_text('Nessuna azione di rehash in sospeso.')
            except Exception:
                await query.message.reply_text('Nessuna azione di rehash in sospeso.')
            return
        action_kind = pending.get('action')
        await query.edit_message_text('Avvio ricalcolo degli hash... Attendi, invierò un riepilogo.')
        loop = asyncio.get_running_loop()
        try:
            from find_duplicate_helper import rehash_files
            stats = await loop.run_in_executor(None, rehash_files, SAVE_DIR)
            msg = (f"Ricalcolo completato. Hash aggiornati: {stats.get('updated',0)}, "
                   f"nuovi inserimenti: {stats.get('inserted',0)}, "
                   f"unchanged: {stats.get('unchanged',0)}, errors: {stats.get('errors',0)}")
            await context.bot.send_message(query.from_user.id, msg)
            if action_kind == 'rehash_dedup':
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Rimuovi duplicati ora", callback_data='confirm_dedupe'),
                    InlineKeyboardButton("No, poi", callback_data='cancel_dedupe')
                ]])
                context.user_data['pending_action'] = {'action': 'run_dedupe'}
                await context.bot.send_message(query.from_user.id, "Vuoi procedere ora con la rimozione dei duplicati?", reply_markup=keyboard)
            return
        except Exception as e:
            await context.bot.send_message(query.from_user.id, f'Errore durante il ricalcolo: {e}')
            return
    if data == 'confirm_dedupe':
        pending = context.user_data.pop('pending_action', None)
        if not pending or pending.get('action') != 'run_dedupe':
            try:
                await query.edit_message_text('Nessuna azione di deduplica in sospeso.')
            except Exception:
                await query.message.reply_text('Nessuna azione di deduplica in sospeso.')
            return
        await query.edit_message_text('Avvio rimozione duplicati... Ti invierò un messaggio quando è completato.')
        loop = asyncio.get_running_loop()
        try:
            from find_duplicate_helper import find_duplicates as _fd
            removed = await loop.run_in_executor(None, _fd, SAVE_DIR)
            await context.bot.send_message(query.from_user.id, f"Rimossi {removed} file duplicati.")
            return
        except Exception as e:
            await context.bot.send_message(query.from_user.id, f'Errore durante la deduplica: {e}')
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
    await query.edit_message_text('Avvio download... Ti invierò un messaggio quando è completato.')
    loop = asyncio.get_running_loop()
    try:
        if pending['action'] == 'redgifs_profile':
            from redgifs_helper import download_redgifs_profile
            username = pending['username']
            allow_video = pending.get('allow_video', True)
            allow_photo = pending.get('allow_photo', True)
            max_posts = pending.get('max_posts')
            stats = {}
            results = await loop.run_in_executor(None, download_redgifs_profile, username, SAVE_DIR, max_posts, allow_video, allow_photo, stats)
            await context.bot.send_message(query.from_user.id, f"Download completato. File salvati: {len(results)}")
            await post_download_report(update, context, results, stats=stats, label="Redgifs")
            return
        if pending['action'] == 'reddit_profile':
            from reddit_helper import download_reddit_auto
            url = pending.get('url')
            stats = {}
            result = await download_reddit_auto(url, SAVE_DIR, user_id=pending.get('user_id'), stats=stats)
            if isinstance(result, list):
                if result:
                    await context.bot.send_message(query.from_user.id, f"Download completato! File salvati: {len(result)}")
                else:
                    await context.bot.send_message(query.from_user.id, "Nessun media scaricabile trovato nel link Reddit.")
            elif isinstance(result, str):
                await context.bot.send_message(query.from_user.id, result)
            await post_download_report(update, context, result, stats=stats, label="Reddit")
            return
        await context.bot.send_message(query.from_user.id, 'Tipo di download non riconosciuto.')
    except Exception as e:
        await context.bot.send_message(query.from_user.id, f'Errore durante il download: {e}')

async def mapactor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Uso: /mapactor <nome attore> [reddit:user] [redgifs:user]")
        return
    # normalizza: tollera lo spazio dopo i due punti (reddit: user / redgifs: user)
    spec = re.sub(r'(reddit|redgifs|actor):\s+', r'\1:', parts[1])
    tokens = spec.split()
    reddit = ""
    redgifs = ""
    remaining = []
    for t in tokens:
        if t.startswith("reddit:"):
            reddit = t[len("reddit:"):].strip()
        elif t.startswith("redgifs:"):
            redgifs = t[len("redgifs:"):].strip()
        else:
            remaining.append(t)
    actor = " ".join(remaining).strip()
    if not actor:
        await update.message.reply_text("Devi specificare almeno il nome attore.")
        return
    from actor_map import add_actor_mapping
    entry, status = add_actor_mapping(actor, reddit or None, redgifs or None)
    verb = "Unità a mappatura esistente" if status == "merged" else "Mappatura salvata"
    await update.message.reply_text(
        f"{verb}:\nAttore: {entry.get('actor','') or '-'}\n"
        f"Reddit: {entry.get('reddit','') or '-'}\nRedgifs: {entry.get('redgifs','') or '-'}"
    )
    
async def listmap_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    from actor_map import list_actor_mappings
    mappings = list_actor_mappings()
    if not mappings:
        await update.message.reply_text("Nessuna mappatura attore salvata.")
        return
    lines = [f"{i+1}) {m.get('actor','?')} | reddit: {m.get('reddit','') or '-'} | redgifs: {m.get('redgifs','') or '-'}"
             for i, m in enumerate(mappings)]
    await update.message.reply_text(
        "Mappature attore:\n" + "\n".join(lines) +
        "\n\nUsa /editactor <num> ... o /delactor <num> per modificare/rimuovere."
    )

async def editactor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Uso: /editactor <num> [actor:Nome] [reddit:user] [redgifs:user]\n"
            "Esempio: /editactor 1 actor:Aspen Green redgifs:aspencgreen"
        )
        return
    # normalizza: tollera lo spazio dopo i due punti
    spec = re.sub(r'(reddit|redgifs|actor):\s+', r'\1:', parts[1])
    sub = spec.split()
    if not sub[0].isdigit():
        await update.message.reply_text("Il primo argomento deve essere il numero della mappatura (vedi /listmap).")
        return
    identifier = sub[0]
    reddit = None
    redgifs = None
    actor = None
    for t in sub[1:]:
        if t.startswith("reddit:"):
            reddit = t[len("reddit:"):].strip()
        elif t.startswith("redgifs:"):
            redgifs = t[len("redgifs:"):].strip()
        elif t.startswith("actor:"):
            val = t[len("actor:"):].strip()
            actor = val if actor is None else actor + " " + val
        else:
            actor = t if actor is None else actor + " " + t
    from actor_map import update_actor_mapping
    entry, status = update_actor_mapping(identifier, actor=actor, reddit=reddit, redgifs=redgifs)
    if status == "not_found":
        await update.message.reply_text(f"Mappatura numero {identifier} non trovata. Usa /listmap per i numeri corretti.")
        return
    await update.message.reply_text(
        f"Aggiornata:\nAttore: {entry.get('actor','') or '-'}\n"
        f"Reddit: {entry.get('reddit','') or '-'}\nRedgifs: {entry.get('redgifs','') or '-'}"
    )
    
async def delactor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Uso: /delactor <num>  (vedi /listmap)")
        return
    from actor_map import remove_actor_mapping
    ok = remove_actor_mapping(parts[1].strip())
    await update.message.reply_text("Mappatura rimossa." if ok else "Mappatura non trovata.")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN non impostato nelle variabili d'ambiente")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

STARTUP_NOTIFY = os.environ.get("STARTUP_NOTIFY", "false").lower() in ("1", "true", "yes")
STARTUP_CHAT_ID = os.environ.get("STARTUP_CHAT_ID")
if STARTUP_NOTIFY and STARTUP_CHAT_ID:
    try:
        async def _notify_startup():
            await app.bot.send_message(int(STARTUP_CHAT_ID), "Bot avviato e operativo.")
        asyncio.get_event_loop().create_task(_notify_startup())
    except Exception as e:
        print(f"Impossibile inviare notifica di avvio: {e}")

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
app.add_handler(CommandHandler("trovaduplicati", duplicate_check_and_interaction))

async def rehash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized_reply(update)
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Ricalcola gli hash", callback_data='confirm_rehash'),
        InlineKeyboardButton("Annulla", callback_data='cancel_rehash')
    ]])
    context.user_data['pending_action'] = {'action': 'rehash_only'}
    await update.message.reply_text(
        "Se confermi, ricalcolerò gli hash di tutti i file e aggiornerò il DB (operazione potenzialmente lunga). Procedo?",
        reply_markup=keyboard
    )

app.add_handler(CommandHandler("ricalcolahash", rehash_command))
app.add_handler(CommandHandler("rehash", rehash_command))
app.add_handler(CommandHandler("recalculate", rehash_command))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://mega\.nz/(file|folder)/"), handle_mega_link))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://(www\.)?redgifs\.com/(users|watch)/"), handle_redgifs))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://[^\s]*reddit[^\s]*"), handle_reddit_link))
app.add_handler(CommandHandler("mapactor", mapactor_command))
app.add_handler(CommandHandler("listmap", listmap_command))
app.add_handler(CommandHandler("editactor", editactor_command))
app.add_handler(CommandHandler("delactor", delactor_command))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))
app.add_handler(CallbackQueryHandler(handle_confirm_callback))

if __name__ == "__main__":
    try:
        if os.environ.get("WATCHER_ENABLED", "false").lower() in ("1", "true", "yes"):
            start_daily_watcher()
    except Exception as e:
        print(f"Impossibile avviare il watcher: {e}")
    app.run_polling()