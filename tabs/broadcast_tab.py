import datetime
import random
import threading
import time
import customtkinter as ctk
from tkinter import filedialog
from telethon.errors import FloodWaitError
from utils.toast import show_toast
from utils.paste_fix import fix_entry


class BroadcastTab(ctk.CTkFrame):
    def __init__(self, parent, storage, tg_client):
        super().__init__(parent)
        self._storage = storage
        self._tg = tg_client
        self._override_media = None
        self._broadcasting = False
        self._stop_event = threading.Event()
        self._failed_entries = []

        # Template selector
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Шаблон:").pack(side="left", padx=(0, 5))
        self._template_var = ctk.StringVar()
        self._template_menu = ctk.CTkOptionMenu(
            top, variable=self._template_var, values=["—"],
            command=self._on_template_select, width=200,
        )
        self._template_menu.pack(side="left")
        ctk.CTkButton(top, text="↻", width=36, command=self.refresh_templates).pack(side="left", padx=5)

        # Preview
        preview = ctk.CTkFrame(self)
        preview.pack(fill="x", padx=10)
        self._preview_text = ctk.CTkLabel(preview, text="", wraplength=460, justify="left")
        self._preview_text.pack(anchor="w", pady=(8, 2))
        self._media_label = ctk.CTkLabel(preview, text="Медиа: не выбрано", text_color="gray")
        self._media_label.pack(anchor="w")
        ctk.CTkButton(
            preview, text="Сменить медиа (только для этой рассылки)",
            command=self._change_media,
        ).pack(anchor="w", pady=(4, 2))

        # Test send row
        test_row = ctk.CTkFrame(preview, fg_color="transparent")
        test_row.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(test_row, text="Тест в:", text_color="gray").pack(side="left", padx=(0, 6))
        self._test_chat = ctk.CTkEntry(test_row, placeholder_text="@chat или t.me/...", width=200)
        self._test_chat.pack(side="left")
        fix_entry(self._test_chat)
        self._test_btn = ctk.CTkButton(
            test_row, text="Отправить", width=90, command=self._test_send
        )
        self._test_btn.pack(side="left", padx=6)

        # Action buttons row
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(6, 2))
        self._send_btn = ctk.CTkButton(
            action_row, text="Разослать по всем чатам", height=40,
            fg_color="#F97316", hover_color="#EA6C0A",
            command=self._start_broadcast,
        )
        self._send_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._retry_btn = ctk.CTkButton(
            action_row, text="Повторить ошибки", height=40, width=140,
            fg_color="#6B7280", hover_color="#4B5563",
            state="disabled",
            command=self._retry_failed,
        )
        self._retry_btn.pack(side="left")

        # Progress bar
        self._progress = ctk.CTkProgressBar(self)
        self._progress.set(0)
        self._progress.pack(fill="x", padx=10, pady=(4, 0))

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

        # Delay settings
        delay_row = ctk.CTkFrame(self, fg_color="transparent")
        delay_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(delay_row, text="Задержка:", text_color="gray").pack(side="left", padx=(4, 6))
        self._delay_min = ctk.CTkEntry(delay_row, width=52, placeholder_text="3")
        self._delay_min.pack(side="left")
        fix_entry(self._delay_min)
        ctk.CTkLabel(delay_row, text="—", text_color="gray").pack(side="left", padx=4)
        self._delay_max = ctk.CTkEntry(delay_row, width=52, placeholder_text="8")
        self._delay_max.pack(side="left")
        fix_entry(self._delay_max)
        ctk.CTkLabel(delay_row, text="сек", text_color="gray").pack(side="left", padx=(4, 0))

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
        self._override_media = None
        template = next((t for t in self._storage.load_templates() if t["name"] == name), None)
        if template:
            self._preview_text.configure(text=template["text"] or "")
            media = template.get("photo") or ""
            self._media_label.configure(text=f"Медиа: {media or 'нет'}")

    def _change_media(self):
        path = filedialog.askopenfilename(
            filetypes=[("Media", "*.jpg *.jpeg *.png *.mp4 *.mov *.gif *.webp")]
        )
        if path:
            self._override_media = path
            self._media_label.configure(text=f"Медиа (временное): {path}")

    # ── Test send ──────────────────────────────────────────────────────────

    def _test_send(self):
        chat = self._test_chat.get().strip()
        if not chat:
            return
        name = self._template_var.get()
        template = next((t for t in self._storage.load_templates() if t["name"] == name), None)
        if not template:
            self._log_write("Выберите шаблон")
            return
        photo = self._override_media or template.get("photo", "")
        text = self._apply_variables(template["text"])
        self._test_btn.configure(state="disabled", text="...")
        threading.Thread(
            target=self._do_test_send, args=(chat, photo, text), daemon=True
        ).start()

    def _do_test_send(self, chat, photo, text):
        try:
            if photo:
                self._tg.send_photo_message(chat, photo, text)
            else:
                self._tg.send_message(chat, text)
            self._log_write(f"Тест ✓ отправлен в {chat}")
            self.after(0, lambda: show_toast(self, f"Тест отправлен в {chat}"))
        except Exception as e:
            err = str(e)
            self._log_write(f"Тест ✗ {err}")
            self.after(0, lambda: show_toast(self, f"Ошибка теста: {err}", color="#EF4444"))
        finally:
            self.after(0, lambda: self._test_btn.configure(state="normal", text="Отправить"))

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
            self._sched_status.configure(
                text=f"Активно: каждый день в {sched['time']}", text_color="#4CAF50"
            )
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
                self._log_write(f"Автоматическая рассылка по расписанию ({current_time})")
                self._start_broadcast()
        self.after(30000, self._schedule_check)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _apply_variables(self, text):
        now = datetime.datetime.now()
        text = text.replace("{дата}", now.strftime("%d.%m.%Y"))
        text = text.replace("{время}", now.strftime("%H:%M"))
        text = text.replace("{date}", now.strftime("%d.%m.%Y"))
        text = text.replace("{time}", now.strftime("%H:%M"))
        return text

    def _parse_delay_range(self):
        try:
            d_min = float(self._delay_min.get() or "3")
        except ValueError:
            d_min = 3.0
        try:
            d_max = float(self._delay_max.get() or "8")
        except ValueError:
            d_max = 8.0
        d_min = max(1.0, d_min)
        d_max = max(d_min + 0.5, d_max)
        return d_min, d_max

    def _log_write(self, msg):
        self.after(0, self._log_write_main, msg)

    def _log_write_main(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Broadcast ──────────────────────────────────────────────────────────

    def _start_broadcast(self):
        if self._broadcasting:
            return
        name = self._template_var.get()
        template = next((t for t in self._storage.load_templates() if t["name"] == name), None)
        if not template:
            self._log_write("Выберите шаблон")
            return
        chats = [c for c in self._storage.load_chats() if c.get("enabled", True)]
        if not chats:
            self._log_write("Нет активных чатов — добавьте или включите чаты во вкладке Чаты")
            return
        photo = self._override_media or template.get("photo", "")
        d_min, d_max = self._parse_delay_range()
        self._stop_event.clear()
        self._broadcasting = True
        self._failed_entries = []
        self._retry_btn.configure(state="disabled", fg_color="#6B7280", hover_color="#4B5563")
        self._send_btn.configure(
            text="Стоп", fg_color="#6B7280", hover_color="#4B5563",
            command=self._stop_broadcast,
        )
        self._progress.set(0)
        threading.Thread(
            target=self._broadcast,
            args=(chats, template["text"], photo, name, d_min, d_max),
            daemon=True,
        ).start()

    def _stop_broadcast(self):
        self._stop_event.set()
        self._send_btn.configure(state="disabled", text="Остановка...")

    def _retry_failed(self):
        if not self._failed_entries:
            return
        name = self._template_var.get()
        template = next((t for t in self._storage.load_templates() if t["name"] == name), None)
        if not template:
            return
        photo = self._override_media or template.get("photo", "")
        d_min, d_max = self._parse_delay_range()
        self._stop_event.clear()
        self._broadcasting = True
        self._retry_btn.configure(state="disabled")
        self._send_btn.configure(
            text="Стоп", fg_color="#6B7280", hover_color="#4B5563",
            command=self._stop_broadcast,
        )
        self._progress.set(0)
        threading.Thread(
            target=self._broadcast,
            args=(self._failed_entries[:], template["text"], photo, name, d_min, d_max),
            daemon=True,
        ).start()

    def _broadcast(self, chats, text, photo, template_name, d_min, d_max):
        log_lines = []

        def log(msg):
            log_lines.append(msg)
            self._log_write(msg)

        log(f"Начинаю рассылку в {len(chats)} чатов...")
        success = 0
        errors = 0
        failed_entries = []
        total = len(chats)

        for i, entry in enumerate(chats, 1):
            if self._stop_event.is_set():
                log("Рассылка остановлена")
                break

            chat = entry["chat"]
            suffix = entry.get("suffix", "")
            raw = f"{text}\n{suffix}" if suffix else text
            caption = self._apply_variables(raw)

            try:
                if photo:
                    self._tg.send_photo_message(chat, photo, caption)
                else:
                    self._tg.send_message(chat, caption)
                display = entry.get("name") or chat
                log(f"[{i}/{total}] ✓ {display}")
                success += 1
                self._storage.record_chat_stat(chat, True)
            except FloodWaitError as e:
                log(f"[{i}/{total}] FloodWait {e.seconds}s — жду...")
                time.sleep(e.seconds)
                try:
                    if photo:
                        self._tg.send_photo_message(chat, photo, caption)
                    else:
                        self._tg.send_message(chat, caption)
                    log(f"[{i}/{total}] ✓ {chat} (после FloodWait)")
                    success += 1
                    self._storage.record_chat_stat(chat, True)
                except Exception as e2:
                    log(f"[{i}/{total}] ✗ {chat}: {e2}")
                    errors += 1
                    failed_entries.append(entry)
                    self._storage.record_chat_stat(chat, False)
            except Exception as e:
                log(f"[{i}/{total}] ✗ {chat}: {e}")
                errors += 1
                failed_entries.append(entry)
                self._storage.record_chat_stat(chat, False)

            self.after(0, self._progress.set, i / total)

            if i < total and not self._stop_event.is_set():
                time.sleep(random.uniform(d_min, d_max))

        log(f"Готово! Успешно: {success}, ошибок: {errors}")
        if not self._stop_event.is_set():
            self._storage.add_history_entry({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "template": template_name,
                "total": total,
                "success": success,
                "errors": errors,
            })
        self._failed_entries = failed_entries
        self._save_broadcast_log(template_name, log_lines)
        self.after(0, self._broadcast_done, success, errors)

    def _save_broadcast_log(self, template_name, lines):
        try:
            logs_dir = self._storage.chats_file.parent / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            safe = "".join(c for c in template_name if c.isalnum() or c in " _-")[:24].strip()
            (logs_dir / f"{stamp}_{safe}.txt").write_text(
                "\n".join(lines), encoding="utf-8"
            )
        except Exception:
            pass

    def _broadcast_done(self, success=0, errors=0):
        self._broadcasting = False
        self._send_btn.configure(
            state="normal", text="Разослать по всем чатам",
            fg_color="#F97316", hover_color="#EA6C0A",
            command=self._start_broadcast,
        )
        if self._failed_entries:
            self._retry_btn.configure(
                state="normal", fg_color="#EF4444", hover_color="#DC2626"
            )
        if not self._stop_event.is_set():
            color = "#4CAF50" if errors == 0 else "#FF9800"
            show_toast(self, f"Готово! Успешно: {success}, ошибок: {errors}", color=color)
