import re
import asyncio
import json
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError


CONFIG_FILE = Path(__file__).parent / "config.json"
SESSION_FILE = str(Path(__file__).parent / "session")


def parse_chat_link(url):
    """Parse a t.me link into (chat_identifier, topic_id).

    Handles:
      https://t.me/c/1483715443/605  -> (-1001483715443, 605)
      t.me/lzt_service/1420          -> ('@lzt_service', 1420)
      https://t.me/+InviteHash       -> (url, None)
      @username                      -> ('@username', None)
    """
    url = url.strip()

    # Private group with topic: t.me/c/CHATID/TOPICID
    m = re.match(r'(?:https?://)?t\.me/c/(\d+)/(\d+)', url)
    if m:
        return int(f"-100{m.group(1)}"), int(m.group(2))

    # Public group with topic: t.me/username/TOPICID
    m = re.match(r'(?:https?://)?t\.me/([A-Za-z0-9_]+)/(\d+)', url)
    if m:
        username = m.group(1)
        return f"@{username}", int(m.group(2))

    # Plain t.me link without topic: t.me/username
    m = re.match(r'(?:https?://)?t\.me/([A-Za-z0-9_]+)$', url)
    if m:
        return f"@{m.group(1)}", None

    # Invite link: t.me/+hash
    m = re.match(r'(?:https?://)?t\.me/\+(.+)', url)
    if m:
        return url, None

    # Plain @username or bare username
    if not url.startswith('@'):
        url = f"@{url}"
    return url, None


def load_config():
    if not CONFIG_FILE.exists():
        return None
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return data.get("api_id"), data.get("api_hash")


def save_config(api_id, api_hash):
    CONFIG_FILE.write_text(
        json.dumps({"api_id": int(api_id), "api_hash": api_hash}, indent=2),
        encoding="utf-8",
    )


class TGClient:
    def __init__(self, api_id, api_hash):
        self._client = TelegramClient(SESSION_FILE, api_id, api_hash)
        self._loop = asyncio.new_event_loop()
        self._phone = None

    def start_loop(self):
        import threading
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=30)

    def connect(self):
        self._run(self._client.connect())

    def is_authorized(self):
        return self._run(self._client.is_user_authorized())

    def send_code(self, phone):
        self._phone = phone
        self._run(self._client.send_code_request(phone))

    def sign_in(self, code):
        self._run(self._client.sign_in(self._phone, code))

    def get_chat_title(self, url):
        try:
            chat, topic_id = parse_chat_link(url)
            entity = self._run(self._client.get_entity(chat))
            title = getattr(entity, "title", None) or getattr(entity, "first_name", str(url))
            if topic_id:
                title = f"{title} (тема #{topic_id})"
            return title
        except Exception:
            return None

    def send_photo_message(self, url, photo_path, caption):
        chat, topic_id = parse_chat_link(url)
        kwargs = {"caption": caption}
        if topic_id:
            kwargs["reply_to"] = topic_id
        self._run(self._client.send_file(chat, photo_path, **kwargs))

    def disconnect(self):
        self._run(self._client.disconnect())
