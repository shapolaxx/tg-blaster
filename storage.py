import json
import shutil
import threading
from pathlib import Path


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


class Storage:
    def __init__(self, chats_file, templates_file, photos_dir, history_file=None, schedule_file=None):
        self.chats_file = Path(chats_file)
        self.templates_file = Path(templates_file)
        self.photos_dir = Path(photos_dir)
        self.history_file = Path(history_file) if history_file else self.chats_file.parent / "history.json"
        self.schedule_file = Path(schedule_file) if schedule_file else self.chats_file.parent / "schedule.json"
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def load_chats(self):
        if not self.chats_file.exists():
            return []
        data = json.loads(self.chats_file.read_text(encoding="utf-8"))
        result = []
        for c in data:
            if isinstance(c, str):
                result.append({"chat": c, "suffix": "", "enabled": True})
            else:
                c.setdefault("enabled", True)
                result.append(c)
        return result

    def save_chats(self, chats):
        _atomic_write(self.chats_file, json.dumps(chats, ensure_ascii=False, indent=2))

    def load_templates(self):
        if not self.templates_file.exists():
            return []
        return json.loads(self.templates_file.read_text(encoding="utf-8"))

    def save_templates(self, templates):
        _atomic_write(self.templates_file, json.dumps(templates, ensure_ascii=False, indent=2))

    def copy_photo(self, src_path, template_id):
        src = Path(src_path)
        dest = self.photos_dir / f"{template_id}{src.suffix}"
        shutil.copy2(src, dest)
        return str(dest)

    def load_history(self):
        if not self.history_file.exists():
            return []
        return json.loads(self.history_file.read_text(encoding="utf-8"))

    def save_history(self, history):
        _atomic_write(self.history_file, json.dumps(history, ensure_ascii=False, indent=2))

    def add_history_entry(self, entry):
        with self._lock:
            history = self.load_history()
            history.append(entry)
            self.save_history(history)

    def _stats_path(self) -> Path:
        return self.chats_file.parent / "chat_stats.json"

    def load_chat_stats(self):
        path = self._stats_path()
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def record_chat_stat(self, chat, success):
        import time
        with self._lock:
            stats = self.load_chat_stats()
            if chat not in stats:
                stats[chat] = {"ok": 0, "error": 0}
            stats[chat]["ok" if success else "error"] += 1
            stats[chat]["last_sent_at"] = time.time()
            _atomic_write(self._stats_path(), json.dumps(stats, ensure_ascii=False, indent=2))

    def get_chat_last_sent(self, chat: str) -> float:
        return self.load_chat_stats().get(chat, {}).get("last_sent_at", 0.0)

    def load_schedule(self):
        if not self.schedule_file.exists():
            return {"enabled": False, "time": "10:00", "template": "", "last_sent_date": ""}
        return json.loads(self.schedule_file.read_text(encoding="utf-8"))

    def save_schedule(self, schedule):
        _atomic_write(self.schedule_file, json.dumps(schedule, ensure_ascii=False, indent=2))


def _app_base() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def make_storage():
    base = _app_base() / "data"
    return Storage(
        chats_file=base / "chats.json",
        templates_file=base / "templates.json",
        photos_dir=base / "photos",
    )
