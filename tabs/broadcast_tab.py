import datetime
import random
import threading
import time
import customtkinter as ctk
from tkinter import filedialog
from telethon.errors import FloodWaitError
from utils.toast import show_toast
from utils.paste_fix import fix_entry
from utils.notify import notify


class BroadcastTab(ctk.CTkFrame):
    def __init__(self, parent, storage, tg_client):
        super().__init__(parent, fg_color="transparent")
        self._storage = storage
        self._tg = tg_client
        self._override_media = None
        self._broadcasting = False
        self._stop_event = threading.Event()
        self._failed_entries = []

        # ── Header ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            hdr, text="Рассылка",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#111827", "#F1F5F9"),
            anchor="w",
        ).pack(side="left")

        # ── Main action card (always visible at top) ───────────────────────
        action_card = ctk.CTkFrame(
            self, fg_color=("white", "#111827"),
            border_width=1, border_color=("#E5E7EB", "#1E2740"), corner_radius=10,
        )
        action_card.pack(fill="x", padx=20, pady=(0, 6))
        action_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        action_inner.pack(fill="x", padx=12, pady=10)
        self._send_btn = ctk.CTkButton(
            action_inner, text="▷  Разослать по всем чатам", height=44,
            fg_color="#F97316", hover_color="#EA6C0A",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_broadcast,
        )
        self._send_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._retry_btn = ctk.CTkButton(
            action_inner, text="Повторить ошибки", height=44, width=150,
            fg_color=("gray85", "#1A2236"), hover_color=("gray78", "#1E2D45"),
            text_color=("#374151", "#94A3B8"),
            state="disabled",
            command=self._retry_failed,
        )
        self._retry_btn.pack(side="left")
        self._progress = ctk.CTkProgressBar(action_card, height=4)
        self._progress.set(0)
        self._progress.pack(fill="x", padx=0, pady=(0, 0))

        # ── Scrollable settings area ───────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=20, pady=(0, 0))

        # ── Template selector card ─────────────────────────────────────────
        self._section_lbl("ШАБЛОН")
        top_card = ctk.CTkFrame(
            self._scroll, fg_color=("white", "#111827"),
            border_width=1, border_color=("#E5E7EB", "#1E2740"), corner_radius=10,
        )
        top_card.pack(fill="x", pady=(0, 0))
        top = ctk.CTkFrame(top_card, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(top, text="Шаблон:", text_color=("gray50", "#64748B")).pack(side="left", padx=(0, 6))
        self._template_var = ctk.StringVar()
        self._template_menu = ctk.CTkOptionMenu(
            top, variable=self._template_var, values=["—"],
            command=self._on_template_select, width=200,
        )
        self._template_menu.pack(side="left")
        ctk.CTkButton(top, text="↻", width=32, height=32, command=self.refresh_templates,
                      fg_color="transparent", hover_color=("gray80", "#1A2236")).pack(side="left", padx=4)

        preview_inner = ctk.CTkFrame(top_card, fg_color=("gray95", "#0B0F1E"), corner_radius=6)
        preview_inner.pack(fill="x", padx=12, pady=(0, 6))
        self._preview_text = ctk.CTkLabel(
            preview_inner, text="Выберите шаблон...", wraplength=500,
            justify="left", text_color=("#374151", "#94A3B8"),
            font=ctk.CTkFont(size=12),
        )
        self._preview_text.pack(anchor="w", padx=8, pady=(6, 2))
        self._media_label = ctk.CTkLabel(
            preview_inner, text="Медиа: нет", text_color=("gray50", "#475569"),
            font=ctk.CTkFont(size=11),
        )
        self._media_label.pack(anchor="w", padx=8, pady=(0, 6))

        media_test = ctk.CTkFrame(top_card, fg_color="transparent")
        media_test.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkButton(
            media_test, text="Сменить медиа", height=30, width=130,
            fg_color=("gray85", "#1A2236"), hover_color=("gray78", "#1E2D45"),
            text_color=("#374151", "#CBD5E1"), font=ctk.CTkFont(size=12),
            command=self._change_media,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(media_test, text="Тест в:", text_color=("gray50", "#64748B")).pack(side="left", padx=(0, 6))
        self._test_chat = ctk.CTkEntry(media_test, placeholder_text="@chat или t.me/...", width=170, height=30)
        self._test_chat.pack(side="left")
        fix_entry(self._test_chat)
        self._test_btn = ctk.CTkButton(
            media_test, text="Отправить тест", width=120, height=30,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12),
            command=self._test_send,
        )
        self._test_btn.pack(side="left", padx=6)

        # ── Auto-schedule section ──────────────────────────────────────────
        self._section_lbl("АВТО-РАССЫЛКА")
        sched_outer = ctk.CTkFrame(
            self._scroll, fg_color=("white", "#111827"),
            border_width=1, border_color=("#E5E7EB", "#1E2740"), corner_radius=10,
        )
        sched_outer.pack(fill="x", pady=(0, 0))

        sched_r1 = ctk.CTkFrame(sched_outer, fg_color="transparent")
        sched_r1.pack(fill="x", padx=12, pady=(10, 2))
        self._sched_var = ctk.BooleanVar()
        ctk.CTkCheckBox(sched_r1, text="Включить авто-рассылку", variable=self._sched_var).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(sched_r1, text="Режим:", text_color=("gray50", "#64748B")).pack(side="left", padx=(0, 4))
        self._sched_mode = ctk.CTkOptionMenu(
            sched_r1, values=["Каждые N часов", "По времени"], width=170,
            command=self._on_sched_mode,
        )
        self._sched_mode.pack(side="left")
        self._sched_status = ctk.CTkLabel(sched_r1, text="Выключено", text_color=("gray50", "#64748B"))
        self._sched_status.pack(side="left", padx=12)
        self._countdown_lbl = ctk.CTkLabel(
            sched_r1, text="", font=ctk.CTkFont(size=12),
            text_color=("#2563EB", "#60A5FA"),
        )
        self._countdown_lbl.pack(side="left")

        sched_r2 = ctk.CTkFrame(sched_outer, fg_color="transparent")
        sched_r2.pack(fill="x", padx=12, pady=(0, 10))
        self._sched_interval = ctk.CTkEntry(sched_r2, width=60, placeholder_text="2")
        fix_entry(self._sched_interval)
        self._sched_interval_lbl = ctk.CTkLabel(sched_r2, text="ч. между рассылками", text_color="gray")
        self._sched_time = ctk.CTkEntry(sched_r2, width=80, placeholder_text="10:00")
        fix_entry(self._sched_time)
        self._sched_time_lbl = ctk.CTkLabel(sched_r2, text="время отправки (ЧЧ:ММ)", text_color="gray")
        self._sched_save_btn = ctk.CTkButton(sched_r2, text="Сохранить", width=100, command=self._save_schedule)
        self._sched_save_btn.pack(side="left")

        # ── Delay + Cooldown card ──────────────────────────────────────────
        self._section_lbl("НАСТРОЙКИ")
        settings_card = ctk.CTkFrame(
            self._scroll, fg_color=("white", "#111827"),
            border_width=1, border_color=("#E5E7EB", "#1E2740"), corner_radius=10,
        )
        settings_card.pack(fill="x", pady=(0, 12))
        delay_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        delay_row.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(delay_row, text="Задержка:", text_color=("gray50", "#64748B")).pack(side="left", padx=(0, 6))
        self._delay_min = ctk.CTkEntry(delay_row, width=52, placeholder_text="3", height=30)
        self._delay_min.pack(side="left")
        fix_entry(self._delay_min)
        ctk.CTkLabel(delay_row, text="—", text_color=("gray50", "#64748B")).pack(side="left", padx=4)
        self._delay_max = ctk.CTkEntry(delay_row, width=52, placeholder_text="8", height=30)
        self._delay_max.pack(side="left")
        fix_entry(self._delay_max)
        ctk.CTkLabel(delay_row, text="сек", text_color=("gray50", "#64748B")).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(delay_row, text="│", text_color=("gray70", "#334155")).pack(side="left", padx=(16, 16))
        ctk.CTkLabel(delay_row, text="Cooldown:", text_color=("gray50", "#64748B")).pack(side="left", padx=(0, 6))
        self._cooldown = ctk.CTkEntry(delay_row, width=52, placeholder_text="0", height=30)
        self._cooldown.pack(side="left")
        fix_entry(self._cooldown)
        ctk.CTkLabel(delay_row, text="ч. (0 = выкл)", text_color=("gray50", "#64748B")).pack(side="left", padx=(4, 0))

        # ── Log (fixed at bottom, always visible) ─────────────────────────
        self._section_lbl("ЛОГ", parent=self)
        self._log = ctk.CTkTextbox(
            self, height=140, state="disabled",
            fg_color=("gray97", "#080C14"),
            border_width=1, border_color=("#E5E7EB", "#1E2740"),
            corner_radius=10,
            font=ctk.CTkFont(size=12, family="Consolas"),
            text_color=("#374151", "#4ADE80"),
        )
        self._log.pack(fill="x", padx=20, pady=(0, 16))

        self.refresh_templates()
        self._load_schedule()
        self._schedule_check()
        self._tick_countdown()

    def _section_lbl(self, text, parent=None):
        ctk.CTkLabel(
            parent if parent is not None else self._scroll,
            text=text, anchor="w",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "#475569"),
        ).pack(fill="x", padx=2, pady=(10, 3))

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

        # Apply suffix if this chat is in the configured list
        chat_entry = next(
            (c for c in self._storage.load_chats() if c["chat"].rstrip("/") == chat.rstrip("/")),
            None,
        )
        suffix = (chat_entry or {}).get("suffix", "").strip()
        if suffix:
            text = f"{text}\n\n{suffix}"
            self._log_write(f"Тест: применён суффикс чата")

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
            self.after(0, lambda: self._test_btn.configure(state="normal", text="Отправить тест"))

    # ── Schedule ───────────────────────────────────────────────────────────

    def _on_sched_mode(self, mode):
        self._sched_interval.pack_forget()
        self._sched_interval_lbl.pack_forget()
        self._sched_time.pack_forget()
        self._sched_time_lbl.pack_forget()
        if mode == "Каждые N часов":
            self._sched_interval.pack(side="left", padx=(0, 6), before=self._sched_save_btn)
            self._sched_interval_lbl.pack(side="left", padx=(0, 12), before=self._sched_save_btn)
        else:
            self._sched_time.pack(side="left", padx=(0, 6), before=self._sched_save_btn)
            self._sched_time_lbl.pack(side="left", padx=(0, 12), before=self._sched_save_btn)

    def _load_schedule(self):
        sched = self._storage.load_schedule()
        self._sched_var.set(sched.get("enabled", False))
        mode = sched.get("mode", "По времени")
        self._sched_mode.set(mode)
        t = sched.get("time", "")
        if t:
            self._sched_time.insert(0, t)
        interval = sched.get("interval_hours", 2)
        self._sched_interval.insert(0, str(interval))
        self._on_sched_mode(mode)
        self._update_sched_status(sched)

    def _save_schedule(self):
        sched = self._storage.load_schedule()
        sched["enabled"] = self._sched_var.get()
        sched["mode"] = self._sched_mode.get()
        sched["time"] = self._sched_time.get().strip()
        try:
            sched["interval_hours"] = float(self._sched_interval.get().strip() or "2")
        except ValueError:
            sched["interval_hours"] = 2.0
        sched["template"] = self._template_var.get()
        self._storage.save_schedule(sched)
        self._update_sched_status(sched)
        self._tick_countdown()

    def _tick_countdown(self):
        sched = self._storage.load_schedule()
        text = ""
        if sched.get("enabled") and not self._broadcasting:
            mode = sched.get("mode", "По времени")
            try:
                if mode == "Каждые N часов":
                    interval_secs = float(sched.get("interval_hours", 2)) * 3600
                    last = float(sched.get("last_sent_at", 0))
                    remaining = max(0.0, last + interval_secs - time.time())
                    text = self._fmt_countdown(remaining)
                else:
                    t_str = sched.get("time", "")
                    if t_str:
                        now = datetime.datetime.now()
                        h, m = map(int, t_str.split(":"))
                        nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        if nxt <= now:
                            nxt += datetime.timedelta(days=1)
                        remaining = (nxt - now).total_seconds()
                        text = self._fmt_countdown(remaining)
            except Exception:
                pass
        self._countdown_lbl.configure(text=text)
        self.after(10000, self._tick_countdown)

    @staticmethod
    def _fmt_countdown(secs: float) -> str:
        if secs <= 0:
            return "· скоро"
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        if h > 0:
            return f"· через {h}ч {m:02d}мин"
        return f"· через {m}мин {int(secs % 60):02d}с"

    def _update_sched_status(self, sched=None):
        if sched is None:
            sched = self._storage.load_schedule()
        if sched.get("enabled"):
            mode = sched.get("mode", "По времени")
            if mode == "Каждые N часов":
                hours = sched.get("interval_hours", 2)
                self._sched_status.configure(text=f"Активно: каждые {hours} ч.", text_color="#4CAF50")
            elif sched.get("time"):
                self._sched_status.configure(text=f"Активно: каждый день в {sched['time']}", text_color="#4CAF50")
            else:
                self._sched_status.configure(text="Активно (нет времени)", text_color="#FF9800")
        else:
            self._sched_status.configure(text="Выключено", text_color="gray")

    def _schedule_check(self):
        sched = self._storage.load_schedule()
        if sched.get("enabled") and not self._broadcasting:
            mode = sched.get("mode", "По времени")
            if mode == "Каждые N часов":
                interval_hours = float(sched.get("interval_hours", 2))
                last_sent_at = float(sched.get("last_sent_at", 0))
                if time.time() - last_sent_at >= interval_hours * 3600:
                    sched["last_sent_at"] = time.time()
                    self._storage.save_schedule(sched)
                    if sched.get("template"):
                        self._template_var.set(sched["template"])
                    self._log_write(f"Автоматическая рассылка (каждые {interval_hours} ч.)")
                    self._start_broadcast()
            else:
                if sched.get("time"):
                    now = datetime.datetime.now()
                    today = now.strftime("%Y-%m-%d")
                    try:
                        h, m = map(int, sched["time"].split(":"))
                        sched_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        # fire if we're within the last 30-second window and haven't fired today
                        in_window = 0 <= (now - sched_dt).total_seconds() < 30
                    except Exception:
                        in_window = False
                    if in_window and sched.get("last_sent_date") != today:
                        sched["last_sent_date"] = today
                        self._storage.save_schedule(sched)
                        if sched.get("template"):
                            self._template_var.set(sched["template"])
                        self._log_write(f"Автоматическая рассылка по расписанию ({sched['time']})")
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

    def _parse_cooldown(self) -> float:
        try:
            return max(0.0, float(self._cooldown.get() or "0")) * 3600
        except ValueError:
            return 0.0

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
        skipped = 0
        failed_entries = []
        sent_messages = []
        total = len(chats)
        cooldown_secs = self._parse_cooldown()

        for i, entry in enumerate(chats, 1):
            if self._stop_event.is_set():
                log("Рассылка остановлена")
                break

            chat = entry["chat"]

            if cooldown_secs > 0:
                elapsed = time.time() - self._storage.get_chat_last_sent(chat)
                if elapsed < cooldown_secs:
                    remaining_h = (cooldown_secs - elapsed) / 3600
                    display = entry.get("name") or chat
                    log(f"[{i}/{total}] ⏭ {display} — cooldown ({remaining_h:.1f}ч. осталось)")
                    skipped += 1
                    self.after(0, self._progress.set, i / total)
                    continue

            suffix = entry.get("suffix", "").strip()
            raw = f"{text}\n\n{suffix}" if suffix else text
            caption = self._apply_variables(raw)
            preview = caption.replace("\n", " ↵ ")[:70]

            try:
                if photo:
                    msg_id = self._tg.send_photo_message(chat, photo, caption)
                else:
                    msg_id = self._tg.send_message(chat, caption)
                sent_messages.append({"chat": chat, "msg_id": msg_id})
                display = entry.get("name") or chat
                suffix_tag = " [+суффикс]" if suffix else ""
                log(f"[{i}/{total}] ✓ {display}{suffix_tag}")
                log(f"   → {preview}")
                success += 1
                self._storage.record_chat_stat(chat, True)
            except FloodWaitError as e:
                log(f"[{i}/{total}] FloodWait {e.seconds}s — жду...")
                time.sleep(e.seconds)
                try:
                    if photo:
                        msg_id = self._tg.send_photo_message(chat, photo, caption)
                    else:
                        msg_id = self._tg.send_message(chat, caption)
                    sent_messages.append({"chat": chat, "msg_id": msg_id})
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

        skip_note = f", пропущено (cooldown): {skipped}" if skipped else ""
        log(f"Готово! Успешно: {success}, ошибок: {errors}{skip_note}")
        if not self._stop_event.is_set():
            self._storage.add_history_entry({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "template": template_name,
                "total": total,
                "success": success,
                "errors": errors,
                "skipped": skipped,
                "messages": sent_messages,
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
            state="normal", text="▷  Разослать по всем чатам",
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
            notify("TG Blaster", f"Рассылка завершена: ✓{success} ✗{errors}")
