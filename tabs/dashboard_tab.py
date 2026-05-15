import customtkinter as ctk


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent, fg_color="transparent")
        self._storage = storage

        # ── Header ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 0))
        ctk.CTkLabel(
            header, text="Дашборд",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#111827", "white"),
        ).pack(side="left")
        ctk.CTkButton(
            header, text="↻", width=32, height=32, command=self.refresh,
            fg_color="transparent", hover_color=("gray80", "#1E293B"),
            font=ctk.CTkFont(size=16),
        ).pack(side="right")

        # ── Stat cards ────────────────────────────────────────────────────
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=24, pady=(16, 0))
        cards.columnconfigure((0, 1, 2), weight=1, uniform="card")

        self._chat_val = self._stat_card(cards, "Чатов", "активных каналов", "#3B82F6", 0)
        self._tmpl_val = self._stat_card(cards, "Шаблонов", "готовых к отправке", "#F97316", 1)
        self._hist_val = self._stat_card(cards, "Рассылок", "выполнено всего", "#22C55E", 2)

        # ── Section label ─────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="СТАТУС", anchor="w",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "#475569"),
        ).pack(fill="x", padx=26, pady=(24, 4))

        # ── Info cards ────────────────────────────────────────────────────
        self._last_val = self._info_card("Последняя рассылка", "—")
        self._sched_val = self._info_card("Авто-рассылка", "—")

        self.refresh()

    def _stat_card(self, parent, title, subtitle, accent, col):
        card = ctk.CTkFrame(
            parent,
            fg_color=("white", "#0F172A"),
            border_width=1,
            border_color=("#E2E8F0", "#1E293B"),
            corner_radius=12,
        )
        card.grid(row=0, column=col, padx=6, pady=0, sticky="nsew")

        # Accent top stripe
        ctk.CTkFrame(card, height=3, corner_radius=0, fg_color=accent).pack(fill="x")

        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "#64748B"),
        ).pack(pady=(14, 0))

        val = ctk.CTkLabel(
            card, text="0",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=("#111827", "white"),
        )
        val.pack()

        ctk.CTkLabel(
            card, text=subtitle,
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "#475569"),
        ).pack(pady=(0, 14))

        return val

    def _info_card(self, label, default):
        card = ctk.CTkFrame(
            self,
            fg_color=("white", "#0F172A"),
            border_width=1,
            border_color=("#E2E8F0", "#1E293B"),
            corner_radius=10,
        )
        card.pack(fill="x", padx=24, pady=5)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(10, 2))
        ctk.CTkLabel(
            top, text=label,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "#64748B"),
            anchor="w",
        ).pack(side="left")

        val = ctk.CTkLabel(
            card, text=default,
            font=ctk.CTkFont(size=13),
            text_color=("#111827", "#E2E8F0"),
            anchor="w",
            wraplength=560,
            justify="left",
        )
        val.pack(padx=16, pady=(0, 10), anchor="w")
        return val

    def refresh(self):
        chats = self._storage.load_chats()
        templates = self._storage.load_templates()
        history = self._storage.load_history()
        schedule = self._storage.load_schedule()

        active_chats = sum(1 for c in chats if c.get("enabled", True))
        self._chat_val.configure(text=str(active_chats))
        self._tmpl_val.configure(text=str(len(templates)))
        self._hist_val.configure(text=str(len(history)))

        if history:
            last = history[-1]
            ok, err = last.get("success", 0), last.get("errors", 0)
            skip = last.get("skipped", 0)
            skip_str = f"  пропущено: {skip}" if skip else ""
            self._last_val.configure(
                text=f"{last.get('date', '—')}  ·  {last.get('template', '—')}  ·  ✓{ok} ✗{err}{skip_str}"
            )
        else:
            self._last_val.configure(text="Рассылок ещё не было")

        mode = schedule.get("mode", "По времени")
        if schedule.get("enabled"):
            if mode == "Каждые N часов":
                h = schedule.get("interval_hours", 2)
                self._sched_val.configure(text=f"Активно — каждые {h} ч.")
            elif schedule.get("time"):
                self._sched_val.configure(text=f"Активно — каждый день в {schedule['time']}")
            else:
                self._sched_val.configure(text="Включено (нет настроек)")
        else:
            self._sched_val.configure(text="Выключено")
