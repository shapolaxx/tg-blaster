import threading
import customtkinter as ctk
from tkinter import messagebox


class HistoryTab(ctk.CTkFrame):
    def __init__(self, parent, storage, tg_client=None):
        super().__init__(parent, fg_color="transparent")
        self._storage = storage
        self._tg = tg_client
        self._selected: set[int] = set()
        self._rows: dict[int, ctk.CTkFrame] = {}

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(
            header, text="История",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#111827", "white"),
        ).pack(side="left")
        self._count_label = ctk.CTkLabel(header, text="", text_color=("gray50", "#64748B"), font=ctk.CTkFont(size=12))
        self._count_label.pack(side="left", padx=12)

        # Action bar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(12, 8))
        ctk.CTkButton(bar, text="↻ Обновить", width=110, height=34, command=self._refresh,
                      fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
                      text_color=("#374151", "#E2E8F0")).pack(side="left", padx=(0, 6))
        self._del_btn = ctk.CTkButton(
            bar, text="Удалить выбранные", width=150, height=34,
            fg_color="#EF4444", hover_color="#DC2626",
            state="disabled", command=self._delete_selected,
        )
        self._del_btn.pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            bar, text="Очистить всё", width=120, height=34,
            fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
            text_color=("gray50", "#64748B"),
            command=self._clear,
        ).pack(side="left")

        self._listbox = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._listbox.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._refresh()

    # ── Refresh ────────────────────────────────────────────────────────────

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._rows.clear()
        self._selected.clear()
        self._del_btn.configure(state="disabled")

        history = self._storage.load_history()
        self._count_label.configure(text=f"Всего рассылок: {len(history)}")

        for rev_idx, entry in enumerate(reversed(history)):
            self._add_row(rev_idx, entry)

    def _add_row(self, idx: int, entry: dict):
        success = entry.get("success", 0)
        total   = entry.get("total", 0)
        errors  = entry.get("errors", 0)
        skipped = entry.get("skipped", 0)
        ok_all  = errors == 0

        card = ctk.CTkFrame(
            self._listbox,
            fg_color=("white", "#0F172A"),
            border_width=1,
            border_color=("#E2E8F0", "#1E293B"),
            corner_radius=8,
        )
        card.pack(fill="x", pady=3)
        self._rows[idx] = card

        # Left accent bar
        accent_color = "#22C55E" if ok_all else "#F59E0B"
        ctk.CTkFrame(card, width=4, corner_radius=0, fg_color=accent_color).pack(side="left", fill="y")

        # Checkbox
        sel_btn = ctk.CTkButton(
            card, text="☐", width=28, height=28,
            fg_color="transparent", hover_color=("gray80", "#1E293B"),
            font=ctk.CTkFont(size=14),
            command=lambda i=idx: self._toggle(i),
        )
        sel_btn.pack(side="left", padx=(4, 0))
        card._sel_btn = sel_btn  # type: ignore[attr-defined]

        # Info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=10, pady=6)

        ctk.CTkLabel(
            info,
            text=f"{entry.get('date', '—')}  ·  {entry.get('template', '—')}",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#111827", "white"),
        ).pack(anchor="w")

        skip_str = f"  ⏭{skipped}" if skipped else ""
        stat_text = f"✓ {success}  ✗ {errors}{skip_str}  из {total}"
        ctk.CTkLabel(
            info, text=stat_text, anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=("#22C55E" if ok_all else "#F59E0B"),
        ).pack(anchor="w")

        # Right buttons
        ctk.CTkButton(
            card, text="✕", width=28, height=28,
            fg_color="transparent", text_color="#EF4444",
            hover_color=("gray80", "#1E293B"),
            command=lambda i=idx: self._delete_one(i),
        ).pack(side="right", padx=(0, 6))

        if self._tg and entry.get("messages"):
            ctk.CTkButton(
                card, text="Del TG", width=56, height=28,
                fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
                text_color=("gray50", "#94A3B8"),
                font=ctk.CTkFont(size=10),
                command=lambda e=entry: self._delete_tg_msgs(e),
            ).pack(side="right", padx=(0, 4))

    # ── Selection ──────────────────────────────────────────────────────────

    def _toggle(self, idx: int):
        if idx in self._selected:
            self._selected.discard(idx)
            self._rows[idx]._sel_btn.configure(text="☐", fg_color="transparent")
            self._rows[idx].configure(border_color=("#E2E8F0", "#1E293B"))
        else:
            self._selected.add(idx)
            self._rows[idx]._sel_btn.configure(text="☑", fg_color=("#2563EB", "#2563EB"))
            self._rows[idx].configure(border_color=("#2563EB", "#3B82F6"))
        self._del_btn.configure(state="normal" if self._selected else "disabled")

    # ── Delete ─────────────────────────────────────────────────────────────

    def _delete_one(self, rev_idx: int):
        history = self._storage.load_history()
        real_idx = len(history) - 1 - rev_idx
        if 0 <= real_idx < len(history):
            del history[real_idx]
            self._storage.save_history(history)
        self._refresh()

    def _delete_selected(self):
        if not self._selected:
            return
        if not messagebox.askyesno("Удалить", f"Удалить {len(self._selected)} запись(ей)?"):
            return
        history = self._storage.load_history()
        total = len(history)
        # Convert reversed indices back to real indices and delete
        real_indices = sorted({total - 1 - i for i in self._selected}, reverse=True)
        for i in real_indices:
            if 0 <= i < len(history):
                del history[i]
        self._storage.save_history(history)
        self._refresh()

    def _clear(self):
        if messagebox.askyesno("Очистить", "Очистить всю историю рассылок?"):
            self._storage.save_history([])
            self._refresh()

    # ── TG message deletion ────────────────────────────────────────────────

    def _delete_tg_msgs(self, entry):
        messages = entry.get("messages", [])
        if not messages:
            return
        if not messagebox.askyesno("Удалить из Telegram", f"Удалить {len(messages)} сообщений из Telegram?\nЭто действие необратимо."):
            return
        threading.Thread(target=self._do_delete_tg, args=(messages,), daemon=True).start()

    def _do_delete_tg(self, messages):
        from collections import defaultdict
        by_chat = defaultdict(list)
        for m in messages:
            by_chat[m["chat"]].append(m["msg_id"])
        errors = 0
        for chat, msg_ids in by_chat.items():
            try:
                self._tg.delete_messages(chat, msg_ids)
            except Exception:
                errors += 1
        if errors:
            self.after(0, lambda: messagebox.showwarning("Ошибка", f"Не удалось удалить сообщения из {errors} чат(ов)"))
