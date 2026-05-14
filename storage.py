import json
import shutil
from pathlib import Path


class Storage:
    def __init__(self, chats_file, templates_file, photos_dir):
        self.chats_file = Path(chats_file)
        self.templates_file = Path(templates_file)
        self.photos_dir = Path(photos_dir)
        self.photos_dir.mkdir(parents=True, exist_ok=True)

    def load_chats(self):
        if not self.chats_file.exists():
            return []
        data = json.loads(self.chats_file.read_text(encoding="utf-8"))
        return [{"chat": c, "suffix": ""} if isinstance(c, str) else c for c in data]

    def save_chats(self, chats):
        self.chats_file.write_text(
            json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_templates(self):
        if not self.templates_file.exists():
            return []
        return json.loads(self.templates_file.read_text(encoding="utf-8"))

    def save_templates(self, templates):
        self.templates_file.write_text(
            json.dumps(templates, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def copy_photo(self, src_path, template_id):
        src = Path(src_path)
        dest = self.photos_dir / f"{template_id}{src.suffix}"
        shutil.copy2(src, dest)
        return str(dest)


def make_storage():
    base = Path(__file__).parent / "data"
    return Storage(
        chats_file=base / "chats.json",
        templates_file=base / "templates.json",
        photos_dir=base / "photos",
    )
