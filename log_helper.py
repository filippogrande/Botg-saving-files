"""Logging centralizzato: stdout (docker logs) + file rotante in SAVE_DIR."""
import logging
import os
from logging.handlers import RotatingFileHandler

_configured = False

def setup_logging(save_dir=None, level=logging.INFO):
    global _configured
    if _configured:
        return
    save_dir = save_dir or os.environ.get("SAVE_DIR", "/mnt/truenas-bot")
    os.makedirs(save_dir, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        fh = RotatingFileHandler(os.path.join(save_dir, "botg.log"),
                                 maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as e:
        print(f"Impossibile aprire file di log: {e}")
    _configured = True