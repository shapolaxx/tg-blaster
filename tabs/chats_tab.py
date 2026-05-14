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
