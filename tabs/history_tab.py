import customtkinter as ctk
from tkinter import messagebox


class HistoryTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btn_frame, text="↻ Обновить", width=110, command=self._refresh).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Очистить", width=110, command=self._clear).pack(side="left", padx=4)
        self._count_label = ctk.CTkLabel(btn_frame, text="", text_color="gray")
        self._count_label.pack(side="left", padx=10)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh()

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        history = self._storage.load_history()
        self._count_label.configure(text=f"Всего рассылок: {len(history)}")
        for entry in reversed(history):
            success = entry.get("success", 0)
            total = entry.get("total", 0)
            errors = entry.get("errors", 0)
            status = "✓" if errors == 0 else f"✓{success} ✗{errors}"
            text = f"{entry.get('date', '—')}    {entry.get('template', '—')}    {status}/{total}"
            color = "#4CAF50" if errors == 0 else "#FF9800"
            ctk.CTkLabel(
                self._listbox, text=text, anchor="w",
                text_color=color, font=ctk.CTkFont(size=12),
            ).pack(fill="x", pady=2, padx=4)

    def _clear(self):
        if messagebox.askyesno("Очистить", "Очистить всю историю рассылок?"):
            self._storage.save_history([])
            self._refresh()
