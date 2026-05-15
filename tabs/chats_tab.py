import json
import threading
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
        super().__init__(parent, fg_color="transparent")
        self._storage = storage
        self._tg = tg_client
        self._selected = None
        self._buttons = {}
        self._val_labels: dict[str, ctk.CTkLabel] = {}
        self._validation: dict[str, bool] = {}
        self._search_var = ctk.StringVar()

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(
            header, text="Чаты",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#111827", "white"),
        ).pack(side="left")
        self._count_label = ctk.CTkLabel(header, text="", text_color=("gray50", "#64748B"), font=ctk.CTkFont(size=12))
        self._count_label.pack(side="left", padx=12)

        # Action bar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(12, 4))
        ctk.CTkButton(
            bar, text="+ Добавить", width=110, height=34,
            fg_color="#F97316", hover_color="#EA6C0A",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._add,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            bar, text="Изменить", width=100, height=34,
            fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
            text_color=("#374151", "#E2E8F0"),
            command=self._edit,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            bar, text="Удалить", width=90, height=34,
            fg_color="#EF4444", hover_color="#DC2626",
            command=self._delete,
        ).pack(side="left", padx=(0, 6))
        self._resolve_btn = ctk.CTkButton(
            bar, text="↻ Названия", width=110, height=34,
            fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
            text_color=("#374151", "#E2E8F0"),
            command=self._resolve_all,
        )
        self._resolve_btn.pack(side="left")

        # Tools bar
        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkButton(
            tools, text="Экспорт", width=90, height=30,
            fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
            text_color=("gray50", "#64748B"), font=ctk.CTkFont(size=12),
            command=self._export,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            tools, text="Импорт", width=90, height=30,
            fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
            text_color=("gray50", "#64748B"), font=ctk.CTkFont(size=12),
            command=self._import,
        ).pack(side="left", padx=(0, 12))
        self._validate_btn = ctk.CTkButton(
            tools, text="✓ Проверить доступность", width=190, height=30,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12),
            command=self._validate_all,
        )
        self._validate_btn.pack(side="left", padx=(0, 12))
        self._search_entry = ctk.CTkEntry(
            tools, textvariable=self._search_var, placeholder_text="Поиск...", width=160, height=30,
        )
        self._search_entry.pack(side="right")
        self._search_var.trace_add("write", lambda *_: self._refresh())

        self._listbox = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._listbox.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._refresh()
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

        card = ctk.CTkFrame(
            self._listbox,
            fg_color=("white", "#0F172A"),
            border_width=1,
            border_color=("#E2E8F0", "#1E293B"),
            corner_radius=8,
        )
        card.pack(fill="x", pady=3)

        # Enable/disable switch
        enabled_var = ctk.BooleanVar(value=entry.get("enabled", True))
        ctk.CTkSwitch(
            card, text="", variable=enabled_var, width=46,
            command=lambda c=chat, v=enabled_var: self._toggle_enabled(c, v.get()),
        ).pack(side="left", padx=(8, 0))

        # Main button (chat name)
        suffix_badge = "  +" if entry.get("suffix") else ""
        btn = ctk.CTkButton(
            card, text=name + suffix_badge, anchor="w",
            fg_color="transparent",
            hover_color=("gray92", "#1E293B"),
            text_color=("#111827", "white"),
            font=ctk.CTkFont(size=13),
            corner_radius=6,
            command=lambda c=chat: self._select(c),
        )
        btn.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        self._buttons[chat] = btn

        # Validation dot
        val_lbl = ctk.CTkLabel(card, text="", width=22, font=ctk.CTkFont(size=14))
        val_lbl.pack(side="right", padx=(0, 4))
        self._val_labels[chat] = val_lbl
        if chat in self._validation:
            self._apply_val_label(val_lbl, self._validation[chat])

        # Stats badge
        chat_stats = stats.get(chat)
        if chat_stats:
            ok = chat_stats.get("ok", 0)
            err = chat_stats.get("error", 0)
            total = ok + err
            if total > 0:
                ratio = ok / total
                color = "#22C55E" if ratio > 0.8 else ("#F59E0B" if ratio > 0.3 else "#EF4444")
                ctk.CTkLabel(
                    card, text=f"✓{ok} ✗{err}",
                    text_color=color,
                    font=ctk.CTkFont(size=10),
                ).pack(side="right", padx=(0, 8))

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

    # ── Validation ─────────────────────────────────────────────────────────

    @staticmethod
    def _apply_val_label(lbl: ctk.CTkLabel, ok: bool):
        lbl.configure(text="●" if ok else "✗", text_color="#4CAF50" if ok else "#EF4444")

    def _validate_all(self):
        if not self._tg:
            return
        self._validate_btn.configure(state="disabled", text="Проверка...")
        self._validation.clear()
        threading.Thread(target=self._validate_worker, daemon=True).start()

    def _validate_worker(self):
        chats = self._storage.load_chats()
        for entry in chats:
            chat = entry["chat"]
            ok = self._tg.get_chat_title(chat) is not None
            self._validation[chat] = ok
            lbl = self._val_labels.get(chat)
            if lbl:
                self.after(0, self._apply_val_label, lbl, ok)
        self.after(0, self._validate_done)

    def _validate_done(self):
        self._validate_btn.configure(state="normal", text="✓ Проверить")
        ok_n = sum(1 for v in self._validation.values() if v)
        fail_n = sum(1 for v in self._validation.values() if not v)
        if fail_n:
            messagebox.showwarning(
                "Проверка чатов",
                f"Доступно: {ok_n}  Недоступно: {fail_n}\n\nКрасные ✗ — чат недоступен или вы не участник.",
            )

    # ── CRUD ───────────────────────────────────────────────────────────────

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
