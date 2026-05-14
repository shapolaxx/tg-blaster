import customtkinter as ctk
from tkinter import messagebox


class ChatDialog(ctk.CTkToplevel):
    def __init__(self, parent, entry=None, on_save=None):
        super().__init__(parent)
        self.title("Чат")
        self.geometry("460x300")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save

        ctk.CTkLabel(self, text="@username или ссылка t.me/...:").pack(anchor="w", padx=20, pady=(15, 0))
        self._chat = ctk.CTkEntry(self, width=420)
        self._chat.pack(padx=20)
        if entry:
            self._chat.insert(0, entry["chat"])

        ctk.CTkLabel(self, text="Суффикс (добавляется в конец каждого сообщения, необязательно):").pack(anchor="w", padx=20, pady=(12, 0))
        self._suffix = ctk.CTkTextbox(self, width=420, height=100)
        self._suffix.pack(padx=20)
        if entry and entry.get("suffix"):
            self._suffix.insert("1.0", entry["suffix"])

        ctk.CTkButton(self, text="Сохранить", command=self._save).pack(pady=12)

    def _save(self):
        chat = self._chat.get().strip()
        if not chat:
            return
        suffix = self._suffix.get("1.0", "end").strip()
        self.destroy()
        if self._on_save:
            self._on_save({"chat": chat, "suffix": suffix})


class ChatsTab(ctk.CTkFrame):
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage
        self._selected = None
        self._buttons = {}

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btn_frame, text="Добавить", width=110, command=self._add).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Изменить", width=110, command=self._edit).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Удалить", width=110, command=self._delete).pack(side="left", padx=4)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh()

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._selected = None
        self._buttons = {}
        for entry in self._storage.load_chats():
            label = entry["chat"]
            if entry.get("suffix"):
                label += "  [+ суффикс]"
            btn = ctk.CTkButton(
                self._listbox, text=label, anchor="w",
                fg_color="transparent", text_color=("black", "white"),
                hover_color=("gray80", "gray30"),
                command=lambda c=entry["chat"]: self._select(c),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[entry["chat"]] = btn

    def _select(self, chat):
        if self._selected and self._selected in self._buttons:
            self._buttons[self._selected].configure(fg_color="transparent")
        self._selected = chat
        self._buttons[chat].configure(fg_color=("gray75", "gray25"))

    def _add(self):
        ChatDialog(self, on_save=self._on_add_save)

    def _on_add_save(self, entry):
        chats = self._storage.load_chats()
        if not any(c["chat"] == entry["chat"] for c in chats):
            chats.append(entry)
            self._storage.save_chats(chats)
        self._refresh()

    def _edit(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите чат")
            return
        chats = self._storage.load_chats()
        entry = next((c for c in chats if c["chat"] == self._selected), None)
        if entry:
            ChatDialog(self, entry=entry, on_save=lambda e: self._on_edit_save(e))

    def _on_edit_save(self, entry):
        chats = self._storage.load_chats()
        chats = [entry if c["chat"] == entry["chat"] else c for c in chats]
        self._storage.save_chats(chats)
        self._refresh()

    def _delete(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите чат")
            return
        if messagebox.askyesno("Удалить", f"Удалить {self._selected}?"):
            chats = [c for c in self._storage.load_chats() if c["chat"] != self._selected]
            self._storage.save_chats(chats)
            self._refresh()
