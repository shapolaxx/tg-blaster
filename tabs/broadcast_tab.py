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
        for i, entry in enumerate(chats, 1):
            chat = entry["chat"]
            suffix = entry.get("suffix", "")
            caption = f"{text}\n{suffix}" if suffix else text
            try:
                self._tg.send_photo_message(chat, photo, caption)
                self._log_write(f"[{i}/{len(chats)}] ✓ {chat}")
            except FloodWaitError as e:
                self._log_write(f"[{i}/{len(chats)}] FloodWait {e.seconds}s — жду...")
                time.sleep(e.seconds)
                try:
                    self._tg.send_photo_message(chat, photo, caption)
                    self._log_write(f"[{i}/{len(chats)}] ✓ {chat} (после FloodWait)")
                except Exception as e2:
                    self._log_write(f"[{i}/{len(chats)}] ✗ {chat}: {e2}")
            except Exception as e:
                self._log_write(f"[{i}/{len(chats)}] ✗ {chat}: {e}")
            if i < len(chats):
                time.sleep(5)
        self._log_write("✅ Готово!")
