import customtkinter as ctk


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage

        ctk.CTkLabel(
            self, text="Дашборд",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 16), padx=16, anchor="w")

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=16, pady=(0, 16))
        cards_frame.columnconfigure((0, 1), weight=1)

        self._chat_val = self._stat_card(cards_frame, "Чатов", 0, 0)
        self._tmpl_val = self._stat_card(cards_frame, "Шаблонов", 0, 1)

        self._last_val = self._info_row("Последняя рассылка")
        self._sched_val = self._info_row("По расписанию")

        self.refresh()

    def _stat_card(self, parent, title, row, col):
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(
            card, text=title, text_color="gray", font=ctk.CTkFont(size=12)
        ).pack(pady=(14, 4))
        val = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=36, weight="bold"))
        val.pack(pady=(0, 14))
        return val

    def _info_row(self, label):
        row = ctk.CTkFrame(self)
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(
            row, text=label + ":", text_color="gray", width=180, anchor="w"
        ).pack(side="left", padx=12, pady=10)
        val = ctk.CTkLabel(row, text="—")
        val.pack(side="right", padx=12)
        return val

    def refresh(self):
        chats = self._storage.load_chats()
        templates = self._storage.load_templates()
        history = self._storage.load_history()
        schedule = self._storage.load_schedule()

        self._chat_val.configure(text=str(len(chats)))
        self._tmpl_val.configure(text=str(len(templates)))

        if history:
            last = history[-1]
            date = last.get("date", "—")
            tmpl = last.get("template", "—")
            ok = last.get("success", 0)
            err = last.get("errors", 0)
            self._last_val.configure(text=f"{date}  {tmpl}  ✓{ok} ✗{err}")
        else:
            self._last_val.configure(text="—")

        if schedule.get("enabled") and schedule.get("time"):
            self._sched_val.configure(text=f"Каждый день в {schedule['time']}")
        else:
            self._sched_val.configure(text="Выключено")
