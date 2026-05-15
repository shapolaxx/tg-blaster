import customtkinter as ctk
from tkinter import messagebox


class HistoryTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage
        self._selected: set[int] = set()   # indices into reversed history
        self._rows: dict[int, ctk.CTkFrame] = {}

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btn_frame, text="↻ Обновить", width=110, command=self._refresh).pack(side="left", padx=4)
        self._del_btn = ctk.CTkButton(
            btn_frame, text="Удалить выбранные", width=150,
            fg_color="#EF4444", hover_color="#DC2626",
            state="disabled", command=self._delete_selected,
        )
        self._del_btn.pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Очистить всё", width=120,
            fg_color="#6B7280", hover_color="#4B5563",
            command=self._clear,
        ).pack(side="left", padx=4)
        self._count_label = ctk.CTkLabel(btn_frame, text="", text_color="gray")
        self._count_label.pack(side="left", padx=10)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

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
        status  = "✓" if errors == 0 else f"✓{success} ✗{errors}"
        text    = f"{entry.get('date', '—')}    {entry.get('template', '—')}    {status}/{total}"
        color   = "#4CAF50" if errors == 0 else "#FF9800"

        row = ctk.CTkFrame(self._listbox, fg_color="transparent")
        row.pack(fill="x", pady=1)
        self._rows[idx] = row

        # Checkbox-style selection button
        sel_btn = ctk.CTkButton(
            row, text="☐", width=28, height=28,
            fg_color="transparent", hover_color=("gray75", "gray30"),
            font=ctk.CTkFont(size=14),
            command=lambda i=idx, b=None: self._toggle(i),
        )
        sel_btn.pack(side="left", padx=(0, 4))
        row._sel_btn = sel_btn  # type: ignore[attr-defined]

        ctk.CTkLabel(
            row, text=text, anchor="w",
            text_color=color, font=ctk.CTkFont(size=12),
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row, text="✕", width=28, height=28,
            fg_color="transparent", text_color="#EF4444",
            hover_color=("gray75", "gray30"),
            command=lambda i=idx: self._delete_one(i),
        ).pack(side="right", padx=4)

    # ── Selection ──────────────────────────────────────────────────────────

    def _toggle(self, idx: int):
        if idx in self._selected:
            self._selected.discard(idx)
            self._rows[idx]._sel_btn.configure(text="☐", fg_color="transparent")
        else:
            self._selected.add(idx)
            self._rows[idx]._sel_btn.configure(text="☑", fg_color=("#3B82F6", "#2563EB"))
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
