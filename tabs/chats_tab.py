import json
import customtkinter as ctk
from tkinter import messagebox, filedialog
from utils.paste_fix import fix_entry, fix_textbox


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
        fix_entry(self._chat)
        if entry:
            self._chat.insert(0, entry["chat"])

        ctk.CTkLabel(self, text="Суффикс (добавляется в конец каждого сообщения, необязательно):").pack(anchor="w", padx=20, pady=(12, 0))
        self._suffix = ctk.CTkTextbox(self, width=420, height=100)
        self._suffix.pack(padx=20)
        fix_textbox(self._suffix)
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
    def __init__(self, parent, storage, tg_client=None):
        super().__init__(parent)
        self._storage = storage
        self._tg = tg_client
        self._selected = None
        self._buttons = {}
        self._search_var = ctk.StringVar()

        # Buttons row
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkButton(btn_frame, text="Добавить", width=100, command=self._add).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="Изменить", width=100, command=self._edit).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="Удалить", width=100,
            fg_color="#EF4444", hover_color="#DC2626",
            command=self._delete,
        ).pack(side="left", padx=3)
        self._resolve_btn = ctk.CTkButton(
            btn_frame, text="↻ Названия", width=110, command=self._resolve_all
        )
        self._resolve_btn.pack(side="left", padx=3)

        # Export/Import row
        io_frame = ctk.CTkFrame(self)
        io_frame.pack(fill="x", padx=10, pady=(2, 2))
        ctk.CTkButton(io_frame, text="Экспорт", width=110, command=self._export).pack(side="left", padx=3)
        ctk.CTkButton(io_frame, text="Импорт", width=110, command=self._import).pack(side="left", padx=3)

        # Search + count row
        filter_row = ctk.CTkFrame(self, fg_color="transparent")
        filter_row.pack(fill="x", padx=10, pady=(2, 2))
        self._search_entry = ctk.CTkEntry(
            filter_row, textvariable=self._search_var, placeholder_text="Поиск...", width=200
        )
        self._search_entry.pack(side="left")
        self._search_var.trace_add("write", lambda *_: self._refresh())
        self._count_label = ctk.CTkLabel(filter_row, text="", text_color="gray")
        self._count_label.pack(side="right", padx=4)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh()
        import threading
        threading.Thread(target=self._auto_resolve_missing, daemon=True).start()

    def _update_count_label(self):
        chats = self._storage.load_chats()
        enabled_count = sum(1 for c in chats if c.get("enabled", True))
        self._count_label.configure(text=f"Всего: {len(chats)}  активных: {enabled_count}")

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._selected = None
        self._buttons = {}

        all_chats = self._storage.load_chats()
        query = self._search_var.get().strip().lower()
        chats = (
            [c for c in all_chats if query in (c.get("name") or c["chat"]).lower()]
            if query else all_chats
        )
        stats = self._storage.load_chat_stats()
        self._update_count_label()

        for entry in chats:
            self._add_chat_row(entry, stats)

    def _add_chat_row(self, entry, stats):
        chat = entry["chat"]
        name = entry.get("name") or chat
        label = name + ("  [+ суффикс]" if entry.get("suffix") else "")

        row = ctk.CTkFrame(self._listbox, fg_color="transparent")
        row.pack(fill="x", pady=1)

        # Enable/disable switch
        enabled_var = ctk.BooleanVar(value=entry.get("enabled", True))
        ctk.CTkSwitch(
            row, text="", variable=enabled_var,
            command=lambda c=chat, v=enabled_var: self._toggle_enabled(c, v.get()),
        ).pack(side="left", padx=(0, 4))

        # Selection button
        btn = ctk.CTkButton(
            row, text=label, anchor="w",
            fg_color="transparent", text_color=("black", "white"),
            hover_color=("gray80", "gray30"),
            command=lambda c=chat: self._select(c),
        )
        btn.pack(side="left", fill="x", expand=True)
        self._buttons[chat] = btn

        # Stats indicator
        chat_stats = stats.get(chat)
        if chat_stats:
            ok = chat_stats.get("ok", 0)
            err = chat_stats.get("error", 0)
            total = ok + err
            if total > 0:
                ratio = ok / total
                color = "#4CAF50" if ratio > 0.8 else ("#FF9800" if ratio > 0.3 else "#EF4444")
                ctk.CTkLabel(
                    row, text=f"✓{ok} ✗{err}", text_color=color,
                    font=ctk.CTkFont(size=10), width=60,
                ).pack(side="right", padx=(4, 0))

    def _toggle_enabled(self, chat, enabled):
        chats = self._storage.load_chats()
        for c in chats:
            if c["chat"] == chat:
                c["enabled"] = enabled
                break
        self._storage.save_chats(chats)
        self._update_count_label()

    def _select(self, chat):
        if self._selected and self._selected in self._buttons:
            self._buttons[self._selected].configure(fg_color="transparent")
        self._selected = chat
        self._buttons[chat].configure(fg_color=("gray75", "gray25"))

    def _auto_resolve_missing(self):
        if not self._tg:
            return
        chats = self._storage.load_chats()
        missing = [c for c in chats if not c.get("name")]
        if not missing:
            return
        for entry in chats:
            if not entry.get("name"):
                entry["name"] = self._resolve_name(entry["chat"])
        self._storage.save_chats(chats)
        self.after(0, self._refresh)

    def _resolve_all(self):
        import threading
        self._resolve_btn.configure(state="disabled", text="Загрузка...")
        threading.Thread(target=self._resolve_all_worker, daemon=True).start()

    def _resolve_all_worker(self):
        chats = self._storage.load_chats()
        for entry in chats:
            entry["name"] = self._resolve_name(entry["chat"])
        self._storage.save_chats(chats)
        self.after(0, self._resolve_done)

    def _resolve_done(self):
        self._resolve_btn.configure(state="normal", text="↻ Названия")
        self._refresh()

    def _resolve_name(self, chat):
        if self._tg:
            return self._tg.get_chat_title(chat) or chat
        return chat

    def _add(self):
        ChatDialog(self, on_save=self._on_add_save)

    def _on_add_save(self, entry):
        chats = self._storage.load_chats()
        if not any(c["chat"] == entry["chat"] for c in chats):
            entry["name"] = self._resolve_name(entry["chat"])
            entry["enabled"] = True
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
            ChatDialog(self, entry=entry, on_save=self._on_edit_save)

    def _on_edit_save(self, entry):
        chats = self._storage.load_chats()
        old = next((c for c in chats if c["chat"] == entry["chat"]), {})
        entry["name"] = old.get("name") or self._resolve_name(entry["chat"])
        entry["enabled"] = old.get("enabled", True)
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

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="chats_export.json",
        )
        if path:
            chats = self._storage.load_chats()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(chats, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Экспорт", f"Сохранено {len(chats)} чатов в {path}")

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                imported = json.load(f)
            imported = [
                {"chat": c, "suffix": "", "enabled": True} if isinstance(c, str) else c
                for c in imported
            ]
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
            return
        existing = self._storage.load_chats()
        existing_ids = {c["chat"] for c in existing}
        added = [c for c in imported if c["chat"] not in existing_ids]
        existing.extend(added)
        self._storage.save_chats(existing)
        self._refresh()
        messagebox.showinfo("Импорт", f"Добавлено {len(added)} новых чатов")
