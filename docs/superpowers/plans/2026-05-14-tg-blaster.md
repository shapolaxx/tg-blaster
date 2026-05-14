# TG Blaster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop app that sends Telegram bulk messages (text + photo) to a manually managed list of chats using a personal TG account.

**Architecture:** CustomTkinter GUI runs on the main thread; Telethon asyncio event loop runs on a background thread. GUI calls Telethon coroutines via `asyncio.run_coroutine_threadsafe`. Data persisted as JSON files in `data/`.

**Tech Stack:** Python 3.10+, Telethon, CustomTkinter, Pillow, pytest

---

### Task 1: Project scaffold

**Files:**
- Create: `D:\tg-blaster\requirements.txt`
- Create: `D:\tg-blaster\.gitignore`
- Create: `D:\tg-blaster\data\chats.json`
- Create: `D:\tg-blaster\data\templates.json`
- Create: `D:\tg-blaster\data\photos\.gitkeep`

- [ ] **Step 1: Initialize git repo**

```bash
cd D:\tg-blaster
git init
```

- [ ] **Step 2: Create requirements.txt**

```
telethon
customtkinter
pillow
pytest
```

- [ ] **Step 3: Create .gitignore**

```
session.session
config.json
__pycache__/
*.pyc
.pytest_cache/
data/photos/*
!data/photos/.gitkeep
```

- [ ] **Step 4: Create empty data files**

`data/chats.json`:
```json
[]
```

`data/templates.json`:
```json
[]
```

`data/photos/.gitkeep` — empty file.

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore data/chats.json data/templates.json data/photos/.gitkeep
git commit -m "chore: project scaffold"
```

---

### Task 2: storage.py — JSON persistence

**Files:**
- Create: `D:\tg-blaster\storage.py`
- Create: `D:\tg-blaster\tests\__init__.py`
- Create: `D:\tg-blaster\tests\test_storage.py`

- [ ] **Step 1: Write failing tests**

`tests/__init__.py` — empty file.

`tests/test_storage.py`:
```python
import pytest
from pathlib import Path
from storage import Storage

@pytest.fixture
def store(tmp_path):
    return Storage(
        chats_file=tmp_path / "chats.json",
        templates_file=tmp_path / "templates.json",
        photos_dir=tmp_path / "photos",
    )

def test_load_chats_empty(store):
    assert store.load_chats() == []

def test_save_and_load_chats(store):
    store.save_chats(["@chat1", "@chat2"])
    assert store.load_chats() == ["@chat1", "@chat2"]

def test_load_templates_empty(store):
    assert store.load_templates() == []

def test_save_and_load_templates(store):
    templates = [{"id": "abc", "name": "Test", "text": "Hello", "photo": ""}]
    store.save_templates(templates)
    assert store.load_templates() == templates

def test_copy_photo(store, tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"fakejpeg")
    dest_path = store.copy_photo(str(src), "test-id")
    assert Path(dest_path).exists()
    assert Path(dest_path).read_bytes() == b"fakejpeg"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:\tg-blaster
pytest tests/test_storage.py -v
```

Expected: `ModuleNotFoundError: No module named 'storage'`

- [ ] **Step 3: Implement storage.py**

```python
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
        return json.loads(self.chats_file.read_text(encoding="utf-8"))

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_storage.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/
git commit -m "feat: storage module with JSON persistence"
```

---

### Task 3: telegram_client.py — Telethon wrapper

**Files:**
- Create: `D:\tg-blaster\telegram_client.py`

No unit tests — wraps a live external API. Tested manually in Task 5 (auth screen).

- [ ] **Step 1: Create telegram_client.py**

```python
import asyncio
import json
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError


CONFIG_FILE = Path(__file__).parent / "config.json"
SESSION_FILE = str(Path(__file__).parent / "session")


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

    def send_photo_message(self, chat, photo_path, caption):
        self._run(self._client.send_file(chat, photo_path, caption=caption))

    def disconnect(self):
        self._run(self._client.disconnect())
```

- [ ] **Step 2: Commit**

```bash
git add telegram_client.py
git commit -m "feat: Telethon client wrapper"
```

---

### Task 4: Config screen — first-time API setup

**Files:**
- Create: `D:\tg-blaster\screens\__init__.py`
- Create: `D:\tg-blaster\screens\config_screen.py`

- [ ] **Step 1: Create screens/__init__.py**

Empty file.

- [ ] **Step 2: Create screens/config_screen.py**

```python
import customtkinter as ctk
from telegram_client import save_config


class ConfigScreen(ctk.CTkToplevel):
    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.title("Настройка API")
        self.geometry("420x260")
        self.resizable(False, False)
        self.grab_set()
        self._on_done = on_done

        ctk.CTkLabel(self, text="Введите данные с my.telegram.org", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="API ID:").pack(anchor="w", padx=30)
        self._api_id = ctk.CTkEntry(self, width=360)
        self._api_id.pack(padx=30)

        ctk.CTkLabel(self, text="API Hash:").pack(anchor="w", padx=30, pady=(10, 0))
        self._api_hash = ctk.CTkEntry(self, width=360)
        self._api_hash.pack(padx=30)

        self._error = ctk.CTkLabel(self, text="", text_color="red")
        self._error.pack(pady=5)

        ctk.CTkButton(self, text="Сохранить", command=self._save).pack()

    def _save(self):
        api_id = self._api_id.get().strip()
        api_hash = self._api_hash.get().strip()
        if not api_id.isdigit() or not api_hash:
            self._error.configure(text="Заполните оба поля корректно")
            return
        save_config(api_id, api_hash)
        self.destroy()
        self._on_done()
```

- [ ] **Step 3: Commit**

```bash
git add screens/
git commit -m "feat: config screen for API credentials"
```

---

### Task 5: Auth screen — Telegram login

**Files:**
- Create: `D:\tg-blaster\screens\auth_screen.py`

- [ ] **Step 1: Create screens/auth_screen.py**

```python
import customtkinter as ctk


class AuthScreen(ctk.CTkToplevel):
    def __init__(self, parent, tg_client, on_done):
        super().__init__(parent)
        self.title("Вход в Telegram")
        self.geometry("420x320")
        self.resizable(False, False)
        self.grab_set()
        self._tg = tg_client
        self._on_done = on_done

        ctk.CTkLabel(self, text="Войдите в Telegram аккаунт", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="Номер телефона (напр. +79001234567):").pack(anchor="w", padx=30)
        self._phone = ctk.CTkEntry(self, width=360)
        self._phone.pack(padx=30)

        ctk.CTkButton(self, text="Получить код", command=self._send_code).pack(pady=10)

        ctk.CTkLabel(self, text="Код из Telegram:").pack(anchor="w", padx=30)
        self._code = ctk.CTkEntry(self, width=360)
        self._code.pack(padx=30)
        self._code.configure(state="disabled")

        self._login_btn = ctk.CTkButton(self, text="Войти", command=self._sign_in, state="disabled")
        self._login_btn.pack(pady=10)

        self._status = ctk.CTkLabel(self, text="")
        self._status.pack()

    def _send_code(self):
        phone = self._phone.get().strip()
        if not phone:
            self._status.configure(text="Введите номер телефона", text_color="red")
            return
        try:
            self._tg.send_code(phone)
            self._code.configure(state="normal")
            self._login_btn.configure(state="normal")
            self._status.configure(text="Код отправлен", text_color="green")
        except Exception as e:
            self._status.configure(text=f"Ошибка: {e}", text_color="red")

    def _sign_in(self):
        code = self._code.get().strip()
        if not code:
            self._status.configure(text="Введите код", text_color="red")
            return
        try:
            self._tg.sign_in(code)
            self.destroy()
            self._on_done()
        except Exception as e:
            self._status.configure(text=f"Ошибка: {e}", text_color="red")
```

- [ ] **Step 2: Commit**

```bash
git add screens/auth_screen.py
git commit -m "feat: auth screen for Telegram login"
```

---

### Task 6: Templates tab

**Files:**
- Create: `D:\tg-blaster\tabs\__init__.py`
- Create: `D:\tg-blaster\tabs\templates_tab.py`

- [ ] **Step 1: Create tabs/__init__.py**

Empty file.

- [ ] **Step 2: Create tabs/templates_tab.py**

```python
import uuid
import customtkinter as ctk
from tkinter import filedialog, messagebox


class TemplateDialog(ctk.CTkToplevel):
    def __init__(self, parent, storage, template=None, on_save=None):
        super().__init__(parent)
        self.title("Шаблон")
        self.geometry("500x440")
        self.resizable(False, False)
        self.grab_set()
        self._storage = storage
        self._template = template
        self._on_save = on_save
        self._photo_path = template["photo"] if template else ""

        ctk.CTkLabel(self, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        self._name = ctk.CTkEntry(self, width=460)
        self._name.pack(padx=20)
        if template:
            self._name.insert(0, template["name"])

        ctk.CTkLabel(self, text="Текст сообщения:").pack(anchor="w", padx=20, pady=(10, 0))
        self._text = ctk.CTkTextbox(self, width=460, height=160)
        self._text.pack(padx=20)
        if template:
            self._text.insert("1.0", template["text"])

        self._photo_label = ctk.CTkLabel(self, text=self._photo_display(), wraplength=440)
        self._photo_label.pack(pady=(8, 2))

        ctk.CTkButton(self, text="Выбрать фото", command=self._pick_photo).pack()
        ctk.CTkButton(self, text="Сохранить", command=self._save).pack(pady=12)

    def _photo_display(self):
        return f"Фото: {self._photo_path}" if self._photo_path else "Фото не выбрано"

    def _pick_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            self._photo_path = path
            self._photo_label.configure(text=self._photo_display())

    def _save(self):
        name = self._name.get().strip()
        text = self._text.get("1.0", "end").strip()
        if not name or not text:
            messagebox.showwarning("Ошибка", "Заполните название и текст")
            return
        tid = self._template["id"] if self._template else str(uuid.uuid4())
        photo = self._storage.copy_photo(self._photo_path, tid) if self._photo_path else ""
        templates = self._storage.load_templates()
        entry = {"id": tid, "name": name, "text": text, "photo": photo}
        if self._template:
            templates = [entry if t["id"] == tid else t for t in templates]
        else:
            templates.append(entry)
        self._storage.save_templates(templates)
        self.destroy()
        if self._on_save:
            self._on_save()


class TemplatesTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage
        self._selected = None

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btn_frame, text="Добавить", width=110, command=self._add).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Изменить", width=110, command=self._edit).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Удалить", width=110, command=self._delete).pack(side="left", padx=4)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh()

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._selected = None
        self._buttons = {}
        for t in self._storage.load_templates():
            btn = ctk.CTkButton(
                self._listbox, text=t["name"], anchor="w",
                fg_color="transparent", text_color=("black", "white"),
                hover_color=("gray80", "gray30"),
                command=lambda tid=t["id"]: self._select(tid),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[t["id"]] = btn

    def _select(self, tid):
        if self._selected and self._selected in self._buttons:
            self._buttons[self._selected].configure(fg_color="transparent")
        self._selected = tid
        self._buttons[tid].configure(fg_color=("gray75", "gray25"))

    def _add(self):
        TemplateDialog(self, self._storage, on_save=self._refresh)

    def _edit(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите шаблон")
            return
        template = next((t for t in self._storage.load_templates() if t["id"] == self._selected), None)
        if template:
            TemplateDialog(self, self._storage, template=template, on_save=self._refresh)

    def _delete(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите шаблон")
            return
        if messagebox.askyesno("Удалить", "Удалить шаблон?"):
            templates = [t for t in self._storage.load_templates() if t["id"] != self._selected]
            self._storage.save_templates(templates)
            self._refresh()
```

- [ ] **Step 3: Commit**

```bash
git add tabs/
git commit -m "feat: templates tab with add/edit/delete"
```

---

### Task 7: Chats tab

**Files:**
- Create: `D:\tg-blaster\tabs\chats_tab.py`

- [ ] **Step 1: Create tabs/chats_tab.py**

```python
import customtkinter as ctk
from tkinter import messagebox, simpledialog


class ChatsTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage
        self._selected = None
        self._buttons = {}

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btn_frame, text="Добавить", width=110, command=self._add).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Удалить", width=110, command=self._delete).pack(side="left", padx=4)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh()

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._selected = None
        self._buttons = {}
        for chat in self._storage.load_chats():
            btn = ctk.CTkButton(
                self._listbox, text=chat, anchor="w",
                fg_color="transparent", text_color=("black", "white"),
                hover_color=("gray80", "gray30"),
                command=lambda c=chat: self._select(c),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[chat] = btn

    def _select(self, chat):
        if self._selected and self._selected in self._buttons:
            self._buttons[self._selected].configure(fg_color="transparent")
        self._selected = chat
        self._buttons[chat].configure(fg_color=("gray75", "gray25"))

    def _add(self):
        val = simpledialog.askstring("Добавить чат", "Введите @username или ссылку t.me/...")
        if val:
            val = val.strip()
            chats = self._storage.load_chats()
            if val not in chats:
                chats.append(val)
                self._storage.save_chats(chats)
            self._refresh()

    def _delete(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите чат")
            return
        if messagebox.askyesno("Удалить", f"Удалить {self._selected}?"):
            chats = [c for c in self._storage.load_chats() if c != self._selected]
            self._storage.save_chats(chats)
            self._refresh()
```

- [ ] **Step 2: Commit**

```bash
git add tabs/chats_tab.py
git commit -m "feat: chats tab with add/delete"
```

---

### Task 8: Broadcast tab

**Files:**
- Create: `D:\tg-blaster\tabs\broadcast_tab.py`

- [ ] **Step 1: Create tabs/broadcast_tab.py**

```python
import threading
import time
import customtkinter as ctk
from tkinter import filedialog
from telethon.errors import FloodWaitError


class BroadcastTab(ctk.CTkFrame):
    def __init__(self, parent, storage, tg_client):
        super().__init__(parent)
        self._storage = storage
        self._tg = tg_client
        self._override_photo = None

        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Шаблон:").pack(side="left", padx=(0, 5))
        self._template_var = ctk.StringVar()
        self._template_menu = ctk.CTkOptionMenu(
            top, variable=self._template_var, values=["—"],
            command=self._on_template_select, width=220,
        )
        self._template_menu.pack(side="left")
        ctk.CTkButton(top, text="↻", width=36, command=self.refresh_templates).pack(side="left", padx=5)

        preview = ctk.CTkFrame(self)
        preview.pack(fill="x", padx=10)
        self._preview_text = ctk.CTkLabel(preview, text="", wraplength=460, justify="left")
        self._preview_text.pack(anchor="w", pady=(8, 2))
        self._photo_label = ctk.CTkLabel(preview, text="Фото: не выбрано", text_color="gray")
        self._photo_label.pack(anchor="w")
        ctk.CTkButton(preview, text="Сменить фото (только для этой рассылки)", command=self._change_photo).pack(anchor="w", pady=6)

        ctk.CTkButton(self, text="🚀  Разослать по всем чатам", height=40, command=self._start_broadcast).pack(pady=8)

        self._log = ctk.CTkTextbox(self, state="disabled")
        self._log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh_templates()

    def refresh_templates(self):
        templates = self._storage.load_templates()
        names = [t["name"] for t in templates]
        self._template_menu.configure(values=names if names else ["—"])
        if names:
            self._template_var.set(names[0])
            self._on_template_select(names[0])

    def _on_template_select(self, name):
        self._override_photo = None
        template = next((t for t in self._storage.load_templates() if t["name"] == name), None)
        if template:
            self._preview_text.configure(text=template["text"] or "")
            self._photo_label.configure(text=f"Фото: {template['photo'] or 'нет'}")

    def _change_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            self._override_photo = path
            self._photo_label.configure(text=f"Фото (временное): {path}")

    def _log_write(self, msg):
        self.after(0, self._log_write_main, msg)

    def _log_write_main(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _start_broadcast(self):
        name = self._template_var.get()
        template = next((t for t in self._storage.load_templates() if t["name"] == name), None)
        if not template:
            self._log_write("Выберите шаблон")
            return
        chats = self._storage.load_chats()
        if not chats:
            self._log_write("Список чатов пуст — добавьте чаты во вкладке Чаты")
            return
        photo = self._override_photo or template["photo"]
        if not photo:
            self._log_write("У шаблона нет фото — добавьте фото в шаблон или выберите временное")
            return
        threading.Thread(
            target=self._broadcast,
            args=(chats, template["text"], photo),
            daemon=True,
        ).start()

    def _broadcast(self, chats, text, photo):
        self._log_write(f"Начинаю рассылку в {len(chats)} чатов...")
        for i, chat in enumerate(chats, 1):
            try:
                self._tg.send_photo_message(chat, photo, text)
                self._log_write(f"[{i}/{len(chats)}] ✓ {chat}")
            except FloodWaitError as e:
                self._log_write(f"[{i}/{len(chats)}] FloodWait {e.seconds}s — жду...")
                time.sleep(e.seconds)
                try:
                    self._tg.send_photo_message(chat, photo, text)
                    self._log_write(f"[{i}/{len(chats)}] ✓ {chat} (после FloodWait)")
                except Exception as e2:
                    self._log_write(f"[{i}/{len(chats)}] ✗ {chat}: {e2}")
            except Exception as e:
                self._log_write(f"[{i}/{len(chats)}] ✗ {chat}: {e}")
            if i < len(chats):
                time.sleep(5)
        self._log_write("✅ Готово!")
```

- [ ] **Step 2: Commit**

```bash
git add tabs/broadcast_tab.py
git commit -m "feat: broadcast tab with send loop and real-time log"
```

---

### Task 9: main.py — startup + main window

**Files:**
- Create: `D:\tg-blaster\main.py`

- [ ] **Step 1: Create main.py**

```python
import customtkinter as ctk
from storage import make_storage
from telegram_client import TGClient, load_config
from screens.config_screen import ConfigScreen
from screens.auth_screen import AuthScreen
from tabs.templates_tab import TemplatesTab
from tabs.chats_tab import ChatsTab
from tabs.broadcast_tab import BroadcastTab


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Blaster")
        self.geometry("720x620")
        self._storage = make_storage()
        self._tg = None
        self.withdraw()
        self.after(100, self._startup)

    def _startup(self):
        config = load_config()
        if not config:
            ConfigScreen(self, on_done=self._startup)
            return
        api_id, api_hash = config
        self._tg = TGClient(api_id, api_hash)
        self._tg.start_loop()
        self._tg.connect()
        if not self._tg.is_authorized():
            AuthScreen(self, self._tg, on_done=self._open_main)
        else:
            self._open_main()

    def _open_main(self):
        self.deiconify()
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tabs.add("Шаблоны")
        tab2 = tabs.add("Чаты")
        tab3 = tabs.add("Рассылка")

        TemplatesTab(tab1, self._storage).pack(fill="both", expand=True)
        ChatsTab(tab2, self._storage).pack(fill="both", expand=True)
        BroadcastTab(tab3, self._storage, self._tg).pack(fill="both", expand=True)

    def _on_closing(self):
        if self._tg:
            self._tg.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app._on_closing)
    app.mainloop()
```

- [ ] **Step 2: Run the app manually**

```bash
cd D:\tg-blaster
python main.py
```

Expected behaviour:
- No `config.json` → config screen opens, enter API_ID + API_HASH from my.telegram.org
- No session → auth screen opens, enter phone number + Telegram code
- Main window opens with tabs: Шаблоны / Чаты / Рассылка

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main app entry point with startup flow"
```

---

### Task 10: Manual smoke test

- [ ] **Step 1: Add a template**

Tab "Шаблоны" → Добавить → fill in name, text, choose a photo → Сохранить.
Expected: template appears in the list with its name.

- [ ] **Step 2: Add a test chat**

Tab "Чаты" → Добавить → enter `@username` of a chat you have access to.
Expected: chat appears in the list.

- [ ] **Step 3: Send broadcast**

Tab "Рассылка" → select template from dropdown → click "Разослать по всем чатам".
Expected: log shows `✓ @username` for each chat; message + photo received in Telegram.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: smoke test complete, app working"
```
