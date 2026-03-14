import os
import requests
import logging

logger = logging.getLogger(__name__)

def _split_message(message: str, limit: int = 4000) -> list[str]:
    parts = []
    while len(message) > limit:
        split_index = message.rfind("\n", 0, limit)
        if split_index == -1:
            split_index = limit
        parts.append(message[:split_index])
        message = message[split_index:]
    parts.append(message)
    return parts

def _get_creds() -> tuple[str, str]:
    return os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")

def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """Send a text message. Returns True on success."""
    bot_token, chat_id = _get_creds()
    if not bot_token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return False

    url   = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    parts = _split_message(text)
    success = True
    for part in parts:
        try:
            r = requests.post(url, data={
                "chat_id": chat_id, "text": part, "parse_mode": parse_mode
            }, timeout=10)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Telegram send_message failed: {e}")
            success = False
    return success

def send_photo(photo_path: str, caption: str = "", parse_mode: str = "HTML") -> bool:
    """Send a photo file. Used by smart money flow chart."""
    bot_token, chat_id = _get_creds()
    if not bot_token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            r = requests.post(url, data={
                "chat_id": chat_id, "caption": caption, "parse_mode": parse_mode
            }, files={"photo": f}, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send_photo failed: {e}")
        return False