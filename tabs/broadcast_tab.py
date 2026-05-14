import datetime
import random
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
        self._broadcasting = False

        # Template selector
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Шаблон:").pack(side="left", padx=(0, 5))
        self._template_var = ctk.StringVar()
        self._template_menu = ctk.CTkOptionMenu(
            top, variable=self._template_var, values=["—"],
            command=self._on_template_select, width=220,
        )
        self._template_menu.pack(side="left")
        ctk.CTkButton(top, text="↻", width=36, command=self.refresh_templates).pack(side="left", padx=5)

        # Preview
        preview = ctk.CTkFrame(self)
        preview.pack(fill="x", padx=10)
        self._preview_text = ctk.CTkLabel(preview, text="", wraplength=460, justify="left")
        self._preview_text.pack(anchor="w", pady=(8, 2))
        self._photo_label = ctk.CTkLabel(preview, text="Фото: не выбрано", text_color="gray")
        self._photo_label.pack(anchor="w")
        ctk.CTkButton(preview, text="Сменить фото (только для этой рассылки)", command=self._change_photo).pack(anchor="w", pady=6)

        # Broadcast button
        self._send_btn = ctk.CTkButton(self, text="🚀  Разослать по всем чатам", height=40, command=self._start_broadcast)
        self._send_btn.pack(pady=(6, 2))

        # Schedule frame
        sched_frame = ctk.CTkFrame(self)
        sched_frame.pack(fill="x", padx=10, pady=4)
        self._sched_var = ctk.BooleanVar()
        ctk.CTkCheckBox(sched_frame, text="Расписание", variable=self._sched_var).pack(side="left", padx=(6, 4))
        ctk.CTkLabel(sched_frame, text="Время:").pack(side="left")
        self._sched_time = ctk.CTkEntry(sched_frame, width=64, placeholder_text="10:00")
        self._sched_time.pack(side="left", padx=(4, 6))
        ctk.CTkButton(sched_frame, text="Сохранить", width=90, command=self._save_schedule).pack(side="left")
        self._sched_status = ctk.CTkLabel(sched_frame, text="", text_color="gray")
        self._sched_status.pack(side="left", padx=8)

        # Log
        self._log = ctk.CTkTextbox(self, state="disabled")
        self._log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        self.refresh_templates()
        self._load_schedule()
        self._schedule_check()

    # ── Templates ──────────────────────────────────────────────────────────

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

    # ── Schedule ───────────────────────────────────────────────────────────

    def _load_schedule(self):
        sched = self._storage.load_schedule()
        self._sched_var.set(sched.get("enabled", False))
        t = sched.get("time", "")
        if t:
            self._sched_time.insert(0, t)
        self._update_sched_status(sched)

    def _save_schedule(self):
        sched = self._storage.load_schedule()
        sched["enabled"] = self._sched_var.get()
        sched["time"] = self._sched_time.get().strip()
        sched["template"] = self._template_var.get()
        self._storage.save_schedule(sched)
        self._update_sched_status(sched)

    def _update_sched_status(self, sched=None):
        if sched is None:
            sched = self._storage.load_schedule()
        if sched.get("enabled") and sched.get("time"):
            self._sched_status.configure(text=f"Активно: каждый день в {sched['time']}", text_color="#4CAF50")
        else:
            self._sched_status.configure(text="Выключено", text_color="gray")

    def _schedule_check(self):
        sched = self._storage.load_schedule()
        if sched.get("enabled") and sched.get("time") and not self._broadcasting:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            today = now.strftime("%Y-%m-%d")
            if current_time == sched.get("time") and sched.get("last_sent_date") != today:
                sched["last_sent_date"] = today
                self._storage.save_schedule(sched)
                if sched.get("template"):
                    self._template_var.set(sched["template"])
                self._log_write(f"⏰ Автоматическая рассылка по расписанию ({current_time})")
                self._start_broadcast()
        self.after(30000, self._schedule_check)

    # ── Broadcast ──────────────────────────────────────────────────────────

    def _log_write(self, msg):
        self.after(0, self._log_write_main, msg)

    def _log_write_main(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _start_broadcast(self):
        if self._broadcasting:
            return
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
        self._broadcasting = True
        self._send_btn.configure(state="disabled", text="Отправка...")
        threading.Thread(
            target=self._broadcast,
            args=(chats, template["text"], photo, name),
            daemon=True,
        ).start()

    def _broadcast(self, chats, text, photo, template_name):
        self._log_write(f"Начинаю рассылку в {len(chats)} чатов...")
        success = 0
        errors = 0
        for i, entry in enumerate(chats, 1):
            chat = entry["chat"]
            suffix = entry.get("suffix", "")
            caption = f"{text}\n{suffix}" if suffix else text
            try:
                self._tg.send_photo_message(chat, photo, caption)
                display = entry.get("name") or chat
                self._log_write(f"[{i}/{len(chats)}] ✓ {display}")
                success += 1
            except FloodWaitError as e:
                self._log_write(f"[{i}/{len(chats)}] FloodWait {e.seconds}s — жду...")
                time.sleep(e.seconds)
                try:
                    self._tg.send_photo_message(chat, photo, caption)
                    self._log_write(f"[{i}/{len(chats)}] ✓ {chat} (после FloodWait)")
                    success += 1
                except Exception as e2:
                    self._log_write(f"[{i}/{len(chats)}] ✗ {chat}: {e2}")
                    errors += 1
            except Exception as e:
                self._log_write(f"[{i}/{len(chats)}] ✗ {chat}: {e}")
                errors += 1
            if i < len(chats):
                delay = random.uniform(3, 8)
                time.sleep(delay)

        self._log_write(f"✅ Готово! Успешно: {success}, ошибок: {errors}")
        self._storage.add_history_entry({
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "template": template_name,
            "total": len(chats),
            "success": success,
            "errors": errors,
        })
        self.after(0, self._broadcast_done)

    def _broadcast_done(self):
        self._broadcasting = False
        self._send_btn.configure(state="normal", text="🚀  Разослать по всем чатам")
