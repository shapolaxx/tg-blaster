import re
import asyncio
import json
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError


# ── Custom emoji helpers ───────────────────────────────────────────────────────

_EMOJI_RE = re.compile(r'\[(.+?):(\d{10,})\]')


def _parse_emoji_entities(text):
    """Parse [CHAR:DOCUMENT_ID] notation and return (clean_text, entities | None)."""
    from telethon.tl.types import MessageEntityCustomEmoji
    entities = []
    parts = []
    pos = 0
    utf16_off = 0
    for m in _EMOJI_RE.finditer(text):
        before = text[pos:m.start()]
        parts.append(before)
        utf16_off += len(before.encode("utf-16-le")) // 2
        char = m.group(1)
        doc_id = int(m.group(2))
        char_len = len(char.encode("utf-16-le")) // 2
        entities.append(MessageEntityCustomEmoji(offset=utf16_off, length=char_len, document_id=doc_id))
        parts.append(char)
        utf16_off += char_len
        pos = m.end()
    parts.append(text[pos:])
    return "".join(parts), (entities if entities else None)


def _app_base() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


CONFIG_FILE = _app_base() / "config.json"
SESSION_FILE = str(_app_base() / "session")


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

    def sign_in_password(self, password):
        self._run(self._client.sign_in(password=password))

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

    def send_photo_message(self, url, photo_path, caption) -> int:
        chat, topic_id = parse_chat_link(url)
        clean, entities = _parse_emoji_entities(caption)
        kwargs = {"caption": clean}
        if topic_id:
            kwargs["reply_to"] = topic_id
        if entities:
            kwargs["formatting_entities"] = entities
        msg = self._run(self._client.send_file(chat, photo_path, **kwargs))
        return msg.id

    def send_message(self, url, text) -> int:
        chat, topic_id = parse_chat_link(url)
        clean, entities = _parse_emoji_entities(text)
        kwargs = {}
        if topic_id:
            kwargs["reply_to"] = topic_id
        if entities:
            kwargs["formatting_entities"] = entities
        msg = self._run(self._client.send_message(chat, clean, **kwargs))
        return msg.id

    def delete_messages(self, url, msg_ids: list[int]):
        chat, _ = parse_chat_link(url)
        self._run(self._client.delete_messages(chat, msg_ids))

    def get_custom_emoji_packs(self):
        """Return [(pack_title, [(char, doc_id), ...]), ...] for user's emoji packs."""
        from telethon.tl.functions.messages import GetAllStickersRequest, GetStickerSetRequest
        from telethon.tl.types import InputStickerSetID
        all_stickers = self._run(self._client(GetAllStickersRequest(0)))
        emoji_sets = [s for s in all_stickers.sets if getattr(s, "emojis", False)]
        packs = []
        for s in emoji_sets[:20]:
            try:
                full = self._run(self._client(GetStickerSetRequest(
                    stickerset=InputStickerSetID(id=s.id, access_hash=s.access_hash),
                    hash=0,
                )))
                doc_to_char = {}
                for pack in full.packs:
                    for doc_id in pack.documents:
                        doc_to_char[doc_id] = pack.emoticon
                items = [(doc_to_char.get(d.id, "?"), d.id) for d in full.documents]
                if items:
                    packs.append((s.title, items))
            except Exception:
                continue
        return packs

    def load_emoji_pack_by_name(self, name_or_url):
        """Load any emoji/sticker pack by short name or t.me/addemoji/ URL.
        Returns (title, [(char, doc_id), ...]).
        """
        from telethon.tl.functions.messages import GetStickerSetRequest
        from telethon.tl.types import InputStickerSetShortName
        name = name_or_url.strip()
        for prefix in (
            "https://t.me/addemoji/", "t.me/addemoji/",
            "https://t.me/addstickers/", "t.me/addstickers/",
        ):
            if name.lower().startswith(prefix):
                name = name[len(prefix):]
                break
        name = name.rstrip("/")
        full = self._run(self._client(GetStickerSetRequest(
            stickerset=InputStickerSetShortName(short_name=name),
            hash=0,
        )))
        doc_to_char = {}
        for pack in full.packs:
            for doc_id in pack.documents:
                doc_to_char[doc_id] = pack.emoticon
        items = [(doc_to_char.get(d.id, "?"), d.id) for d in full.documents]
        return full.set.title, items

    def logout(self):
        try:
            self._run(self._client.log_out())
        except Exception:
            pass

    def disconnect(self):
        self._run(self._client.disconnect())
